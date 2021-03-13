"""Links manager."""

from typing import List


class Links(dict):

    def disambiguate(self, digits: str, max_digits: int):
        """Return the list of possible candidates for those digits."""
        if len(digits) == max_digits:
            return [int(digits)]
        return [
            link_id for link_id, url in self.items()
            if str(link_id).startswith(digits)
        ]

    @staticmethod
    def from_metalines(metalines: List):
        links = Links()
        for meta, _ in metalines:
            if "link_id" in meta and "url" in meta:
                links[meta["link_id"]] = meta["url"]
        return links
