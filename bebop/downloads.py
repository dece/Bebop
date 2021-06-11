"""Downloads management."""

from pathlib import Path
from typing import Optional

from bebop.fs import get_downloads_path


def get_download_path(url: str, download_dir: Optional[str] =None) -> Path:
    """Try to find the best download file path possible from this URL."""
    download_path = Path(download_dir) if download_dir else get_downloads_path()
    if not download_path.exists():
        download_path.mkdir(parents=True)
    url_parts = url.rsplit("/", maxsplit=1)
    if url_parts:
        filename = url_parts[-1]
    else:
        filename = url.split("://")[1] if "://" in url else url
        filename = filename.replace("/", "_")
    return download_path / filename
