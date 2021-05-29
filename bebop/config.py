"""Config management."""

import json
import logging
import os.path


DEFAULT_CONFIG = {
    "connect_timeout": 10,
    "text_width": 80,
    "download_path": "",
    "source_editor": ["vi"],
    "command_editor": ["vi"],
    "history_limit": 1000,
    "external_commands": {},
    "external_command_default": ["xdg-open"],
    "home": "bebop:welcome",
    "render_mode": "fancy",
    "generate_client_cert_command": [
        "openssl", "req",
        "-newkey", "rsa:4096",
        "-nodes",
        "-keyform", "PEM",
        "-keyout", "{key_path}",
        "-x509",
        "-days", "28140",  # https://www.youtube.com/watch?v=F9L4q-0Pi4E
        "-outform", "PEM",
        "-out", "{cert_path}",
        "-subj", "/CN={common_name}",
    ],
}

RENDER_MODES = ("fancy", "dumb")


def load_config(config_path):
    if not os.path.isfile(config_path):
        create_default_config(config_path)
        return DEFAULT_CONFIG

    try:
        with open(config_path, "rt") as config_file:
            config = json.load(config_file)
    except OSError as exc:
        logging.error(f"Could not read config file {config_path}: {exc}")
    except ValueError as exc:
        logging.error(f"Could not parse config file {config_path}: {exc}")
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
        logging.error(f"Could not create config file {config_path}: {exc}")
