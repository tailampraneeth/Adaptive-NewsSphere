import os
from PIL import Image

def make_favicon():
    logo_path = r"E:\News\frontend\public\logo.jpg"
    png_path = r"E:\News\frontend\public\logo.png"
    ico_path = r"E:\News\frontend\public\favicon.ico"
    
    print(f"Loading logo from {logo_path}...")
    img = Image.open(logo_path)
    
    # Save as PNG
    print(f"Saving as PNG to {png_path}...")
    img.save(png_path, "PNG")
    
    # Save as ICO (commonly 32x32)
    print(f"Saving as ICO to {ico_path}...")
    img_ico = img.resize((32, 32), Image.Resampling.LANCZOS)
    img_ico.save(ico_path, format="ICO")
    print("Favicon creation completed!")

if __name__ == "__main__":
    make_favicon()
