# Small utility functions used in the hook app
import os
import shutil
import string
import random

def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def delete_temp_dir(temp_dir):
    try:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        print(f"Temporary directory {temp_dir} deleted successfully.")
    except Exception as e:
        print(f"Error deleting temporary directory {temp_dir}: {str(e)}")

def handle_task_cancellation(temp_dir, task_id):
    delete_temp_dir(temp_dir)

def split_hook_text(hook_text):
    words = hook_text.split()
    hook_text = ' '.join(word.capitalize() for word in words)

    if ' - ' in hook_text:
        last_dash_index = hook_text.rfind('-')
        line1 = hook_text[:last_dash_index].strip()
        line2 = hook_text[last_dash_index + 1:].strip()
        return [line1, line2]
    else:
        line1 = hook_text
        return [line1]
      
def generate_task_id():
    chars = string.ascii_letters + string.digits
    task_id = "task-"
    for _ in range(9):
        task_id += random.choice(chars)
    return task_id