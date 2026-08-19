from pathlib import Path
from typing import Iterator
import os
import json
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes


CHUNK_MAGIC = b"STSH"
CHUNK_VERSION = 1
NONCE_SIZE = 12
TAG_SIZE = 16
KEY_SIZE = 32
HEADER_SIZE = 37  # magic(4) + version(1) + file_id(16) + index(8) + size(4) + total(4)


def derive_file_key(master_key: bytes, file_id: bytes) -> bytes:
    """Derive a per-file encryption key from master key and file ID."""
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=KEY_SIZE,
        salt=None,
        info=b"stash-file-key" + file_id,
    )
    return hkdf.derive(master_key)


def encrypt_chunk(data: bytes, key: bytes, chunk_index: int) -> bytes:
    """Encrypt a chunk with AES-GCM. Returns nonce + ciphertext + tag."""
    aesgcm = AESGCM(key)
    nonce = os.urandom(NONCE_SIZE)
    # Include chunk index in AAD to prevent reordering
    aad = chunk_index.to_bytes(8, "big")
    ciphertext = aesgcm.encrypt(nonce, data, aad)
    # ciphertext = ciphertext_body + tag (AESGCM appends tag)
    return nonce + ciphertext


def decrypt_chunk(encrypted: bytes, key: bytes, chunk_index: int) -> bytes:
    """Decrypt a chunk encrypted with encrypt_chunk."""
    if len(encrypted) < NONCE_SIZE + TAG_SIZE:
        raise ValueError("Chunk too small")
    nonce = encrypted[:NONCE_SIZE]
    ciphertext = encrypted[NONCE_SIZE:]
    aesgcm = AESGCM(key)
    aad = chunk_index.to_bytes(8, "big")
    return aesgcm.decrypt(nonce, ciphertext, aad)


def parse_chunk_header(header: bytes) -> tuple[bytes, int, int, int]:
    """Parse chunk header. Returns (file_id, chunk_index, orig_size, total_chunks)."""
    if len(header) != HEADER_SIZE:
        raise ValueError(f"Invalid header size: {len(header)} != {HEADER_SIZE}")
    if header[:4] != CHUNK_MAGIC:
        raise ValueError(f"Invalid magic: {header[:4]!r}")
    if header[4] != CHUNK_VERSION:
        raise ValueError(f"Unsupported version: {header[4]}")
    file_id = header[5:21]
    chunk_index = int.from_bytes(header[21:29], "big")
    orig_size = int.from_bytes(header[29:33], "big")
    total_chunks = int.from_bytes(header[33:37], "big")
    return file_id, chunk_index, orig_size, total_chunks


def build_chunk_header(file_id: bytes, chunk_index: int, chunk_size: int, total_chunks: int) -> bytes:
    """Build chunk header: magic(4) | version(1) | file_id(16) | index(8) | size(4) | total(4)"""
    header = bytearray()
    header.extend(CHUNK_MAGIC)
    header.append(CHUNK_VERSION)
    header.extend(file_id[:16].ljust(16, b'\x00'))
    header.extend(chunk_index.to_bytes(8, "big"))
    header.extend(chunk_size.to_bytes(4, "big"))
    header.extend(total_chunks.to_bytes(4, "big"))
    return bytes(header)


def chunk_file(
    path: str | Path,
    chunk_size: int = 10 * 1024 * 1024,
) -> Iterator[bytes]:
    """
    Read a file in fixed-size chunks without loading the entire
    file into memory.

    Args:
        path: Path to the file.
        chunk_size: Maximum size of each chunk in bytes.

    Yields:
        Individual chunks as bytes.
    """

    path = Path(path)

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")

    with path.open("rb") as file:
        while chunk := file.read(chunk_size):
            yield chunk


