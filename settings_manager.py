import json
import os

SETTINGS_FILE = "settings.json"

DEFAULT_SETTINGS = {
    "theme": "light",
    "lock_timeout": 5,  # в минутах
    "generator": {
        "length": 16,
        "use_upper": True,
        "use_lower": True,
        "use_digits": True,
        "use_special": True,
        "mnemonic": False
    },
    "hotkeys": {
        "lock": "alt+l",
        "autofill": "alt+b",
        "capture": "alt+h",
        "reset": "alt+r",
        "generate": "alt+g"
    }
}

def load_settings():
    settings = DEFAULT_SETTINGS.copy()
    if not os.path.exists(SETTINGS_FILE):
        save_settings(settings)
        return settings
    
    try:
        with open(SETTINGS_FILE, "r") as f:
            loaded = json.load(f)
            # Глубокое обновление (для hotkeys)
            if "hotkeys" in loaded:
                settings["hotkeys"].update(loaded["hotkeys"])
            
            # Глубокое обновление (для generator)
            if "generator" in loaded:
                settings["generator"].update(loaded["generator"])

            if "theme" in loaded:
                settings["theme"] = loaded["theme"]
            if "lock_timeout" in loaded:
                settings["lock_timeout"] = loaded["lock_timeout"]
            return settings
    except Exception:
        return settings

def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=4)
