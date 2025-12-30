"""
GUI module for Hemliga valvet.
Main CustomTkinter interface with Swedish localization.
"""

import tkinter as tk
from tkinter import messagebox
from typing import Optional, List, Union
from pathlib import Path

import customtkinter as ctk

from core.vfs import VirtualFileSystem, VfsError
# from core.password_validator import PasswordStrength
# from core.session_manager import SessionManager
from ui.async_ops import AsyncOperations, OperationResult

# 🔒 Critical: Ensure UTF-8 encoding for file operations
# Temporarily remove locale settings
# import sys
# if sys.version_info >= (3, 7):
#     import locale
#     try:
#         locale.setlocale(locale.LC_ALL, 'sv_SE.UTF-8')
#     except locale.Error:
#         try:
#             locale.setlocale(locale.LC_ALL, 'C.UTF-8')
#         except locale.Error:
#             pass  # Fallback to default


class IconLoader:
    """Handles icon loading with fallback generation."""
    
    def __init__(self, assets_dir: Path):
        self.assets_dir = assets_dir
        self.icons = {}
        self._load_icons()
    
    def _load_icons(self):
        """Load icons from assets directory or generate fallbacks."""
        icon_names = ["folder", "file", "add", "extract", "delete", "lock", "unlock"]
        
        for name in icon_names:
            icon_path = self.assets_dir / f"{name}.png"
            if icon_path.exists():
                try:
                    from PIL import Image
                    self.icons[name] = ctk.CTkImage(Image.open(icon_path))
                except Exception:
                    self.icons[name] = self._generate_fallback_icon(name)
            else:
                self.icons[name] = self._generate_fallback_icon(name)
    
    def _generate_fallback_icon(self, name: str) -> ctk.CTkImage:
        """Generate a simple fallback icon using PIL."""
        from PIL import Image, ImageDraw
        
        # Create a simple 32x32 image
        img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        if name == "folder":
            # Draw folder icon
            draw.rectangle([4, 12, 28, 24], fill=(255, 193, 7, 255))
            draw.rectangle([4, 8, 16, 12], fill=(255, 193, 7, 255))
        elif name == "file":
            # Draw file icon
            draw.rectangle([6, 4, 26, 28], fill=(33, 150, 243, 255))
            draw.rectangle([20, 4, 26, 10], fill=(255, 255, 255, 255))
        elif name == "add":
            # Draw plus icon
            draw.rectangle([4, 14, 28, 18], fill=(76, 175, 80, 255))
            draw.rectangle([14, 4, 18, 28], fill=(76, 175, 80, 255))
        elif name == "extract":
            # Draw arrow icon
            draw.polygon([(16, 6), (10, 16), (13, 16), (13, 26), (19, 26), (19, 16), (22, 16)], 
                        fill=(156, 39, 176, 255))
        elif name == "delete":
            # Draw X icon
            draw.rectangle([4, 4, 28, 28], fill=(244, 67, 54, 255))
            draw.rectangle([10, 14, 22, 18], fill=(255, 255, 255, 255))
            draw.rectangle([14, 10, 18, 22], fill=(255, 255, 255, 255))
        elif name == "lock":
            # Draw lock icon
            draw.rectangle([8, 14, 24, 24], fill=(96, 125, 139, 255))
            draw.rectangle([10, 8, 22, 14], fill=(0, 0, 0, 0), outline=(96, 125, 139, 255), width=2)
        elif name == "unlock":
            # Draw unlock icon
            draw.rectangle([8, 14, 24, 24], fill=(76, 175, 80, 255))
            draw.rectangle([14, 8, 22, 14], fill=(0, 0, 0, 0), outline=(76, 175, 80, 255), width=2)
        
        return ctk.CTkImage(img)
    
    def get_icon(self, name: str) -> Optional[ctk.CTkImage]:
        """Get an icon by name."""
        return self.icons.get(name)


