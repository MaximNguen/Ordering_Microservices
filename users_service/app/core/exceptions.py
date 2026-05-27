class AppError(Exception):
    """Base application error for service layer."""

    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


class AuthError(AppError):
    """Raised when authentication or token validation fails."""
