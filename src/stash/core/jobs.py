"""Async job engine with bounded workers, retries, and resumable operations."""

import asyncio
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from stash.core.exceptions import JobCancelledError, JobError


class JobStatus(Enum):
    """Job execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class JobConfig:
    """Job engine configuration."""
    max_workers: int = 4
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_factor: float = 2.0
    timeout: float = 300.0


@dataclass(slots=True)
class JobProgress:
    """Progress information for a job."""
    job_id: str
    status: JobStatus
    total: int
    completed: int
    failed: int
    current_chunk: int | None = None
    bytes_transferred: int = 0
    total_bytes: int = 0
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    error: str | None = None

    @property
    def percent(self) -> float:
        if self.total == 0:
            return 0.0
        return (self.completed / self.total) * 100

    @property
    def elapsed(self) -> float:
        end = self.end_time or time.time()
        return end - self.start_time


@dataclass
class Job:
    """A unit of work to execute."""
    id: str
    func: Callable[..., Awaitable[Any]]
    args: tuple[Any, ...]
    kwargs: dict[str, Any]
    retries: int = 0
    status: JobStatus = JobStatus.PENDING
    result: Any = None
    error: str | None = None
    progress_callback: Callable[[JobProgress], None] | None = None


class JobEngine:
    """Async job engine with bounded concurrency and retries."""

    def __init__(self, config: JobConfig | None = None):
        self.config = config or JobConfig()
        self._queue: asyncio.Queue[Job | None] = asyncio.Queue()
        self._workers: list[asyncio.Task[Any]] = []
        self._running = False
        self._progress: dict[str, JobProgress] = {}
        self._progress_lock = asyncio.Lock()
        self._results: dict[str, Any] = {}
        self._cancelled: set[str] = set()

    async def start(self) -> None:
        """Start the worker pool."""
        if self._running:
            return
        self._running = True
        for i in range(self.config.max_workers):
            worker = asyncio.create_task(self._worker(f"worker-{i}"))
            self._workers.append(worker)

    async def stop(self, wait: bool = True) -> None:
        """Stop the worker pool."""
        if not self._running:
            return
        self._running = False
        for _ in self._workers:
            await self._queue.put(None)
        if wait:
            await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()

    async def submit(
        self,
        job_id: str,
        func: Callable[..., Awaitable[Any]],
        *args: Any,
        progress_callback: Callable[[JobProgress], None] | None = None,
        **kwargs: Any,
    ) -> str:
        """Submit a job for execution."""
        if not self._running:
            await self.start()
        job = Job(
            id=job_id,
            func=func,
            args=args,
            kwargs=kwargs,
            progress_callback=progress_callback,
        )
        await self._queue.put(job)
        async with self._progress_lock:
            self._progress[job_id] = JobProgress(
                job_id=job_id,
                status=JobStatus.PENDING,
                total=kwargs.get("total", 1),
                completed=0,
                failed=0,
            )
        return job_id

    async def wait(self, job_id: str, timeout: float | None = None) -> Any:
        """Wait for a job to complete and return its result."""
        deadline = time.time() + (timeout or self.config.timeout)
        while True:
            if job_id in self._results:
                result = self._results.pop(job_id)
                if isinstance(result, Exception):
                    raise result
                return result
            if job_id in self._cancelled:
                self._cancelled.discard(job_id)
                raise JobCancelledError(f"Job {job_id} was cancelled")
            remaining = deadline - time.time()
            if remaining <= 0:
                raise JobError(f"Job {job_id} timed out")
            await asyncio.sleep(0.1)

    def cancel(self, job_id: str) -> None:
        """Cancel a pending or running job."""
        self._cancelled.add(job_id)
        if job_id in self._progress:
            self._progress[job_id].status = JobStatus.CANCELLED
            self._progress[job_id].end_time = time.time()

    def get_progress(self, job_id: str) -> JobProgress | None:
        """Get current progress of a job."""
        return self._progress.get(job_id)

    async def _worker(self, name: str) -> None:
        """Worker loop."""
        while self._running:
            job = await self._queue.get()
            if job is None:
                break
            if job.id in self._cancelled:
                self._queue.task_done()
                continue
            await self._execute_job(job)
            self._queue.task_done()

    async def _execute_job(self, job: Job) -> None:
        """Execute a single job with retries."""
        async with self._progress_lock:
            if job.id in self._progress:
                self._progress[job.id].status = JobStatus.RUNNING

        last_error = None
        for attempt in range(self.config.max_retries + 1):
            if job.id in self._cancelled:
                async with self._progress_lock:
                    if job.id in self._progress:
                        self._progress[job.id].status = JobStatus.CANCELLED
                        self._progress[job.id].end_time = time.time()
                return

            try:
                result = await asyncio.wait_for(
                    job.func(*job.args, **job.kwargs),
                    timeout=self.config.timeout,
                )
                self._results[job.id] = result
                async with self._progress_lock:
                    if job.id in self._progress:
                        self._progress[job.id].status = JobStatus.COMPLETED
                        self._progress[job.id].completed = self._progress[job.id].total
                        self._progress[job.id].end_time = time.time()
                return
            except asyncio.CancelledError:
                async with self._progress_lock:
                    if job.id in self._progress:
                        self._progress[job.id].status = JobStatus.CANCELLED
                        self._progress[job.id].end_time = time.time()
                raise
            except Exception as e:
                last_error = e
                if attempt < self.config.max_retries:
                    delay = min(
                        self.config.base_delay * (self.config.backoff_factor ** attempt),
                        self.config.max_delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    break

        async with self._progress_lock:
            if job.id in self._progress:
                self._progress[job.id].status = JobStatus.FAILED
                self._progress[job.id].error = str(last_error)
                self._progress[job.id].end_time = time.time()
        self._results[job.id] = last_error or JobError("Job failed")

    @asynccontextmanager
    async def session(self) -> AsyncIterator["JobEngine"]:
        """Context manager for engine lifecycle."""
        await self.start()
        try:
            yield self
        finally:
            await self.stop()