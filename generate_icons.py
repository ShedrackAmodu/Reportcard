#!/usr/bin/env python3
"""
Generate PWA icons for ReportCardApp
Creates 192x192 and 512x512 PNG icons
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_icon(size, filename):
    """Create a simple gradient icon with 'RCA' text"""
    # Create image with transparent background
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Create gradient background (blue to purple)
    for y in range(size):
        r = int(0 + (102 - 0) * (y / size))
        g = int(123 + (75 - 123) * (y / size))
        b = int(255 + (102 - 255) * (y / size))
        for x in range(size):
            draw.point((x, y), (r, g, b))

    # Add white circle in center
    circle_center = (size // 2, size // 2)
    circle_radius = size // 3
    draw.ellipse(
        [(circle_center[0] - circle_radius, circle_center[1] - circle_radius),
         (circle_center[0] + circle_radius, circle_center[1] + circle_radius)],
        fill='white'
    )

    # Add 'SS' text
    try:
        # Try to use a system font
        font_size = size // 3
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        # Fallback to default font
        font = ImageFont.load_default()
        font_size = size // 4

    text = "RCA"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    text_x = (size - text_width) // 2
    text_y = (size - text_height) // 2

    draw.text((text_x, text_y), text, fill='#007bff', font=font)

    # Save the image
    img.save(filename, 'PNG')
    print(f"Created {filename} ({size}x{size})")

def main():
    # Create images directory if it doesn't exist
    images_dir = os.path.join('schools', 'static', 'schools', 'images')
    os.makedirs(images_dir, exist_ok=True)

    # Generate icons
    create_icon(192, os.path.join(images_dir, 'icon-192.png'))
    create_icon(512, os.path.join(images_dir, 'icon-512.png'))

    print("PWA icons generated successfully!")

if __name__ == '__main__':
    main()
