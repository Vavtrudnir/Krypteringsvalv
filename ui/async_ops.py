"""
Async operations module for Hemliga valvet.
Handles threading for GUI responsiveness during crypto operations.
"""

import threading
import time
from typing import Callable, Optional, Any
from queue import Queue, Empty
import tkinter as tk
from tkinter import filedialog

import customtkinter as ctk

from core.container import VaultContainer, ContainerError
from core.vfs import VirtualFileSystem, VfsError


class OperationResult:
    """Result of an async operation."""
    
    def __init__(self, success: bool, data: Any = None, error: str = None):
        self.success = success
        self.data = data
        self.error = error


class AsyncWorker(threading.Thread):
    """Worker thread for background operations."""
    
    def __init__(self, operation: Callable, callback: Callable, *args, **kwargs):
        super().__init__()
        self.operation = operation
        self.callback = callback
        self.args = args
        self.kwargs = kwargs
        self.result = None
        self.daemon = True
    
    def run(self):
        """Execute the operation and call callback with result."""
        try:
            result = self.operation(*self.args, **self.kwargs)
            self.result = OperationResult(success=True, data=result)
        except Exception as e:
            self.result = OperationResult(success=False, error=str(e))
        
        # Schedule callback on main thread
        if self.callback:
            self.callback(self.result)


class ProgressDialog(ctk.CTkToplevel):
    """Progress dialog for long-running operations."""
    
    def __init__(self, parent, title="Laddar...", message="Vänligen vänta"):
        super().__init__(parent)
        
        self.title(title)
        self.geometry("400x150")
        self.resizable(False, False)
        
        # Center the dialog
        self.transient(parent)
        self.grab_set()
        
        # Create UI
        self.frame = ctk.CTkFrame(self)
        self.frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        self.message_label = ctk.CTkLabel(self.frame, text=message, font=ctk.CTkFont(size=14))
        self.message_label.pack(pady=10)
        
        self.progress = ctk.CTkProgressBar(self.frame)
        self.progress.pack(pady=10, padx=20, fill="x")
        self.progress.set(0)
        
        # Make progress bar indeterminate
        self.progress.configure(mode="indeterminate")
        self.progress.start()
        
        # Center on screen
        self._center_window()
    
    def _center_window(self):
        """Center the window on screen."""
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (self.winfo_width() // 2)
        y = (self.winfo_screenheight() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")
    
    def close(self):
        """Close the progress dialog."""
        self.progress.stop()
        self.grab_release()
        self.destroy()


class AsyncOperations:
    """Manages async operations for the vault application."""
    
    def __init__(self, app):
        self.app = app
        self.current_worker = None
        self.progress_dialog = None
    
    def create_vault(self, vault_path: str, password: str, callback: Callable):
        """Create a new vault asynchronously."""
        def operation():
            with VaultContainer(vault_path) as container:
                container.create_new(password)
                return "Valv skapat"
        
        self._run_operation(operation, callback, "Skapar valv...", "Skapar nytt krypterat valv")
    
    def open_vault(self, vault_path: str, password: str, callback: Callable):
        """Open an existing vault asynchronously."""
        def operation():
            container = VaultContainer(vault_path)
            vfs = VirtualFileSystem(container)
            vfs.load(password)
            return vfs
        
        self._run_operation(operation, callback, "Öppnar valv...", "Dekrypterar och laddar valv")
    
    def save_vault(self, vfs: VirtualFileSystem, password: str, callback: Callable):
        """Save vault changes asynchronously."""
        def operation():
            vfs.save(password)
            return "Valv sparat"
        
        self._run_operation(operation, callback, "Sparar valv...", "Krypterar och sparar valv")
    
    def add_files(self, vfs: VirtualFileSystem, file_paths: list, callback: Callable):
        """Add files to vault asynchronously."""
        def operation():
            added_files = []
            for file_path in file_paths:
                # Use filename as vault path
                vault_path = "/" + file_path.name
                vfs.add_file(file_path, vault_path)
                added_files.append(vault_path)
            return added_files
        
        self._run_operation(operation, callback, "Lägger till filer...", "Krypterar och lägger till filer")
    
    def extract_files(self, vfs: VirtualFileSystem, vault_paths: list, extract_dir: str, callback: Callable):
        """Extract files from vault asynchronously."""
        def operation():
            extracted_files = []
            for vault_path in vault_paths:
                # Use filename from vault path
                filename = vault_path.split("/")[-1]
                extract_path = f"{extract_dir}/{filename}"
                vfs.extract_file(vault_path, extract_path)
                extracted_files.append(extract_path)
            return extracted_files
        
        self._run_operation(operation, callback, "Extraherar filer...", "Dekrypterar och extraherar filer")
    
    def remove_files(self, vfs: VirtualFileSystem, vault_paths: list, callback: Callable):
        """Remove files from vault asynchronously."""
        def operation():
            removed_files = []
            for vault_path in vault_paths:
                vfs.remove_file(vault_path)
                removed_files.append(vault_path)
            return removed_files
        
        self._run_operation(operation, callback, "Tar bort filer...", "Tar bort filer från valvet")
    
    def _run_operation(self, operation: Callable, callback: Callable, title: str, message: str):
        """Run an operation with progress dialog."""
        # Show progress dialog
        self.progress_dialog = ProgressDialog(self.app, title, message)
        
        # Create and start worker thread
        self.current_worker = AsyncWorker(operation, self._operation_complete)
        self.current_worker.callback = callback
        self.current_worker.start()
    
    def _operation_complete(self, result: OperationResult):
        """Handle operation completion."""
        # Close progress dialog
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
        
        # Call application callback
        if self.current_worker and self.current_worker.callback:
            self.current_worker.callback(result)
        
        self.current_worker = None
    
    def show_file_dialog(self, title: str, file_types: list = None, mode: str = "open") -> Optional[str]:
        """Show file dialog for file selection."""
        if file_types is None:
            file_types = [("Alla filer", "*.*")]
        
        # Default to Documents folder for better permissions
        import os
        initialdir = os.path.join(os.path.expanduser("~"), "Documents")
        
        if mode == "open":
            result = filedialog.askopenfilename(
                title=title,
                filetypes=file_types,
                initialdir=initialdir
            )
        elif mode == "save":
            result = filedialog.asksaveasfilename(
                title=title,
                filetypes=file_types,
                defaultextension=".vault",
                initialdir=initialdir
            )
        elif mode == "directory":
            result = filedialog.askdirectory(
                title=title,
                initialdir=initialdir
            )
        else:
            result = filedialog.askopenfilenames(
                title=title,
                filetypes=file_types,
                initialdir=initialdir
            )
        
        return result if result else None
    
    def show_multiple_files_dialog(self, title: str, file_types: list = None) -> tuple:
        """Show file dialog for multiple file selection."""
        if file_types is None:
            file_types = [("Alla filer", "*.*")]
        
        # Default to Documents folder for better permissions
        import os
        initialdir = os.path.join(os.path.expanduser("~"), "Documents")
        
        result = filedialog.askopenfilenames(
            title=title,
            filetypes=file_types,
            initialdir=initialdir
        )
        
        return result if result else ()
