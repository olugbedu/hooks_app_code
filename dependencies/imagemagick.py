import subprocess
import platform

def is_imagemagick_installed():
    """
    Check if ImageMagick is installed on the system.
    
    Returns:
        bool: True if ImageMagick is installed, False otherwise.
    """
    # Determine the command based on the operating system
    command = "magick --version" if platform.system() == "Windows" else "convert --version"
    
    try:
        # Execute the command to check for ImageMagick installation
        subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError:
        # If the command fails, ImageMagick is not installed
        return False

def install_imagemagick():
    """
    Provide instructions to the user for installing ImageMagick.
    """
    print("ImageMagick is required but not found on your system.")
    
    if platform.system() == "Windows":
        # Provide download link for Windows users
        print("Please download and install ImageMagick from: https://imagemagick.org/script/download.php")
    else:
        # Suggest using a package manager for non-Windows users
        print("You can install ImageMagick using your package manager (e.g., 'brew install imagemagick' on macOS)")
