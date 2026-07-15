"""Custom exceptions for LLM operations."""


class LLMException(Exception):
    """Base exception for LLM operations."""

    pass


class LLMConnectionError(LLMException):
    """Exception raised when connection to LLM server fails."""

    pass


class LLMGenerationError(LLMException):
    """Exception raised when text generation fails."""

    pass


class LLMTimeoutError(LLMException):
    """Exception raised when LLM request times out."""

    pass


class LLMInvalidResponseError(LLMException):
    """Exception raised when LLM returns invalid response."""

    pass
