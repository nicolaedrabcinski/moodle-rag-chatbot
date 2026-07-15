"""
Structured logging configuration for FCIM AI Chatbot.
Provides JSON and text formatters with context.
"""

import logging
import sys
from typing import Any, Dict, Optional

import structlog
from pythonjsonlogger import jsonlogger

from src.core.config import settings


def configure_logging() -> None:
    """
    Configure structured logging with structlog and stdlib logging.

    Sets up JSON or text logging based on configuration.
    """
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            (
                structlog.processors.JSONRenderer()
                if settings.log_format == "json"
                else structlog.dev.ConsoleRenderer()
            ),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure stdlib logging
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Create formatter
    if settings.log_format == "json":
        formatter = jsonlogger.JsonFormatter(
            "%(timestamp)s %(level)s %(name)s %(message)s",
            rename_fields={"levelname": "level", "asctime": "timestamp"},
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)

    # File handler (if configured)
    if settings.log_file_path:
        try:
            file_handler = logging.FileHandler(settings.log_file_path)
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        except (OSError, PermissionError) as e:
            root_logger.warning(f"Failed to create file handler: {e}")

    # Suppress noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (usually __name__)

    Returns:
        structlog.BoundLogger: Configured logger instance
    """
    return structlog.get_logger(name)


class LoggerAdapter:
    """
    Logger adapter for adding context to all log messages.

    Usage:
        logger = LoggerAdapter("mymodule", context={"request_id": "123"})
        logger.info("Processing request", user_id=456)
    """

    def __init__(self, name: str, context: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize logger adapter.

        Args:
            name: Logger name
            context: Default context to add to all log messages
        """
        self.logger = get_logger(name)
        self.context = context or {}

    def _log(self, level: str, message: str, **kwargs: Any) -> None:
        """
        Log message with context.

        Args:
            level: Log level
            message: Log message
            **kwargs: Additional context
        """
        log_method = getattr(self.logger, level)
        combined_context = {**self.context, **kwargs}
        log_method(message, **combined_context)

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message."""
        self._log("debug", message, **kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message."""
        self._log("info", message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message."""
        self._log("warning", message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        """Log error message."""
        self._log("error", message, **kwargs)

    def critical(self, message: str, **kwargs: Any) -> None:
        """Log critical message."""
        self._log("critical", message, **kwargs)

    def exception(self, message: str, **kwargs: Any) -> None:
        """Log exception with traceback."""
        self._log("exception", message, **kwargs)

    def bind(self, **kwargs: Any) -> "LoggerAdapter":
        """
        Create new logger adapter with additional context.

        Args:
            **kwargs: Additional context

        Returns:
            LoggerAdapter: New logger adapter with combined context
        """
        new_context = {**self.context, **kwargs}
        return LoggerAdapter(self.logger.name, context=new_context)


# Initialize logging on module import
configure_logging()
