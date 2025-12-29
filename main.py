#!/usr/bin/env python3
"""
Hemliga valvet - Secure Vault Application
Main entry point for the encrypted file vault application.

Features:
- AES-256-GCM encryption
- Argon2id key derivation
- Atomic file saves
- Cross-platform compatibility
- Modern GUI with CustomTkinter
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Check Python version
if sys.version_info < (3, 11):
    print("Error: Hemliga valvet requires Python 3.11 or higher")
    sys.exit(1)

# Import the GUI application
from ui.gui import main as gui_main


def check_dependencies():
    """Check if required dependencies are installed."""
    required_packages = [
        "cryptography",
        "customtkinter", 
        "argon2_cffi",
        "portalocker",
        "PIL"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == "PIL":
                import PIL
            elif package == "argon2_cffi":
                import argon2
            else:
                __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("Error: Missing required dependencies:")
        for package in missing_packages:
            print(f"  - {package}")
        print("\nInstall dependencies with:")
        print("pip install -r requirements.txt")
        return False
    
    return True


def main():
    """Main entry point."""
    print("Hemliga valvet v1.0 - Säker filkryptering")
    print("=" * 50)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Start GUI
    try:
        gui_main()
    except KeyboardInterrupt:
        print("\nAvbrytet av användare")
        sys.exit(0)
    except Exception as e:
        print(f"Ett oväntat fel uppstod: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
