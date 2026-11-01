"""Application errors translated into stable HTTP responses at the API layer."""


class ApplicationError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class ProviderError(ApplicationError):
    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=503)
