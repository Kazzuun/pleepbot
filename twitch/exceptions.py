
class SevenTVException(Exception):
    """Used for 7tv api related exceptions."""
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class Filtered(Exception):
    """Raised when a message gets filtered."""
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)