def split_file(
    source: str | Path,
    output_dir: str | Path,
    chunk_size: int = 10 * 1024 * 1024,
    master_key: bytes | None = None,
) -> dict:
    """
    Split a file into encrypted chunk files.

    Args:
        source: Path to the file.
        output_dir: Directory for the output.
        chunk_size: Maximum size of each chunk in bytes.
        master_key: Optional master key. If not provided, one is generated.

    Returns:
        Dict with manifest info: file_id, master_key, chunks list, etc.
    """

    source = Path(source)
    output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    if master_key is None:
        master_key = os.urandom(KEY_SIZE)

    # Generate file ID (random)
    file_id = os.urandom(16)

    # Derive per-file encryption key
    file_key = derive_file_key(master_key, file_id)

    # First pass: count chunks
    chunks_data = list(chunk_file(source, chunk_size))
    total_chunks = len(chunks_data)

    manifest_chunks = []

    for index, data in enumerate(chunks_data):
        # Encrypt chunk
        encrypted_data = encrypt_chunk(data, file_key, index)

        # Build header
        header = build_chunk_header(file_id, index, len(data), total_chunks)

        # Write chunk file: header + encrypted_data
        chunk_filename = f"{source.name}.stsh{index:04d}"
        chunk_path = output_dir / chunk_filename
        chunk_path.write_bytes(header + encrypted_data)

        manifest_chunks.append({
            "index": index,
            "filename": chunk_filename,
            "size": len(data),
            "encrypted_size": len(encrypted_data),
        })

    manifest = {
        "version": 1,
        "file_name": source.name,
        "file_size": sum(c["size"] for c in manifest_chunks),
        "chunk_size": chunk_size,
        "total_chunks": total_chunks,
        "file_id": file_id.hex(),
        "master_key": master_key.hex(),
        "chunks": manifest_chunks,
    }

    # Write manifest
    manifest_path = output_dir / f"{source.name}.manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))

    return manifest


def reconstruct_file(
    manifest_path: str | Path,
    output_path: str | Path,
    master_key: bytes | None = None,
) -> Path:
    """
    Reconstruct a file from encrypted chunks using manifest.

    Args:
        manifest_path: Path to manifest.json
        output_path: Path to write reconstructed file
        master_key: Master key (if not in manifest)

    Returns:
        Path to reconstructed file
    """
    manifest_path = Path(manifest_path)
    output_path = Path(output_path)

    with manifest_path.open("r") as f:
        manifest = json.load(f)

    file_id = bytes.fromhex(manifest["file_id"])
    if master_key is None:
        master_key = bytes.fromhex(manifest["master_key"])

    file_key = derive_file_key(master_key, file_id)

    # Sort chunks by index
    chunks_info = sorted(manifest["chunks"], key=lambda c: c["index"])

    output_dir = manifest_path.parent
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("wb") as outfile:
        for chunk_info in chunks_info:
            chunk_path = output_dir / chunk_info["filename"]
            with chunk_path.open("rb") as f:
                data = f.read()

            # Parse header
            header = data[:HEADER_SIZE]
            parsed_file_id, chunk_index, orig_size, total_chunks = parse_chunk_header(header)

            if parsed_file_id != file_id:
                raise ValueError(f"File ID mismatch in chunk {chunk_index}")

            # Decrypt
            encrypted_data = data[HEADER_SIZE:]
            decrypted = decrypt_chunk(encrypted_data, file_key, chunk_index)

            if len(decrypted) != orig_size:
                raise ValueError(f"Size mismatch in chunk {chunk_index}")

            outfile.write(decrypted)

    return output_path


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python -m src.main split <source_file> <output_dir> [chunk_size_mb]")
        print("  python -m src.main reconstruct <manifest_path> <output_file> [master_key_hex]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "split":
        if len(sys.argv) < 4:
            print("Usage: python -m src.main split <source_file> <output_dir> [chunk_size_mb]")
            sys.exit(1)
        source = sys.argv[2]
        output_dir = sys.argv[3]
        chunk_size_mb = int(sys.argv[4]) if len(sys.argv) > 4 else 10
        chunk_size = chunk_size_mb * 1024 * 1024

        manifest = split_file(source, output_dir, chunk_size)
        print(f"Created {manifest['total_chunks']} encrypted chunks")
        print(f"Manifest: {output_dir}/{source}.manifest.json")
        print(f"Master key (save this!): {manifest['master_key']}")

    elif command == "reconstruct":
        if len(sys.argv) < 4:
            print("Usage: python -m src.main reconstruct <manifest_path> <output_file> [master_key_hex]")
            sys.exit(1)
        manifest_path = sys.argv[2]
        output_path = sys.argv[3]
        master_key = bytes.fromhex(sys.argv[4]) if len(sys.argv) > 4 else None

        reconstruct_file(manifest_path, output_path, master_key)
        print(f"Reconstructed: {output_path}")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)