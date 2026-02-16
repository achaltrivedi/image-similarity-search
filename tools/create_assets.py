import os
import sys
from PIL import Image

def create_placeholders():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir) # tools -> root
    images_dir = os.path.join(project_root, "images")
    
    os.makedirs(images_dir, exist_ok=True)
    
    # 1. Placeholder (Gray 200x200)
    img = Image.new('RGB', (200, 200), color='lightgray')
    img.save(os.path.join(images_dir, "placeholder.png"))
    print(f"Created {os.path.join(images_dir, 'placeholder.png')}")

    # 2. Error (Red 200x200)
    img_err = Image.new('RGB', (200, 200), color='salmon')
    img_err.save(os.path.join(images_dir, "error.png"))
    print(f"Created {os.path.join(images_dir, 'error.png')}")

if __name__ == "__main__":
    create_placeholders()
