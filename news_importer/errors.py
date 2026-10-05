"""Errors a person can fix by changing a file, a flag, or the database path."""


class ImporterError(Exception):
    """A failed import, listing, or export with a message safe to print."""
