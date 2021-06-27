"""Config management."""

import json
import logging
from pathlib import Path


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
        "-utf8",
        "-x509",
        "-days", "28140",  # https://www.youtube.com/watch?v=F9L4q-0Pi4E
        "-outform", "PEM",
        "-out", "{cert_path}",
        "-subj", "/CN={common_name}",
    ],
    "scroll_step": 3,
    "persistent_history": False,
    "enabled_plugins": [],
    "list_item_bullet": "• ",
}


def load_config(config_path: Path):
    if not config_path.is_file():
        create_default_config(config_path)
        return DEFAULT_CONFIG

    try:
        with open(config_path, "rt") as config_file:
            config = json.load(config_file)
    except OSError as exc:
        abs_path = config_path.absolute()
        logging.error(f"Could not read config file {abs_path}: {exc}")
    except ValueError as exc:
        abs_path = config_path.absolute()
        logging.error(f"Could not parse config file {abs_path}: {exc}")
    else:
        # Fill missing values with defaults.
        for key, value in DEFAULT_CONFIG.items():
            if key not in config:
                config[key] = value
        return config
    return DEFAULT_CONFIG


def create_default_config(config_path: Path):
    config_dir = config_path.parent
    if not config_dir.is_dir():
        try:
            config_dir.mkdir(parents=True)
        except OSError as exc:
            logging.error(f"Could not create config dir {config_dir}: {exc}")
            return
    try:
        with open(config_path, "wt") as config_file:
            json.dump(DEFAULT_CONFIG, config_file, indent=2)
    except OSError as exc:
        logging.error(f"Could not create config file {config_path}: {exc}")