class LoginScreen(ctk.CTkFrame):
    """Login screen for vault access."""
    
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the login screen UI."""
        # Configure grid for centering
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)  # For footer space
        
        # Main container - centered
        self.container = ctk.CTkFrame(self, corner_radius=15, width=400, height=650)
        self.container.grid(row=1, column=0, sticky="nsew", padx=40, pady=20)
        self.container.grid_propagate(False)
        
        # Center content within container
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure(6, weight=1)
        
        # Title
        self.title_label = ctk.CTkLabel(
            self.container,
            text="🔐 Hemliga valvet",
            font=ctk.CTkFont(size=32, weight="bold")
        )
        self.title_label.grid(row=0, column=0, pady=(30, 10))
        
        self.subtitle_label = ctk.CTkLabel(
            self.container,
            text="Säkert filvalv med AES-256-GCM kryptering",
            font=ctk.CTkFont(size=14),
            text_color="gray60"
        )
        self.subtitle_label.grid(row=1, column=0, pady=(0, 20))
        
        # Info box
        self.info_frame = ctk.CTkFrame(self.container, fg_color=("gray90", "gray20"))
        self.info_frame.grid(row=2, column=0, pady=(0, 20), padx=40, sticky="ew")
        self.info_frame.grid_columnconfigure(0, weight=1)
        
        self.info_label = ctk.CTkLabel(
            self.info_frame,
            text="ℹ️ Om du får åtkomstfel, kör programmet som administratör\neller välj en annan plats för valvfilen.",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray70"),
            justify="center"
        )
        self.info_label.grid(row=0, column=0, pady=10, padx=15, sticky="ew")
        
        # Password input
        self.password_frame = ctk.CTkFrame(self.container)
        self.password_frame.grid(row=3, column=0, pady=20, padx=40, sticky="ew")
        self.password_frame.grid_columnconfigure(0, weight=1)
        
        self.password_label = ctk.CTkLabel(
            self.password_frame,
            text="🔑 Lösenord:",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.password_label.grid(row=0, column=0, pady=(10, 5), sticky="w")
        
        self.password_entry = ctk.CTkEntry(
            self.password_frame,
            show="*",
            placeholder_text="Ange ditt lösenord...",
            font=ctk.CTkFont(size=14),
            height=45,
            border_width=2
        )
        self.password_entry.grid(row=1, column=0, pady=(0, 10), sticky="ew")
        self.password_entry.bind("<Return>", lambda e: self._unlock_vault())
        # self.password_entry.bind("<KeyRelease>", self._on_password_change)
        
        # Buttons
        self.button_frame = ctk.CTkFrame(self.container)
        self.button_frame.grid(row=4, column=0, pady=20, padx=40, sticky="ew")
        self.button_frame.grid_columnconfigure(0, weight=1)
        
        self.unlock_button = ctk.CTkButton(
            self.button_frame,
            text="🔓 Lås upp valvet",
            font=ctk.CTkFont(size=16, weight="bold"),
            height=50,
            command=self._unlock_vault,
            fg_color="#1e3a8a",
            hover_color="#1e40af"
        )
        self.unlock_button.grid(row=0, column=0, pady=10, sticky="ew")
        
        self.create_button = ctk.CTkButton(
            self.button_frame,
            text="➕ Skapa nytt valv",
            font=ctk.CTkFont(size=16),
            height=50,
            command=self._create_vault,
            fg_color="transparent",
            border_width=2,
            text_color=("#1e3a8a", "#60a5fa")
        )
        self.create_button.grid(row=1, column=0, pady=(0, 10), sticky="ew")
        
        # Password strength indicator
        self.strength_frame = ctk.CTkFrame(self.container)
        self.strength_frame.grid(row=6, column=0, pady=(5, 0), padx=40, sticky="ew")
        self.strength_frame.grid_columnconfigure(0, weight=1)
        
        self.strength_label = ctk.CTkLabel(
            self.strength_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="gray50"
        )
        self.strength_label.grid(row=0, column=0, sticky="w", padx=10, pady=5)
        
        # Temporarily remove progress bar to test
        # self.strength_progress = ctk.CTkProgressBar(self.strength_frame, height=4)
        # self.strength_progress.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 5))
        # self.strength_progress.set(0)
        
        # Status label
        self.status_label = ctk.CTkLabel(
            self.container,
            text="",
            font=ctk.CTkFont(size=12)
        )
        self.status_label.grid(row=5, column=0, pady=(10, 0))
        
        # Version footer
        self.version_frame = ctk.CTkFrame(self, corner_radius=0, height=40)
        self.version_frame.grid(row=2, column=0, sticky="ew", padx=0, pady=0)
        self.version_frame.grid_propagate(False)
        
        self.version_label = ctk.CTkLabel(
            self.version_frame,
            text="Hemliga valvet v1.0 | © 2025 | AES-256-GCM | Bcrypt",
            font=ctk.CTkFont(size=11),
            text_color="gray50"
        )
        self.version_label.pack(side="right", padx=20, pady=10)
    
    def _unlock_vault(self):
        """Handle vault unlock."""
        print("DEBUG: _unlock_vault called")  # Debug output
        password = self.password_entry.get()
        print(f"DEBUG: Password entered: '{password}'")  # Debug output
        
        # Temporarily remove password validation
        # is_valid, issues = PasswordStrength.validate_password(password)
        # if not is_valid and len(password) > 0:
        #     issue_text = ", ".join(issues[:3])  # Show max 3 issues
        #     self.status_label.configure(text=f"Svagt lösenord: {issue_text}", text_color="orange")
        #     return
        
        if not password:
            print("DEBUG: No password entered")  # Debug output
            self.status_label.configure(text="Ange ett lösenord", text_color="red")
            return
        
        print("DEBUG: Calling app.unlock_vault")  # Debug output
        # Let app handle the unlock
        self.app.unlock_vault(password)
    
    def _create_vault(self):
        """Handle new vault creation."""
        print("DEBUG: _create_vault called")  # Debug output
        password = self.password_entry.get()
        print(f"DEBUG: Password entered: '{password}'")  # Debug output
        
        if not password:
            print("DEBUG: No password entered")  # Debug output
            self.status_label.configure(text="Ange ett lösenord", text_color="red")
            return
        
        print("DEBUG: Calling app.create_new_vault")  # Debug output
        self.app.create_new_vault(password)
    
    # Temporarily remove password change handler
    # def _on_password_change(self, event):
    #     """Handle password change for strength indicator."""
    #     password = self.password_entry.get()
    #     
    #     if not password:
    #         self.strength_label.configure(text="")
    #         # self.strength_progress.set(0)
    #         return
    #     
    #     score = PasswordStrength.get_strength_score(password)
    #     strength_text = PasswordStrength.get_strength_text(score)
    #     
    #     # Update progress bar color based on strength
    #     if score < 30:
    #         color = "red"
    #     elif score < 50:
    #         color = "orange"
    #     elif score < 70:
    #         color = "yellow"
    #     elif score < 90:
    #         color = "green"
    #     else:
    #         color = "dark green"
    #     
    #     # self.strength_progress.set(score / 100)
    #     self.strength_label.configure(text=f"Styrka: {strength_text} ({score}/100)")
    #     
    #     # Validate and show issues
    #     is_valid, issues = PasswordStrength.validate_password(password)
    #     if not is_valid and len(password) > 0:
    #         issue_text = ", ".join(issues[:2])
    #         self.status_label.configure(text=f"Saknas: {issue_text}", text_color="orange")
    #     else:
    #         self.status_label.configure(text="", text_color="green")
    
    def show_error(self, message: str):
        """Show error message."""
        self.status_label.configure(text=message, text_color="red")
    
    def show_success(self, message: str):
        """Show success message."""
        self.status_label.configure(text=message, text_color="green")
    
    def clear_password(self):
        """Clear password field."""
        self.password_entry.delete(0, "end")


class MainInterface(ctk.CTkFrame):
    """Main vault interface."""
    
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.vfs: Optional[VirtualFileSystem] = None
        self.selected_files = []
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the main interface UI."""
        # Configure grid layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Sidebar
        self._setup_sidebar()
        
        # Main content area
        self._setup_main_area()
        
        # Toolbar
        self._setup_toolbar()
        
        # Footer
        self._setup_footer()
    
    def _setup_sidebar(self):
        """Setup the sidebar with folder tree."""
        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=(0, 2))
        self.sidebar.grid_propagate(False)
        
        # Sidebar title
        self.sidebar_title = ctk.CTkLabel(
            self.sidebar,
            text="Filer",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.sidebar_title.pack(pady=(10, 5), padx=10)
        
        # File tree
        self.file_tree = ctk.CTkScrollableFrame(self.sidebar)
        self.file_tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        self._refresh_file_tree()
    
    def _setup_main_area(self):
        """Setup the main content area."""
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=(2, 0))
        
        # File list
        self.file_list_frame = ctk.CTkFrame(self.main_frame)
        self.file_list_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # List headers
        self.list_header = ctk.CTkFrame(self.file_list_frame, height=30)
        self.list_header.pack(fill="x", padx=5, pady=(5, 0))
        self.list_header.grid_propagate(False)
        
        self.list_header.grid_columnconfigure(0, weight=1)
        self.list_header.grid_columnconfigure(1, weight=0)
        self.list_header.grid_columnconfigure(2, weight=0)
        
        ctk.CTkLabel(self.list_header, text="Namn", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w", padx=5)
        ctk.CTkLabel(self.list_header, text="Storlek", font=ctk.CTkFont(weight="bold")).grid(row=0, column=1, sticky="w", padx=5)
        ctk.CTkLabel(self.list_header, text="Ändrad", font=ctk.CTkFont(weight="bold")).grid(row=0, column=2, sticky="w", padx=5)
        
        # File list scrollable frame
        self.file_list = ctk.CTkScrollableFrame(self.file_list_frame)
        self.file_list.pack(fill="both", expand=True, padx=5, pady=(0, 5))
        
        self._refresh_file_list()
    
    def _setup_toolbar(self):
        """Setup the toolbar."""
        self.toolbar = ctk.CTkFrame(self.main_frame, height=50)
        self.toolbar.pack(fill="x", padx=10, pady=(0, 10))
        self.toolbar.grid_propagate(False)
        
        # Toolbar buttons
        self.add_button = ctk.CTkButton(
            self.toolbar,
            text="Lägg till fil",
            command=self._add_files,
            width=120
        )
        self.add_button.pack(side="left", padx=5, pady=10)
        
        self.extract_button = ctk.CTkButton(
            self.toolbar,
            text="Extrahera",
            command=self._extract_files,
            width=120
        )
        self.extract_button.pack(side="left", padx=5, pady=10)
        
        self.delete_button = ctk.CTkButton(
            self.toolbar,
            text="Ta bort",
            command=self._delete_files,
            width=120,
            fg_color="red"
        )
        self.delete_button.pack(side="left", padx=5, pady=10)
        
        # Status label
        self.status_label = ctk.CTkLabel(self.toolbar, text="")
        self.status_label.pack(side="right", padx=10, pady=10)
    
    def _setup_footer(self):
        """Setup the footer."""
        self.footer = ctk.CTkFrame(self.main_frame, height=40)
        self.footer.pack(fill="x", side="bottom", padx=0, pady=0)
        self.footer.grid_propagate(False)
        
        self.footer_label = ctk.CTkLabel(
            self.footer,
            text="Hemliga valvet v1.0 | © 2025 | AES-256-GCM | Argon2id",
            font=ctk.CTkFont(size=11),
            text_color="gray50"
        )
        self.footer_label.pack(side="right", padx=20, pady=10)
    
    def set_vfs(self, vfs: VirtualFileSystem):
        """Set the virtual file system."""
        self.vfs = vfs
        self._refresh_file_tree()
        self._refresh_file_list()

    def _refresh_file_tree(self):
        """Refresh the file tree sidebar."""
        # Clear existing widgets
        for widget in self.file_tree.winfo_children():
            widget.destroy()

        if not self.vfs:
            return

        # Get directory tree
        tree = self.vfs.get_directory_tree()
        self._build_tree_items(tree, self.file_tree, "")

    def _build_tree_items(self, tree: dict, parent, path: str):
        """Recursively build tree items."""
        for name, item in tree.items():
            item_path = f"{path}/{name}" if path else f"/{name}"

            if isinstance(item, dict) and "offset" not in item:
                # This is a directory
                frame = ctk.CTkFrame(parent)
                frame.pack(fill="x", pady=2)

                label = ctk.CTkLabel(frame, text=f"📁 {name}")
                label.pack(side="left", padx=5)

                # Recursively add children
                self._build_tree_items(item, parent, item_path)
            else:
                # This is a file
                frame = ctk.CTkFrame(parent)
                frame.pack(fill="x", pady=2)

                label = ctk.CTkLabel(frame, text=f"📄 {name}")
                label.pack(side="left", padx=5)

    def _refresh_file_list(self):
        """Refresh the file list."""
        # Clear existing widgets
        for widget in self.file_list.winfo_children():
            widget.destroy()
        
        if not self.vfs:
            return
        
        # Add files to list
        for file_path in self.vfs.list_files():
            file_info = self.vfs.get_file_info(file_path)
            if file_info:
                self._add_file_item(file_path, file_info)
    
    def _add_file_item(self, file_path: str, file_info: dict):
        """Add a file item to the list."""
        frame = ctk.CTkFrame(self.file_list)
        frame.pack(fill="x", pady=2)
        
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=0)
        frame.grid_columnconfigure(2, weight=0)
        
        # Checkbox for selection
        var = tk.BooleanVar()
        checkbox = ctk.CTkCheckBox(frame, text="", variable=var)
        checkbox.grid(row=0, column=0, sticky="w", padx=5)
        
        # File name
        name_label = ctk.CTkLabel(frame, text=file_path.split("/")[-1])
        name_label.grid(row=0, column=0, sticky="w", padx=(25, 5))
        
        # File size
        size_text = self._format_size(file_info["size"])
        size_label = ctk.CTkLabel(frame, text=size_text)
        size_label.grid(row=0, column=1, sticky="w", padx=5)
        
        # Modified date
        modified_label = ctk.CTkLabel(frame, text=file_info.get("modified", ""))
        modified_label.grid(row=0, column=2, sticky="w", padx=5)
        
        # Store selection info
        checkbox.file_path = file_path
        checkbox.var = var
        var.trace("w", lambda *args: self._update_selection())
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human readable format."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
    
    def _update_selection(self):
        """Update selected files list."""
        self.selected_files = []
        for widget in self.file_list.winfo_children():
            if hasattr(widget, 'winfo_children'):
                for child in widget.winfo_children():
                    if hasattr(child, 'var') and child.var.get():
                        self.selected_files.append(child.file_path)
        
        # Update button states
        self.extract_button.configure(state="normal" if self.selected_files else "disabled")
        self.delete_button.configure(state="normal" if self.selected_files else "disabled")
    
    def _add_files(self):
        """Handle add files button click."""
        if not self.vfs:
            return
        
        file_paths = self.app.async_ops.show_multiple_files_dialog("Välj filer att lägga till")
        if file_paths:
            self.app.add_files_to_vault([Path(p) for p in file_paths])
    
    def _extract_files(self):
        """Handle extract files button click."""
        if not self.vfs or not self.selected_files:
            return
        
        extract_dir = self.app.async_ops.show_file_dialog("Välj extraheringsmapp", mode="directory")
        if extract_dir:
            self.app.extract_files_from_vault(self.selected_files, extract_dir)
    
    def _delete_files(self):
        """Handle delete files button click."""
        if not self.vfs or not self.selected_files:
            return
        
        if messagebox.askyesno("Bekräfta", f"Ta bort {len(self.selected_files)} fil(er) från valvet?"):
            self.app.delete_files_from_vault(self.selected_files)
    
    def show_status(self, message: str, color: str = "black"):
        """Show status message."""
        self.status_label.configure(text=message, text_color=color)


