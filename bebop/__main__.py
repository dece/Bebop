import argparse

from bebop.browser.browser import Browser
from bebop.fs import get_user_data_path
from bebop.tofu import load_cert_stash, save_cert_stash


def main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument("url", nargs="?", default=None)
    args = argparser.parse_args()

    if args.url:
        start_url = args.url
    else:
        start_url = None

    user_data_path = get_user_data_path()
    if not user_data_path.exists():
        user_data_path.mkdir()

    cert_stash_path = user_data_path / "known_hosts.txt"
    cert_stash = load_cert_stash(cert_stash_path) or {}
    try:
        Browser(cert_stash).run(start_url=start_url)
    finally:
        save_cert_stash(cert_stash, cert_stash_path)


main()
