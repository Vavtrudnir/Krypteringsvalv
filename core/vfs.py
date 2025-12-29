"""
Virtual File System module for Hemliga valvet.
Manages the JSON tree structure and binary blob operations.
"""

import os
import time
from typing import Dict, Any, Optional, List, Tuple, Union
from pathlib import Path
import mimetypes

from core.container import VaultContainer, ContainerError


class VfsError(Exception):
    """Virtual File System related errors."""
    pass


class VirtualFileSystem:
    """Manages files within the encrypted vault."""
    
    def __init__(self, container: VaultContainer):
        self.container = container
        self.metadata: Dict[str, Any] = {}
        self.file_data: bytearray = bytearray()
        self._dirty = False
    
    def load(self, password: str) -> None:
        """Load vault data from container."""
        try:
            self.metadata, self.file_data = self.container.load(password)
            self._dirty = False
        except ContainerError as e:
            raise VfsError(f"Failed to load vault: {str(e)}")
    
    def save(self, password: str) -> None:
        """Save vault data to container."""
        if not self._dirty:
            return  # No changes to save
        
        try:
            self.container.save(password, self.metadata, bytes(self.file_data))
            self._dirty = False
        except ContainerError as e:
            raise VfsError(f"Failed to save vault: {str(e)}")
    
    def add_file(self, file_path: Union[str, Path], vault_path: str) -> None:
        """
        Add a file to the vault.
        
        Args:
            file_path: Path to the source file
            vault_path: Virtual path within the vault
        """
        source_path = Path(file_path)
        
        if not source_path.exists():
            raise VfsError(f"Source file does not exist: {file_path}")
        
        if not source_path.is_file():
            raise VfsError(f"Source path is not a file: {file_path}")
        
        # Normalize vault path
        vault_path = self._normalize_path(vault_path)
        
        if vault_path in self.metadata["files"]:
            raise VfsError(f"File already exists in vault: {vault_path}")
        
        try:
            # Read file content
            with open(source_path, 'rb') as f:
                content = f.read()
            
            # Add to file data blob
            offset = len(self.file_data)
            self.file_data.extend(content)
            
            # Update metadata
            self.metadata["files"][vault_path] = {
                "offset": offset,
                "size": len(content),
                "created": time.strftime("%Y-%m-%d %H:%M:%S"),
                "modified": time.strftime("%Y-%m-%d %H:%M:%S"),
                "mime_type": mimetypes.guess_type(str(source_path))[0] or "application/octet-stream"
            }
            
            self._dirty = True
            
        except Exception as e:
            raise VfsError(f"Failed to add file: {str(e)}")
    
    def extract_file(self, vault_path: str, extract_path: Union[str, Path]) -> None:
        """
        Extract a file from the vault.
        
        Args:
            vault_path: Virtual path within the vault
            extract_path: Destination path for extraction
        """
        vault_path = self._normalize_path(vault_path)
        dest_path = Path(extract_path)
        
        if vault_path not in self.metadata["files"]:
            raise VfsError(f"File not found in vault: {vault_path}")
        
        # Validate extraction path is safe
        if not VaultContainer.validate_extraction_path(vault_path, dest_path.parent):
            raise VfsError(f"Unsafe extraction path: {extract_path}")
        
        try:
            # Get file info
            file_info = self.metadata["files"][vault_path]
            offset = file_info["offset"]
            size = file_info["size"]
            
            # Extract content from blob
            content = self.file_data[offset:offset + size]
            
            # Create destination directory if needed
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            with open(dest_path, 'wb') as f:
                f.write(content)
            
        except Exception as e:
            raise VfsError(f"Failed to extract file: {str(e)}")
    
    def remove_file(self, vault_path: str) -> None:
        """
        Remove a file from the vault.
        
        Args:
            vault_path: Virtual path within the vault
        """
        vault_path = self._normalize_path(vault_path)
        
        if vault_path not in self.metadata["files"]:
            raise VfsError(f"File not found in vault: {vault_path}")
        
        try:
            # Get file info
            file_info = self.metadata["files"][vault_path]
            offset = file_info["offset"]
            size = file_info["size"]
            
            # Remove from file data blob
            del self.file_data[offset:offset + size]
            
            # Update offsets for all files after this one
            for path, info in self.metadata["files"].items():
                if info["offset"] > offset:
                    info["offset"] -= size
            
            # Remove from metadata
            del self.metadata["files"][vault_path]
            
            self._dirty = True
            
        except Exception as e:
            raise VfsError(f"Failed to remove file: {str(e)}")
    
    def get_file_info(self, vault_path: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a file in the vault.
        
        Args:
            vault_path: Virtual path within the vault
            
        Returns:
            File information dictionary or None if not found
        """
        vault_path = self._normalize_path(vault_path)
        return self.metadata["files"].get(vault_path)
    
    def list_files(self) -> List[str]:
        """
        List all files in the vault.
        
        Returns:
            List of virtual file paths
        """
        return list(self.metadata["files"].keys())
    
    def get_directory_tree(self) -> Dict[str, Any]:
        """
        Get a nested directory tree structure.
        
        Returns:
            Nested dictionary representing the directory tree
        """
        tree = {}
        
        for file_path in self.metadata["files"].keys():
            parts = file_path.strip("/").split("/")
            current = tree
            
            for i, part in enumerate(parts):
                if i == len(parts) - 1:
                    # This is the file
                    current[part] = self.metadata["files"][file_path]
                else:
                    # This is a directory
                    if part not in current:
                        current[part] = {}
                    current = current[part]
        
        return tree
    
    def file_exists(self, vault_path: str) -> bool:
        """
        Check if a file exists in the vault.
        
        Args:
            vault_path: Virtual path within the vault
            
        Returns:
            True if file exists
        """
        vault_path = self._normalize_path(vault_path)
        return vault_path in self.metadata["files"]
    
    def get_file_size(self, vault_path: str) -> Optional[int]:
        """
        Get the size of a file in the vault.
        
        Args:
            vault_path: Virtual path within the vault
            
        Returns:
            File size in bytes or None if not found
        """
        file_info = self.get_file_info(vault_path)
        return file_info["size"] if file_info else None
    
    def get_total_size(self) -> int:
        """
        Get the total size of all files in the vault.
        
        Returns:
            Total size in bytes
        """
        return sum(info["size"] for info in self.metadata["files"].values())
    
    def get_file_count(self) -> int:
        """
        Get the number of files in the vault.
        
        Returns:
            Number of files
        """
        return len(self.metadata["files"])
    
    def is_dirty(self) -> bool:
        """Check if the vault has unsaved changes."""
        return self._dirty
    
    def _normalize_path(self, path: str) -> str:
        """
        Normalize a virtual path.
        
        Args:
            path: Virtual path to normalize
            
        Returns:
            Normalized path
        """
        # Convert to forward slashes and remove leading/trailing slashes
        normalized = path.replace("\\", "/").strip("/")
        
        # Ensure it starts with /
        if normalized and not normalized.startswith("/"):
            normalized = "/" + normalized
        
        return normalized
    
    @staticmethod
    def create_empty() -> Dict[str, Any]:
        """Create empty vault metadata."""
        return {
            "timestamp": time.time(),
            "files": {}
        }
