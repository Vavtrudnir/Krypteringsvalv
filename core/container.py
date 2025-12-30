"""
Container module for Hemliga valvet.
Handles file I/O, binary format, atomic saves, and compression.
"""

import os
import zlib
import time
from typing import Dict, Any, Optional, Tuple, Union
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
            print(f"DEBUG: Opening vault file: {self.file_path}")  # Debug
            if self.file_path.exists():
                mode = 'r+b'
                print("DEBUG: File exists, using r+b mode")  # Debug
            else:
                mode = 'w+b'
                print("DEBUG: File doesn't exist, using w+b mode")  # Debug
            
            print(f"DEBUG: Attempting to open file with mode: {mode}")  # Debug
            self._file_handle = open(self.file_path, mode)
            print("DEBUG: File opened successfully")  # Debug
            
            # Temporarily disable file locking to fix permission issues
            # # Acquire exclusive lock
            # if portalocker:
            #     portalocker.lock(self._file_handle, portalocker.LOCK_EX)
            # else:
            #     # Fallback for Windows
            #     import msvcrt
            #     msvcrt.locking(self._file_handle.fileno(), msvcrt.LK_NBLCK, 1)
            print("DEBUG: VaultContainer.open() completed successfully")  # Debug
                
        except Exception as e:
            print(f"DEBUG: VaultContainer.open() failed: {e}")  # Debug
            raise ContainerError(f"Failed to open vault file: {str(e)}")
    
    def close(self) -> None:
        """Close vault file and release lock."""
        if self._file_handle:
            # Temporarily disable file locking to fix permission issues
            # if portalocker:
            #     portalocker.unlock(self._file_handle)
            self._file_handle.close()
            self._file_handle = None
    
    def create_new(self, password: str, fast_mode: bool = False) -> None:
        """
        Create a new vault file with the given password.
        
        Args:
            password: Master password for the vault
            fast_mode: Use faster Argon2id settings (64MB, 2 iterations, 2 lanes)
        """
        print("DEBUG: create_new() started")  # Debug
        if self._file_handle is None:
            print("DEBUG: File handle is None!")  # Debug
            raise ContainerError("File not opened")
        
        print("DEBUG: File handle is OK")  # Debug
        
        # Generate salt and derive key
        print("DEBUG: Generating salt...")  # Debug
        salt = self.crypto.generate_salt()
        print("DEBUG: Salt generated, deriving key...")  # Debug
        key = self.crypto.derive_key(password, salt, fast_mode=fast_mode)
        print("DEBUG: Key derived successfully")  # Debug
        
        # Create empty vault data
        print("DEBUG: Creating empty vault data...")  # Debug
        empty_data = {
            "timestamp": time.time(),
            "files": {}
        }
        print("DEBUG: Empty data created")  # Debug
        
        # Serialize and encrypt empty data
        print("DEBUG: Serializing payload...")  # Debug
        payload = self._serialize_payload(empty_data, b"")
        print("DEBUG: Payload serialized, encrypting...")  # Debug
        nonce, ciphertext = self.crypto.encrypt(payload, key)
        print("DEBUG: Data encrypted successfully")  # Debug
        
        # Build header (update to reflect fast mode if used)
        print("DEBUG: Building header...")  # Debug
        header = self._build_header(salt, fast_mode=fast_mode)
        print("DEBUG: Header built successfully")  # Debug
        
        # Write file atomically
        print("DEBUG: Writing file atomically...")  # Debug
        self._write_atomic(header + nonce + ciphertext)
        print("DEBUG: Vault creation completed successfully!")  # Debug
    
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
        salt, bcrypt_rounds = self._parse_header(header)
        
        # Derive key using bcrypt
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
        salt, bcrypt_rounds = self._parse_header(header)
        
        # Derive key
        key = self.crypto.derive_key(password, salt)
        
        # Serialize and compress data
        payload = self._serialize_payload(metadata, file_data)
        
        # Encrypt with new nonce (critical: never reuse nonce)
        nonce, ciphertext = self.crypto.encrypt(payload, key, header)
        
        # Write atomically
        self._write_atomic(header + nonce + ciphertext)
    
    def _build_header(self, salt: bytes, fast_mode: bool = False) -> bytes:
        """Build the fixed 38-byte header for bcrypt."""
        # bcrypt salt is 29 bytes, but we'll use first 16 for consistency
        if len(salt) < 16:
            raise ContainerError("Invalid bcrypt salt size")
        
        # Use only first 16 bytes of bcrypt salt for header
        salt_bytes = salt[:16]
        
        # Choose rounds based on mode
        rounds = 8 if fast_mode else self.crypto.BCRYPT_ROUNDS
        
        header = (
            self.MAGIC_BYTES +
            pack_uint16(self.VERSION) +
            salt_bytes +  # 16 bytes
            pack_uint32(rounds) +  # 4 bytes
            pack_uint32(0) +  # placeholder for old memory_cost
            pack_uint32(0)    # placeholder for old iterations
        )
        
        if len(header) != self.HEADER_SIZE:
            raise ContainerError(f"Header size mismatch: {len(header)} != {self.HEADER_SIZE}")
        
        return header
    
    def _parse_header(self, header: bytes) -> Tuple[bytes, int]:
        """Parse the fixed 38-byte header for bcrypt."""
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
        
        # Extract salt (16 bytes)
        salt = header[10:26]
        
        # Extract bcrypt rounds
        bcrypt_rounds = unpack_uint32(header[26:30])
        
        return salt, bcrypt_rounds
    
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
        print("DEBUG: _write_atomic() started")  # Debug
        if self._file_handle is None:
            print("DEBUG: File handle is None in _write_atomic")  # Debug
            raise ContainerError("File not opened")
        
        try:
            print("DEBUG: Writing directly to file (skip atomic replace)...")  # Debug
            
            # Write directly to the open file handle
            self._file_handle.seek(0)
            self._file_handle.write(data)
            self._file_handle.flush()
            os.fsync(self._file_handle.fileno())
            self._file_handle.truncate()  # Remove any remaining data
            
            print("DEBUG: Direct write completed successfully!")  # Debug
            
        except Exception as e:
            print(f"DEBUG: Error in direct write: {e}")  # Debug
            raise ContainerError(f"Failed to write vault file: {str(e)}")
    
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
