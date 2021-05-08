"""Config management."""

import json
import os.path


DEFAULT_CONFIG = {
    "connect_timeout": 10,
    "text_width": 80,
    "source_editor": ["vi"],
    "command_editor": ["vi"],
    "history_limit": 1000,
}


def load_config(config_path):
    if not os.path.isfile(config_path):
        create_default_config(config_path)
        return DEFAULT_CONFIG

    try:
        with open(config_path, "rt") as config_file:
            config = json.load(config_file)
    except OSError as exc:
        print(f"Could not read config file {config_path}: {exc}")
    except ValueError as exc:
        print(f"Could not parse config file {config_path}: {exc}")
    else:
        # Fill missing values with defaults.
        for key, value in DEFAULT_CONFIG.items():
            if key not in config:
                config[key] = value
        return config
    return DEFAULT_CONFIG


def create_default_config(config_path):
    try:
        with open(config_path, "wt") as config_file:
            json.dump(DEFAULT_CONFIG, config_file, indent=2)
    except OSError as exc:
        print(f"Could not create config file {config_path}: {exc}")
