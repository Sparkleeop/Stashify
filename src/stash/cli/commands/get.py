"""CLI command: get - Retrieve a file."""

import asyncio
from pathlib import Path

import click

from stash.cli.output import create_progress, format_size, print_error, print_info, print_success
from stash.core.crypto import CryptoEngine, EncryptionConfig
from stash.core.metadata import MetadataStore
from stash.providers import ProviderRegistry


@click.command()
@click.argument("file_id_or_name")
@click.option("--output", "-o", type=click.Path(path_type=Path), help="Output path (default: current directory)")
@click.option("--password", prompt=True, hide_input=True, help="Encryption password")
@click.option("--overwrite", is_flag=True, help="Overwrite existing file")
@click.pass_context
def get_cmd(ctx: click.Context, file_id_or_name: str, output: Path | None, password: str, overwrite: bool) -> None:
    """Retrieve a file from Stash."""
    asyncio.run(_get_async(file_id_or_name, ctx.obj["repo"], output, password, overwrite))


async def _get_async(
    file_id_or_name: str,
    repo_path: Path,
    output: Path | None,
    password: str,
    overwrite: bool,
) -> None:
    repo = repo_path.resolve()
    store = MetadataStore(repo)

    file_id = _resolve_file_id(store, file_id_or_name)
    if not file_id:
        print_error(f"File not found: {file_id_or_name}")
        return

    manifest = store.load_manifest(file_id)

    # Decrypt filename
    crypto = CryptoEngine()
    enc_config = EncryptionConfig(
        algorithm=manifest.encryption.algorithm,
        key_size=manifest.encryption.key_size,
        nonce_size=manifest.encryption.nonce_size,
        chunk_key_derivation=manifest.encryption.chunk_key_derivation,
    )
    file_key = None
    try:
        if manifest.encryption.file_key_wrapped:
            from stash.core.crypto import FileKey
            file_key = FileKey(
                key=crypto.decrypt_file_key(
                    manifest.encryption.file_key_wrapped,
                    password,
                    enc_config
                ).key,
                salt=manifest.encryption.file_key_salt,
                config=enc_config
            )
        else:
            print_error("File key not wrapped - cannot decrypt")
            return
    except Exception as e:
        print_error(f"Failed to decrypt file key: {e}")
        return

    # Decrypt filename
    from stash.core.crypto import EncryptedChunk
    encrypted_name_bytes = bytes.fromhex(manifest.encrypted_name)
    encrypted_name_chunk = EncryptedChunk(
        ciphertext=encrypted_name_bytes,
        nonce=manifest.encrypted_name_nonce,
        chunk_index=-1,
    )
    try:
        decrypted_name = crypto.decrypt_chunk(encrypted_name_chunk, file_key).decode()
    except Exception as e:
        print_error(f"Failed to decrypt filename: {e}")
        return

    if output is None:
        output_path = Path.cwd() / decrypted_name
    elif output.is_dir():
        output_path = output / decrypted_name
    else:
        output_path = output

    if output_path.exists() and not overwrite:
        print_error(f"File exists: {output_path}. Use --overwrite to replace.")
        return

    providers_config = {}
    for chunk in manifest.chunks:
        if chunk.provider not in providers_config:
            config = store.get_provider_config(chunk.provider)
            if config:
                providers_config[chunk.provider] = config

    provider_instances = {}
    for name, config in providers_config.items():
        instance = await ProviderRegistry.create(config.type, config)
        provider_instances[name] = instance

    crypto = CryptoEngine()
    file_key = None

    try:
        if manifest.encryption.file_key_wrapped:
            from stash.core.crypto import FileKey
            # Convert EncryptionInfo to EncryptionConfig for decrypt_file_key
            enc_config = EncryptionConfig(
                algorithm=manifest.encryption.algorithm,
                key_size=manifest.encryption.key_size,
                nonce_size=manifest.encryption.nonce_size,
                chunk_key_derivation=manifest.encryption.chunk_key_derivation,
            )
            file_key = FileKey(
                key=crypto.decrypt_file_key(
                    manifest.encryption.file_key_wrapped,
                    password,
                    manifest.encryption.file_key_salt,
                    enc_config
                ).key,
                salt=manifest.encryption.file_key_salt,
                config=enc_config
            )
        else:
            print_error("File key not wrapped - cannot decrypt")
            return
    except Exception as e:
        print_error(f"Failed to decrypt file key: {e}")
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)

    progress = create_progress()
    task = progress.add_task("Downloading", total=manifest.chunk_count)

    with progress, output_path.open("wb") as f:
        for chunk_info in sorted(manifest.chunks, key=lambda c: c.index):
            provider = provider_instances.get(chunk_info.provider)
            if not provider:
                print_error(f"Provider not available: {chunk_info.provider}")
                return

            remote_ref = type('RemoteRef', (), {
                'provider': chunk_info.provider,
                'remote_id': chunk_info.remote_id,
                'metadata': {'message_id': chunk_info.metadata.get('message_id', '')}
            })()

            encrypted_data = await provider.download_chunk(remote_ref)

            from stash.core.crypto import EncryptedChunk
            encrypted_chunk = EncryptedChunk(
                ciphertext=encrypted_data,
                nonce=chunk_info.nonce,
                chunk_index=chunk_info.index,
            )

            try:
                decrypted = crypto.decrypt_chunk(encrypted_chunk, file_key)
                f.write(decrypted)
                progress.advance(task)
            except Exception as e:
                print_error(f"Decryption failed for chunk {chunk_info.index}: {e}")
                return

    for instance in provider_instances.values():
        await instance.close()

    print_success(f"Retrieved '{decrypted_name}' to {output_path}")
    print_info(f"Size: {format_size(manifest.original_size)}")


def _resolve_file_id(store: MetadataStore, identifier: str) -> str | None:
    """Resolve file ID or name to file ID."""
    if store.file_exists(identifier):
        return identifier
    for fid in store.list_files():
        manifest = store.load_manifest(fid)
        if manifest.original_name == identifier:
            return fid
    return None


get_commands = get_cmd