import argparse

from bebop.browser.browser import Browser
from bebop.config import load_config
from bebop.fs import ensure_bebop_files_exist, get_config_path
from bebop.tofu import get_cert_stash_path, load_cert_stash, save_cert_stash


def main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument("url", nargs="?", default=None)
    args = argparser.parse_args()

    if args.url:
        start_url = args.url
    else:
        start_url = None

    config_path = get_config_path()
    config = load_config(config_path)

    bebop_files_error = ensure_bebop_files_exist()
    if bebop_files_error:
        print("Bebop could not create local files:", bebop_files_error)
        return

    cert_stash_path = get_cert_stash_path()
    cert_stash = load_cert_stash(cert_stash_path) or {}
    try:
        Browser(config, cert_stash).run(start_url=start_url)
    finally:
        save_cert_stash(cert_stash, cert_stash_path)


main()
