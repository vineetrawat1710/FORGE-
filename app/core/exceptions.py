class UserAlreadyExistsError(Exception):
    """Raised when the email address already exists in the system."""


class UsernameAlreadyExistsError(Exception):
    """Raised when the username already exists in the system."""


class AuthenticationError(Exception):
    """Base exception for authentication failures."""


class InvalidTokenError(AuthenticationError):
    """Raised when a token is malformed or invalid."""


class TokenExpiredError(AuthenticationError):
    """Raised when a token is expired."""


class InactiveUserError(AuthenticationError):
    """Raised when a user account is inactive."""


class InvalidCredentialsError(AuthenticationError):
    """Raised when the provided credentials are invalid."""


class EnvironmentError(Exception):
    """Base exception for environment management failures."""


class EnvironmentNotFoundError(EnvironmentError):
    """Raised when an environment cannot be found."""


class EnvironmentAccessDeniedError(EnvironmentError):
    """Raised when a user tries to access another user's environment."""


class ActiveEnvironmentNotFoundError(EnvironmentError):
    """Raised when no active environment exists for a user."""


class RequestDomainError(Exception):
    """Base exception for request domain failures."""


class RequestNotFoundError(RequestDomainError):
    """Raised when a request cannot be found."""


class RequestHistoryError(RequestDomainError):
    """Base exception for execution history failures."""


class CollectionError(Exception):
    """Base exception for collection failures."""


class CollectionNotFoundError(CollectionError):
    """Raised when a collection cannot be found."""


class CollectionAccessDeniedError(CollectionError):
    """Raised when a user tries to access another user's collection."""


class RequestExecutionError(Exception):
    """Base exception for request execution failures."""


class InvalidRequestURLError(RequestExecutionError):
    """Raised when a request URL is invalid or blocked."""


class RequestTimeoutError(RequestExecutionError):
    """Raised when a request times out."""


class RequestCancelledError(RequestExecutionError):
    """Raised when a request is cancelled."""


class ResponseTooLargeError(RequestExecutionError):
    """Raised when the response exceeds the configured size."""


class SSLVerificationError(RequestExecutionError):
    """Raised when SSL verification fails."""


class ConnectionFailureError(RequestExecutionError):
    """Raised when the connection cannot be established."""


class RedirectLimitExceededError(RequestExecutionError):
    """Raised when too many redirects occur."""


class DNSResolutionError(RequestExecutionError):
    """Raised when DNS resolution fails."""


class ResponseParseError(RequestExecutionError):
    """Raised when parsing a response fails."""


class ImportExportError(Exception):
    """Base exception for import/export failures."""


class ImportValidationError(ImportExportError):
    """Raised when imported content is invalid."""


class ImportParseError(ImportExportError):
    """Raised when imported content cannot be parsed."""


class ImportLimitExceededError(ImportExportError):
    """Raised when imported content exceeds configured limits."""


class ExportError(ImportExportError):
    """Raised when an export operation fails."""
