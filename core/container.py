"""
Container module for Hemliga valvet.
Handles file I/O, binary format, atomic saves, and compression.
"""

import os
import zlib
import time
from typing import Dict, Any, Optional, Tuple
from pathlib import Path

try:
    import portalocker
except ImportError:
    portalocker = None

from .crypto import CryptoManager, CryptoError, pack_uint16, pack_uint32, unpack_uint16, unpack_uint32


class ContainerError(Exception):
    """Container-related errors."""
    pass


class VaultContainer:
    """Handles vault file operations and binary format."""
    
    MAGIC_BYTES = b"PYVAULT2"
    VERSION = 1
    HEADER_SIZE = 38  # Fixed header size
    
    def __init__(self, file_path: Union[str, Path]):
        self.file_path = Path(file_path)
        self.crypto = CryptoManager()
        self._file_handle = None
        self._lock = None
    
    def __enter__(self):
        self.open()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def open(self) -> None:
        """Open vault file with exclusive lock."""
        try:
            if self.file_path.exists():
                mode = 'r+b'
            else:
                mode = 'w+b'
            
            self._file_handle = open(self.file_path, mode)
            
            # Acquire exclusive lock
            if portalocker:
                portalocker.lock(self._file_handle, portalocker.LOCK_EX)
            else:
                # Fallback for Windows
                import msvcrt
                msvcrt.locking(self._file_handle.fileno(), msvcrt.LK_NBLCK, 1)
                
        except Exception as e:
            raise ContainerError(f"Failed to open vault file: {str(e)}")
    
    def close(self) -> None:
        """Close vault file and release lock."""
        if self._file_handle:
            if portalocker:
                portalocker.unlock(self._file_handle)
            self._file_handle.close()
            self._file_handle = None
    
    def create_new(self, password: str) -> None:
        """
        Create a new vault file with the given password.
        
        Args:
            password: Master password for the vault
        """
        if self._file_handle is None:
            raise ContainerError("File not opened")
        
        # Generate salt and derive key
        salt = self.crypto.generate_salt()
        key = self.crypto.derive_key(password, salt)
        
        # Create empty vault data
        empty_data = {
            "timestamp": time.time(),
            "files": {}
        }
        
        # Serialize and encrypt empty data
        payload = self._serialize_payload(empty_data, b"")
        nonce, ciphertext = self.crypto.encrypt(payload, key)
        
        # Build header
        header = self._build_header(salt)
        
        # Write file atomically
        self._write_atomic(header + nonce + ciphertext)
    
    def load(self, password: str) -> Tuple[Dict[str, Any], bytes]:
        """
        Load and decrypt vault data.
        
        Args:
            password: Master password for the vault
            
        Returns:
            Tuple of (metadata_dict, file_data_bytes)
        """
        if self._file_handle is None:
            raise ContainerError("File not opened")
        
        # Read entire file
        self._file_handle.seek(0)
        file_data = self._file_handle.read()
        
        if len(file_data) < self.HEADER_SIZE + self.crypto.NONCE_SIZE:
            raise ContainerError("Invalid vault file: too small")
        
        # Parse header
        header = file_data[:self.HEADER_SIZE]
        salt, argon2_memory, argon2_time, argon2_parallelism = self._parse_header(header)
        
        # Verify header parameters match our expectations
        if (argon2_memory != self.crypto.ARGON2_MEMORY_COST or
            argon2_time != self.crypto.ARGON2_ITERATIONS or
            argon2_parallelism != self.crypto.ARGON2_LANES):
            raise ContainerError("Invalid vault parameters")
        
        # Derive key
        key = self.crypto.derive_key(password, salt)
        
        # Extract nonce and ciphertext
        nonce = file_data[self.HEADER_SIZE:self.HEADER_SIZE + self.crypto.NONCE_SIZE]
        ciphertext = file_data[self.HEADER_SIZE + self.crypto.NONCE_SIZE:]
        
        # Decrypt with header as AAD
        try:
            payload = self.crypto.decrypt(nonce, ciphertext, key, header)
        except CryptoError as e:
            raise ContainerError(f"Failed to decrypt vault: {str(e)}")
        
        # Decompress and parse
        decompressed = zlib.decompress(payload)
        return self._deserialize_payload(decompressed)
    
    def save(self, password: str, metadata: Dict[str, Any], file_data: bytes) -> None:
        """
        Save vault data with encryption.
        
        Args:
            password: Master password for the vault
            metadata: File metadata dictionary
            file_data: Concatenated file content
        """
        if self._file_handle is None:
            raise ContainerError("File not opened")
        
        # Read existing header to get salt
        self._file_handle.seek(0)
        header = self._file_handle.read(self.HEADER_SIZE)
        salt, _, _, _ = self._parse_header(header)
        
        # Derive key
        key = self.crypto.derive_key(password, salt)
        
        # Serialize and compress data
        payload = self._serialize_payload(metadata, file_data)
        
        # Encrypt with new nonce (critical: never reuse nonce)
        nonce, ciphertext = self.crypto.encrypt(payload, key, header)
        
        # Write atomically
        self._write_atomic(header + nonce + ciphertext)
    
    def _build_header(self, salt: bytes) -> bytes:
        """Build the fixed 38-byte header."""
        if len(salt) != self.crypto.SALT_SIZE:
            raise ContainerError("Invalid salt size")
        
        header = (
            self.MAGIC_BYTES +
            pack_uint16(self.VERSION) +
            salt +
            pack_uint32(self.crypto.ARGON2_MEMORY_COST) +
            pack_uint32(self.crypto.ARGON2_ITERATIONS) +
            pack_uint32(self.crypto.ARGON2_LANES)
        )
        
        if len(header) != self.HEADER_SIZE:
            raise ContainerError(f"Header size mismatch: {len(header)} != {self.HEADER_SIZE}")
        
        return header
    
    def _parse_header(self, header: bytes) -> Tuple[bytes, int, int, int]:
        """Parse the fixed 38-byte header."""
        if len(header) != self.HEADER_SIZE:
            raise ContainerError(f"Invalid header size: {len(header)}")
        
        # Verify magic bytes
        magic = header[:8]
        if magic != self.MAGIC_BYTES:
            raise ContainerError("Invalid vault file: wrong magic bytes")
        
        # Verify version
        version = unpack_uint16(header[8:10])
        if version != self.VERSION:
            raise ContainerError(f"Unsupported vault version: {version}")
        
        # Extract parameters
        salt = header[10:26]
        argon2_memory = unpack_uint32(header[26:30])
        argon2_time = unpack_uint32(header[30:34])
        argon2_parallelism = unpack_uint32(header[34:38])
        
        return salt, argon2_memory, argon2_time, argon2_parallelism
    
    def _serialize_payload(self, metadata: Dict[str, Any], file_data: bytes) -> bytes:
        """Serialize metadata and file data."""
        import json
        
        # Convert metadata to JSON bytes
        metadata_json = json.dumps(metadata, separators=(',', ':'), ensure_ascii=False)
        metadata_bytes = metadata_json.encode('utf-8')
        
        # Build payload: metadata_len + metadata + file_data
        payload = (
            pack_uint32(len(metadata_bytes)) +
            metadata_bytes +
            file_data
        )
        
        # Compress before encryption
        return zlib.compress(payload)
    
    def _deserialize_payload(self, payload: bytes) -> Tuple[Dict[str, Any], bytes]:
        """Deserialize metadata and file data."""
        # Extract metadata length
        if len(payload) < 4:
            raise ContainerError("Invalid payload: too small")
        
        metadata_len = unpack_uint32(payload[:4])
        
        if len(payload) < 4 + metadata_len:
            raise ContainerError("Invalid payload: metadata size mismatch")
        
        # Extract metadata
        metadata_bytes = payload[4:4 + metadata_len]
        metadata_json = metadata_bytes.decode('utf-8')
        
        import json
        metadata = json.loads(metadata_json)
        
        # Extract file data
        file_data = payload[4 + metadata_len:]
        
        return metadata, file_data
    
    def _write_atomic(self, data: bytes) -> None:
        """Write data to file atomically."""
        if self._file_handle is None:
            raise ContainerError("File not opened")
        
        # Create temporary file
        temp_path = self.file_path.with_suffix('.vault.tmp')
        
        try:
            # Ensure parent directory exists
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write to temporary file
            with open(temp_path, 'wb') as temp_file:
                temp_file.write(data)
                temp_file.flush()
                os.fsync(temp_file.fileno())
            
            # Atomically replace original file
            os.replace(temp_path, self.file_path)
            
            # Reopen the file to update handle
            self._file_handle.close()
            self._file_handle = open(self.file_path, 'r+b')
            
            # Reacquire lock
            if portalocker:
                portalocker.lock(self._file_handle, portalocker.LOCK_EX)
            
        except PermissionError as e:
            # Clean up temp file if it exists
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except:
                    pass
            raise ContainerError(f"Åtkomst nekad. Välj en annan plats för valvfilen eller kör programmet som administratör.")
        except Exception as e:
            # Clean up temp file if it exists
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except:
                    pass
            raise ContainerError(f"Failed to write vault atomically: {str(e)}")
    
    @staticmethod
    def validate_extraction_path(file_path: str, extract_dir: Path) -> bool:
        """
        Validate that extraction path doesn't escape the target directory.
        
        Args:
            file_path: Path within vault
            extract_dir: Target extraction directory
            
        Returns:
            True if path is safe
        """
        try:
            # Normalize paths
            target_path = (extract_dir / file_path).resolve()
            extract_dir_resolved = extract_dir.resolve()
            
            # Check if target is within extract directory
            return extract_dir_resolved in target_path.parents or target_path == extract_dir_resolved
        except (ValueError, OSError):
            return False
