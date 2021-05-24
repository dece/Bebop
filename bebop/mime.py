"""Basic MIME utilities (RFC 2046)."""

from dataclasses import dataclass
from typing import Optional


DEFAULT_CHARSET = "utf-8"


@dataclass
class MimeType:
    main_type: str
    sub_type: str
    parameters: dict

    @property
    def short(self):
        return f"{self.main_type or '*'}/{self.sub_type or '*'}"

    @property
    def charset(self):
        return self.parameters.get("charset", DEFAULT_CHARSET)

    @staticmethod
    def from_str(mime_string) -> Optional["MimeType"]:
        """Parse a MIME string into a MimeType instance, or None on error."""
        if ";" in mime_string:
            type_str, *param_strs = mime_string.split(";")
            parameters = {}
            for param in map(lambda s: s.strip().lower(), param_strs):
                if param.count("=") != 1:
                    return None
                param_name, param_value = param.split("=")
                parameters[param_name] = param_value
        else:
            type_str = mime_string.strip()
            parameters = {}
        if type_str.count("/") != 1:
            return None
        main_type, sub_type = type_str.split("/")
        return MimeType(main_type, sub_type, parameters)


DEFAULT_MIME_TYPE = MimeType("text", "gemini", {"charset": DEFAULT_CHARSET})
