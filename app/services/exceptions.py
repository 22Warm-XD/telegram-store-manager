class ServiceError(Exception):
    """Base service exception."""


class ProductNotFoundError(ServiceError):
    """Raised when a product cannot be found."""


class ChannelOperationError(ServiceError):
    """Raised when publication/editing in channel fails."""


class InvalidPriceError(ServiceError):
    """Raised when provided price is invalid."""


class ProductAlreadySoldError(ServiceError):
    """Raised when an operation is attempted on sold product."""


class InvalidProductStateError(ServiceError):
    """Raised when product state does not allow requested transition."""
