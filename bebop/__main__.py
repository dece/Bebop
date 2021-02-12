import argparse

from bebop.tofu import load_cert_stash
from bebop.screen import Screen


def main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument("url", default=None)
    args = argparser.parse_args()

    if args.url:
        start_url = args.url
        if not start_url.startswith("gemini://"):
            start_url = "gemini://" + start_url
    else:
        start_url = None

    cert_stash = load_cert_stash("/tmp/stash")
    Screen(cert_stash).run(start_url=start_url)


main()
