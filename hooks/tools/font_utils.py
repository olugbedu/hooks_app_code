# Utility functions used to process fonts
import logging
import tempfile
import os
import subprocess

logging.basicConfig(level=logging.basicConfig)

def setup_fontconfig(font_path):
    # Step 1: Create a temporary directory
    temp_dir = tempfile.mkdtemp()
    logging.info(f"Created temporary directory at {temp_dir}")

    # Step 2: Prepare the Fontconfig configuration content
    fontconfig_content = f"""<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<fontconfig>
    <dir>{os.path.dirname(font_path)}</dir>
    <match target="pattern">
        <test name="family" qual="any">
            <string>Mu Font</string>
        </test>
        <edit name="family" mode="assign" binding="strong">
            <string>Mu Font</string>
        </edit>
        <edit name="file" mode="assign" binding="strong">
            <string>{font_path}</string>
        </edit>
    </match>
</fontconfig>
"""
    logging.info("Fontconfig content prepared:")
    logging.info(fontconfig_content)

    # Step 3: Write the configuration to the temporary directory
    config_path = os.path.join(temp_dir, "fonts.conf")
    with open(config_path, "w") as f:
        f.write(fontconfig_content.strip())  # Ensure no leading/trailing spaces or newlines
    logging.info(f"Fontconfig written to {config_path}")

    # Step 4: Set the FONTCONFIG_FILE environment variable
    os.environ["FONTCONFIG_FILE"] = config_path
    logging.info(f"FONTCONFIG_FILE environment variable set to {config_path}")

    # Step 5: Verify the setup by listing the fonts recognized by Fontconfig
    result = subprocess.run(['fc-list'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    logging.info("Fontconfig available fonts after setup:")
    logging.info(result.stdout.decode())
    
    # Step 6: Check if any errors were reported
    if result.stderr:
        print("Debug: Fontconfig error:")
        print(result.stderr.decode())

    return temp_dir