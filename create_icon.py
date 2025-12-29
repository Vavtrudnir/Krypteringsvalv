#!/usr/bin/env python3
"""
Create a simple icon for Hemliga valvet.
"""

from PIL import Image, ImageDraw
import os

def create_icon():
    """Create a simple lock icon."""
    # Create a 256x256 image
    img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw lock background
    draw.ellipse([40, 100, 216, 220], fill=(30, 58, 138, 255))  # Blue background
    draw.ellipse([50, 110, 206, 210], fill=(59, 130, 246, 255))  # Lighter blue
    
    # Draw lock shackle
    draw.rectangle([90, 60, 110, 100], fill=(30, 58, 138, 255))
    draw.rectangle([146, 60, 166, 100], fill=(30, 58, 138, 255))
    draw.arc([80, 40, 176, 120], 0, 180, fill=(30, 58, 138, 255), width=30)
    
    # Draw keyhole
    draw.ellipse([118, 140, 138, 160], fill=(255, 255, 255, 255))
    draw.rectangle([124, 160, 132, 180], fill=(255, 255, 255, 255))
    
    # Save as ICO
    img.save('assets/icon.ico', sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
    print("Icon created successfully!")

if __name__ == "__main__":
    create_icon()
