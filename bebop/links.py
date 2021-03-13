"""Links manager."""


class Links(dict):

    def disambiguate(self, digits: str, max_digits: int):
        """Return the list of possible candidates for those digits."""
        if len(digits) == max_digits:
            return [int(digits)]
        return [
            link_id for link_id, url in self.items()
            if str(link_id).startswith(digits)
        ]
