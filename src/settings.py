import json
import os

SETTINGS_FILE = 'settings.json'

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        return {}
    try:
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading settings: {e}")
        return {}

def save_settings(data):
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(data, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving settings: {e}")
        return False
