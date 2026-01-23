#!/usr/bin/env python3
"""
Generate placeholder screenshots for PWABuilder
Creates wide (1280x720) and narrow (390x844) PNG screenshots
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_screenshot(width, height, filename, title, subtitle):
    """Create a placeholder screenshot with app branding"""
    # Create image with white background
    img = Image.new('RGB', (width, height), '#ffffff')
    draw = ImageDraw.Draw(img)

    # Add a subtle background pattern
    for y in range(0, height, 20):
        draw.line([(0, y), (width, y)], fill='#f8f9fa', width=1)

    # Add header bar (like the app's navigation)
    header_height = 60
    draw.rectangle([(0, 0), (width, header_height)], fill='#007bff')

    # Add app title in header
    try:
        font_large = ImageFont.truetype("arial.ttf", 24)
        font_medium = ImageFont.truetype("arial.ttf", 18)
        font_small = ImageFont.truetype("arial.ttf", 14)
    except:
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Header text
    draw.text((20, 15), "ReportCardApp", fill='white', font=font_large)

    # Main content area
    content_y = header_height + 40

    # Title
    title_bbox = draw.textbbox((0, 0), title, font=font_large)
    title_width = title_bbox[2] - title_bbox[0]
    title_x = (width - title_width) // 2
    draw.text((title_x, content_y), title, fill='#333333', font=font_large)

    # Subtitle
    content_y += 60
    subtitle_bbox = draw.textbbox((0, 0), subtitle, font=font_medium)
    subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
    subtitle_x = (width - subtitle_width) // 2
    draw.text((subtitle_x, content_y), subtitle, fill='#666666', font=font_medium)

    # Add some mock content cards
    content_y += 80
    card_width = min(300, width - 40)
    card_height = 100
    card_x = (width - card_width) // 2

    for i in range(3):
        # Card background
        draw.rectangle([(card_x, content_y), (card_x + card_width, content_y + card_height)],
                      fill='#f8f9fa', outline='#dee2e6')

        # Card content
        draw.text((card_x + 15, content_y + 15), f"Sample Content {i+1}", fill='#333333', font=font_medium)
        draw.text((card_x + 15, content_y + 45), "Description text here", fill='#666666', font=font_small)

        content_y += card_height + 20

    # Add bottom navigation (mobile style)
    if height > 700:  # Only for taller screenshots
        nav_y = height - 80
        nav_height = 60
        draw.rectangle([(0, nav_y), (width, height)], fill='#f8f9fa')

        # Navigation items
        nav_items = ["Dashboard", "Grades", "Attendance", "Reports"]
        item_width = width // len(nav_items)

        for i, item in enumerate(nav_items):
            item_x = i * item_width + item_width // 2
            item_bbox = draw.textbbox((0, 0), item, font=font_small)
            item_width_actual = item_bbox[2] - item_bbox[0]
            draw.text((item_x - item_width_actual // 2, nav_y + 20), item, fill='#666666', font=font_small)

    # Save the image
    img.save(filename, 'PNG')
    print(f"Created {filename} ({width}x{height})")

def main():
    # Create images directory if it doesn't exist
    images_dir = os.path.join('schools', 'static', 'schools', 'images')
    os.makedirs(images_dir, exist_ok=True)

    # Generate screenshots
    create_screenshot(1280, 720, os.path.join(images_dir, 'screenshot-wide.png'),
                     "School Management Dashboard", "Multi-tenant Report Card System")

    create_screenshot(390, 844, os.path.join(images_dir, 'screenshot-narrow.png'),
                     "Student Grades", "View and manage academic performance")

    print("PWABuilder screenshots generated successfully!")

if __name__ == '__main__':
    main()