class VaultApp(ctk.CTk):
    """Main application class."""
    
    def __init__(self):
        super().__init__()
        
        # Configure app
        self.title("Hemliga valvet")
        self.geometry("900x600")
        self.minsize(800, 500)
        
        # Set theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Initialize components
        self.assets_dir = Path(__file__).parent.parent / "assets"
        self.icon_loader = IconLoader(self.assets_dir)
        self.async_ops = AsyncOperations(self)
        # self.session_manager = SessionManager(timeout_minutes=15, lock_callback=self._on_session_timeout)
        
        self.vfs: Optional[VirtualFileSystem] = None
        self.vault_path: Optional[str] = None
        self.password: Optional[str] = None
        
        # Setup UI
        self._setup_ui()
        
        # Center window
        self._center_window()
        
        # Bind activity events
        # self._bind_activity_events()
    
    def _setup_ui(self):
        """Setup the main UI."""
        # Configure main window grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Login screen (initial)
        self.login_screen = LoginScreen(self, self)
        self.login_screen.grid(row=0, column=0, sticky="nsew")
        
        # Main interface (hidden initially)
        self.main_interface = MainInterface(self, self)
    
    def _center_window(self):
        """Center the window on screen."""
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (self.winfo_width() // 2)
        y = (self.winfo_screenheight() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")
    
    def create_new_vault(self, password: str):
        """Create a new vault."""
        print("DEBUG: create_new_vault called")  # Debug output
        
        # Show file dialog to choose vault location
        def on_file_selected(vault_path):
            if not vault_path:
                print("DEBUG: No vault path selected")  # Debug output
                return
            
            print(f"DEBUG: Vault path selected: {vault_path}")  # Debug output
            
            # ULTRA SIMPLE TEST - Try to create a simple file first
            import os
            try:
                print(f"DEBUG: Testing simple file creation at: {vault_path}")  # Debug output
                with open(vault_path, 'w') as f:
                    f.write("test")
                print("DEBUG: Simple file creation SUCCESS!")  # Debug output
                os.remove(vault_path)  # Clean up test file
                print("DEBUG: Test file cleaned up")  # Debug output
            except Exception as e:
                print(f"DEBUG: Simple file creation FAILED: {e}")  # Debug output
                self.login_screen.show_error(f"FILTEST MISSLYCKADES: {e}. Välj en annan plats!")
                return
            
            # If simple file works, try vault creation
            self.vault_path = vault_path
            self.password = password
            
            # Create vault asynchronously
            print("DEBUG: About to call async_ops.create_vault")  # Debug output
            self.async_ops.create_vault(vault_path, password, self._on_vault_created)
            print("DEBUG: async_ops.create_vault called")  # Debug output
        
        # Show file dialog
        print("DEBUG: Showing file dialog for vault creation")  # Debug output
        self.async_ops.show_file_dialog(
            "Spara valvfil",
            [("Valvfiler", "*.vault"), ("Alla filer", "*.*")],
            "save"
        ).add_done_callback(lambda future: on_file_selected(future.result()))
    
    def unlock_vault(self, password: str):
        """Unlock existing vault."""
        print("DEBUG: unlock_vault called")  # Debug output
        
        # Show file dialog to choose vault file
        def on_file_selected(vault_path):
            if not vault_path:
                print("DEBUG: No vault path selected")  # Debug output
                return
            
            print(f"DEBUG: Vault path selected: {vault_path}")  # Debug output
            
            # Check if file exists
            import os
            if not os.path.exists(vault_path):
                print(f"DEBUG: Vault file does not exist: {vault_path}")  # Debug output
                self.login_screen.show_error(f"Valvfilen finns inte: {vault_path}")
                return
            
            self.vault_path = vault_path
            self.password = password
            
            # Open vault asynchronously
            print("DEBUG: About to call async_ops.open_vault")  # Debug output
            self.async_ops.open_vault(vault_path, password, self._on_vault_opened)
            print("DEBUG: async_ops.open_vault called")  # Debug output
        
        # Show file dialog
        print("DEBUG: Showing file dialog for vault opening")  # Debug output
        self.async_ops.show_file_dialog(
            "Öppna valvfil",
            [("Valvfiler", "*.vault"), ("Alla filer", "*.*")],
            "open"
        ).add_done_callback(lambda future: on_file_selected(future.result()))
    
    def _on_vault_created(self, result: OperationResult):
        """Handle vault creation completion."""
        if result.success:
            self.login_screen.show_success("Valv skapat! Använd 'Lås upp valv' för att öppna det.")
            # Don't auto-open - let user manually unlock
            # self.async_ops.open_vault(self.vault_path, self.password, self._on_vault_opened)
        else:
            self.login_screen.show_error(f"Kunde inte skapa valv: {result.error}")
    
    def _on_vault_opened(self, result: OperationResult):
        """Handle vault opening completion."""
        if result.success:
            self.vfs = result.data
            self._show_main_interface()
        else:
            self.login_screen.show_error(f"Kunde inte öppna valv: {result.error}")
            self.login_screen.clear_password()
    
    def _show_main_interface(self):
        """Switch to main interface."""
        self.login_screen.grid_forget()
        self.main_interface.grid(row=0, column=0, sticky="nsew")
        self.main_interface.set_vfs(self.vfs)
        
        # Temporarily remove session monitoring
        # self.session_manager.start_session()
    
    # Temporarily remove session timeout functions
    # def _on_session_timeout(self):
    #     """Handle session timeout."""
    #     if self.vfs:  # Only timeout if vault is open
    #         messagebox.showwarning(
    #             "Session timeout", 
    #             "Din session har löpt ut av inaktivitet. Valvet låses för säkerhet."
    #         )
    #         self._lock_vault()
    # 
    # def _lock_vault(self):
    #     """Lock the vault and return to login screen."""
    #     # Stop session monitoring
    #     self.session_manager.stop_session()
    #     
    #     # Clear sensitive data
    #     self.vfs = None
    #     self.vault_path = None
    #     self.password = None
    #     
    #     # Return to login screen
    #     self.main_interface.grid_forget()
    #     self.login_screen.grid(row=0, column=0, sticky="nsew")
    #     self.login_screen.clear_password()
    #     self.login_screen.show_status("Valvet låst", "green")
    # 
    # def _bind_activity_events(self):
    #     """Bind events that indicate user activity."""
    #     # Bind mouse movement and clicks
    #     self.bind("<Motion>", lambda e: self.session_manager.update_activity())
    #     self.bind("<Button-1>", lambda e: self.session_manager.update_activity())
    #     self.bind("<Key>", lambda e: self.session_manager.update_activity())
    #     
    #     # Bind window focus
    #     self.bind("<FocusIn>", lambda e: self.session_manager.update_activity())
    
    def add_files_to_vault(self, file_paths: List[Path]):
        """Add files to vault."""
        if not self.vfs:
            return
        
        self.async_ops.add_files(self.vfs, file_paths, self._on_files_added)
    
    def _on_files_added(self, result: OperationResult):
        """Handle file addition completion."""
        if result.success:
            self.main_interface._refresh_file_tree()
            self.main_interface._refresh_file_list()
            self.main_interface.show_status(f"{len(result.data)} fil(er) tillagda", "green")
        else:
            self.main_interface.show_status(f"Fel vid tillägg: {result.error}", "red")
    
    def extract_files_from_vault(self, vault_paths: List[str], extract_dir: str):
        """Extract files from vault."""
        if not self.vfs:
            return
        
        self.async_ops.extract_files(self.vfs, vault_paths, extract_dir, self._on_files_extracted)
    
    def _on_files_extracted(self, result: OperationResult):
        """Handle file extraction completion."""
        if result.success:
            self.main_interface.show_status(f"{len(result.data)} fil(er) extraherade", "green")
        else:
            self.main_interface.show_status(f"Fel vid extrahering: {result.error}", "red")
    
    def delete_files_from_vault(self, vault_paths: List[str]):
        """Delete files from vault."""
        if not self.vfs:
            return
        
        self.async_ops.remove_files(self.vfs, vault_paths, self._on_files_deleted)
    
    def _on_files_deleted(self, result: OperationResult):
        """Handle file deletion completion."""
        if result.success:
            self.main_interface._refresh_file_tree()
            self.main_interface._refresh_file_list()
            self.main_interface.show_status(f"{len(result.data)} fil(er) borttagna", "green")
        else:
            self.main_interface.show_status(f"Fel vid borttagning: {result.error}", "red")
    
    def on_closing(self):
        """Handle application closing."""
        if self.vfs and self.vfs.is_dirty():
            if messagebox.askyesno("Osparade ändringar", "Det finns osparade ändringar. Vill du spara innan du stänger?"):
                self.async_ops.save_vault(self.vfs, self.password, lambda result: self.destroy())
                return
        
        # 🔒 Critical: Clear sensitive data from memory
        if self.password:
            self.password = None
        if self.vault_path:
            self.vault_path = None
        
        self.destroy()


def main():
    """Main entry point."""
    app = VaultApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()


if __name__ == "__main__":
    main()
