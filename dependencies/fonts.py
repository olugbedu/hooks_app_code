import os
import platform
import shutil

def install_fonts():
    """Install fonts based on the operating system."""
    fonts_dir = 'dependencies/fonts'  # Directory containing font files

    # Check if the fonts directory exists
    if not os.path.exists(fonts_dir):
        print(f"Directory {fonts_dir} does not exist.")
        return

    # List all .ttf and .otf font files in the directory
    font_files = [f for f in os.listdir(fonts_dir) if f.endswith(('.ttf', '.otf'))]

    # If no font files are found, exit the function
    if not font_files:
        print("No .ttf or .otf font files found in the directory.")
        return

    # Determine the operating system
    system = platform.system()

    # Install fonts based on the operating system
    if system == 'Windows':
        install_fonts_windows(font_files, fonts_dir)
    elif system == 'Darwin':
        install_fonts_macos(font_files, fonts_dir)
    else:
        print(f"Unsupported operating system: {system}")

def install_fonts_windows(font_files, fonts_dir):
    """Install fonts on Windows."""
    fonts_dest_dir = os.path.join(os.environ['WINDIR'], 'Fonts')
    for font in font_files:
        src_font_path = os.path.join(fonts_dir, font)
        dest_font_path = os.path.join(fonts_dest_dir, font)
        print(f"Installing {font} to {fonts_dest_dir}")
        shutil.copy(src_font_path, dest_font_path)
        # Register the font in the Windows registry
        os.system(f'REG ADD "HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Fonts" /v "{font}" /t REG_SZ /d "{font}" /f')
    print("Fonts installed on Windows.")

def install_fonts_macos(font_files, fonts_dir):
    """Install fonts on macOS."""
    fonts_dest_dir = os.path.expanduser('~/Library/Fonts')
    for font in font_files:
        src_font_path = os.path.join(fonts_dir, font)
        dest_font_path = os.path.join(fonts_dest_dir, font)
        print(f"Installing {font} to {fonts_dest_dir}")
        shutil.copy(src_font_path, dest_font_path)
    print("Fonts installed on macOS.")

def font_exists(font_name):
    """Check if a font exists in the system's font directory."""
    system = platform.system()
    print(system)

    if system == 'Windows':
        fonts_dest_dir = os.path.join(os.environ['WINDIR'], 'dependencies/fonts')
    elif system in ['Darwin', 'Linux']:
        fonts_dest_dir = os.path.join(os.getcwd(), 'dependencies/fonts')
    else:
        return False

    # Check if the font file exists in the destination directory
    return os.path.exists(os.path.join(fonts_dest_dir, font_name))
