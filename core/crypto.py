"""
Core cryptography module for Hemliga valvet.
Implements Argon2id key derivation and AES-256-GCM encryption.
"""

import os
import struct
from typing import Tuple, Union

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id
from cryptography.hazmat.backends import default_backend


class CryptoError(Exception):
    """Cryptography-related errors."""
    pass


class CryptoManager:
    """Handles all cryptographic operations for the vault."""
    
    # Constants as per specification
    ARGON2_MEMORY_COST = 512 * 1024  # 512 MiB in KiB
    ARGON2_ITERATIONS = 4  # iterations
    ARGON2_LANES = 4  # threads (called lanes in cryptography)
    SALT_SIZE = 16  # bytes
    NONCE_SIZE = 12  # bytes for AES-GCM
    KEY_SIZE = 32  # bytes for AES-256
    
    def __init__(self):
        self.backend = default_backend()
    
    def generate_salt(self) -> bytes:
        """Generate a random 16-byte salt."""
        return os.urandom(self.SALT_SIZE)
    
    def generate_nonce(self) -> bytes:
        """Generate a random 12-byte nonce for AES-GCM."""
        return os.urandom(self.NONCE_SIZE)
    
    def derive_key(self, password: str, salt: bytes) -> bytes:
        """
        Derive encryption key from password using Argon2id.
        
        Args:
            password: User password
            salt: 16-byte salt
            
        Returns:
            32-byte encryption key
        """
        if len(salt) != self.SALT_SIZE:
            raise CryptoError(f"Salt must be {self.SALT_SIZE} bytes")
        
        kdf = Argon2id(
            salt=salt,
            length=self.KEY_SIZE,
            memory_cost=self.ARGON2_MEMORY_COST,
            iterations=self.ARGON2_ITERATIONS,
            lanes=self.ARGON2_LANES
        )
        
        password_bytes = password.encode('utf-8')
        return kdf.derive(password_bytes)
    
    def encrypt(self, data: bytes, key: bytes, aad: bytes = b"") -> Tuple[bytes, bytes]:
        """
        Encrypt data using AES-256-GCM.
        
        Args:
            data: Plaintext to encrypt
            key: 32-byte encryption key
            aad: Additional authenticated data
            
        Returns:
            Tuple of (nonce, ciphertext)
        """
        if len(key) != self.KEY_SIZE:
            raise CryptoError(f"Key must be {self.KEY_SIZE} bytes")
        
        nonce = self.generate_nonce()
        aesgcm = AESGCM(key)
        
        ciphertext = aesgcm.encrypt(nonce, data, aad)
        return nonce, ciphertext
    
    def decrypt(self, nonce: bytes, ciphertext: bytes, key: bytes, aad: bytes = b"") -> bytes:
        """
        Decrypt data using AES-256-GCM.
        
        Args:
            nonce: 12-byte nonce
            ciphertext: Encrypted data
            key: 32-byte encryption key
            aad: Additional authenticated data
            
        Returns:
            Decrypted plaintext
        """
        if len(key) != self.KEY_SIZE:
            raise CryptoError(f"Key must be {self.KEY_SIZE} bytes")
        
        if len(nonce) != self.NONCE_SIZE:
            raise CryptoError(f"Nonce must be {self.NONCE_SIZE} bytes")
        
        aesgcm = AESGCM(key)
        
        try:
            plaintext = aesgcm.decrypt(nonce, ciphertext, aad)
            return plaintext
        except Exception as e:
            raise CryptoError(f"Decryption failed: {str(e)}")
    
    def verify_password(self, password: str, salt: bytes, expected_key: bytes) -> bool:
        """
        Verify password by deriving key and comparing with expected key.
        
        Args:
            password: User password to verify
            salt: Salt used for key derivation
            expected_key: Expected derived key
            
        Returns:
            True if password is correct
        """
        try:
            derived_key = self.derive_key(password, salt)
            return derived_key == expected_key
        except CryptoError:
            return False


# Utility functions for binary format handling
def pack_uint16(value: int) -> bytes:
    """Pack unsigned 16-bit integer (big endian)."""
    return struct.pack(">H", value)


def pack_uint32(value: int) -> bytes:
    """Pack unsigned 32-bit integer (big endian)."""
    return struct.pack(">I", value)


def unpack_uint16(data: bytes) -> int:
    """Unpack unsigned 16-bit integer (big endian)."""
    return struct.unpack(">H", data)[0]


def unpack_uint32(data: bytes) -> int:
    """Unpack unsigned 32-bit integer (big endian)."""
    return struct.unpack(">I", data)[0]
