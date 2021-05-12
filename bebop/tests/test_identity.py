import unittest

from ..identity import get_identities_for_url


def get_fake_identity(ident: int):
    return {"name": f"test{ident}", "id": f"lol{ident}"}


class TestIdentity(unittest.TestCase):

    def test_get_identities_for_url(self):
        result = get_identities_for_url({}, "gemini://host/path")
        self.assertListEqual(result, [])

        identities = {
            "gemini://host/path": [get_fake_identity(1)],
            "gemini://otherhost/path": [get_fake_identity(2)],
        }

        result = get_identities_for_url(identities, "gemini://host/path")
        self.assertListEqual(result, identities["gemini://host/path"])
        result = get_identities_for_url(identities, "gemini://bad/path")
        self.assertListEqual(result, [])

        identities["gemini://host/path/sub"] = [get_fake_identity(3)]
        result = get_identities_for_url(identities, "gemini://host/path/sub")
        self.assertListEqual(result, identities["gemini://host/path/sub"])
        result = get_identities_for_url(identities, "gemini://host/path/sub/a")
        self.assertListEqual(result, identities["gemini://host/path/sub"])
        result = get_identities_for_url(identities, "gemini://host/path/sus")
        self.assertListEqual(result, identities["gemini://host/path"])
