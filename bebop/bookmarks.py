from pathlib import Path

from bebop.fs import get_user_data_path


TEMPLATE = """\
# Bookmarks

Welcome to your bookmark page! This file has been created in "{original_path}" \
and you can edit it as you wish. New bookmarks will be added on a new \
line at the end, so always keep an empty line there!
"""


def get_bookmarks_path() -> Path:
    """Return the path to the bookmarks file."""
    return get_user_data_path() / "bookmarks.gmi"


def init_bookmarks(filepath):
    """Create the bookmarks file and return its initial content.

    Raises OSError if the file could not be written.
    """
    content = TEMPLATE.format(original_path=filepath)
    with open(filepath, "wt") as bookmark_file:
        bookmark_file.write(content)
    return content


def get_bookmarks_document():
    """Return the bookmarks content, or None or failure.

    If no bookmarks file exist yet, it is created. If accessing or creating the
    file fails, or if it is unreadable, return None.
    """
    filepath = get_bookmarks_path()
    try:
        if not filepath.exists():
            content = init_bookmarks(filepath)
        else:
            with open(filepath, "rt") as bookmark_file:
                content = bookmark_file.read()
    except OSError:
        return None
    return content


def save_bookmark(url, title):
    """Append this URL/title pair to the bookmarks, return True on success."""
    filepath = get_bookmarks_path()
    try:
        if not filepath.exists():
            init_bookmarks(filepath)
        with open(filepath, "at") as bookmark_file:
            bookmark_file.write(f"=> {url} {title}\n")
    except OSError:
        return False
    return True
