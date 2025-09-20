#!/usr/bin/env python3
"""
Generate Play Store icon (512x512 PNG) from the app's vector drawable
"""

import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw
import re
import math

def parse_svg_path(path_data):
    """Parse SVG path data and return drawing commands"""
    commands = []
    # Simple SVG path parser for the specific path in our icon
    # M24,2C22.09,2 20.25,2.64 18.78,3.78L12,10.5L5.22,3.78C3.75,2.64 1.91,2 0,2H24M24,8C24,9.1 23.1,10 22,10C20.9,10 20,9.1 20,8C20,6.9 20.9,6 22,6C23.1,6 24,6.9 24,8M2,8C2,9.1 2.9,10 4,10C5.1,10 6,9.1 6,8C6,6.9 5.1,6 4,6C2.9,6 2,6.9 2,8M12,14L19,21H5L12,14Z
    
    # For this specific icon, we'll manually create the shape
    # It appears to be a classical column or temple-like design
    return path_data

def create_play_store_icon():
    # Create 512x512 image with green background
    size = 512
    img = Image.new('RGBA', (size, size), '#2E7D32')
    draw = ImageDraw.Draw(img)
    
    # Scale factor: original viewBox is 108x108, we translate by 30,30
    # So effective drawing area is 48x48 (from 30 to 78)
    # We want to fit this in the center of our 512x512 image with some padding
    
    padding = 80  # Padding around the icon
    draw_size = size - (2 * padding)  # 352x352 drawing area
    scale = draw_size / 48  # Scale from 48 units to 352 pixels
    
    # Offset to center the drawing
    offset_x = padding + (30 * scale)  # Account for the translation in the original
    offset_y = padding + (30 * scale)
    
    def transform_point(x, y):
        """Transform from original coordinates to our canvas"""
        return (x * scale + padding, y * scale + padding)
    
    # Draw the icon shape as polygons
    # This represents a stylized classical column/temple shape
    
    # Top part (triangular pediment)
    triangle_points = [
        transform_point(12, 14),  # Top center
        transform_point(19, 21),  # Bottom right
        transform_point(5, 21),   # Bottom left
    ]
    draw.polygon(triangle_points, fill='white')
    
    # Column bases - two circles
    # Left column base
    draw.ellipse([
        transform_point(2, 6),
        transform_point(6, 10)
    ], fill='white')
    
    # Right column base  
    draw.ellipse([
        transform_point(20, 6),
        transform_point(24, 10)
    ], fill='white')
    
    # Column shafts - vertical rectangles
    # Left column
    draw.rectangle([
        transform_point(3, 3.78),
        transform_point(5.22, 10.5)
    ], fill='white')
    
    # Right column
    draw.rectangle([
        transform_point(18.78, 3.78),
        transform_point(21, 10.5)
    ], fill='white')
    
    # Top horizontal beam
    draw.rectangle([
        transform_point(0, 2),
        transform_point(24, 3.78)
    ], fill='white')
    
    # Save the icon
    img.save('play_store_icon_new.png', 'PNG')
    print("Generated play_store_icon_new.png (512x512)")
    print("This icon represents a classical Greek temple facade, appropriate for a classics reader app")

if __name__ == "__main__":
    create_play_store_icon()