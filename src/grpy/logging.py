import logging
import sys
from typing import Any, Optional


class Logger:
    """Base logger class for grpy-rest-client.

    Provides standardized logging functionality with configurable levels
    and formatting for the REST client operations.
    """

    # Log levels
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL

    def __init__(
        self,
        name: str = "grpy-rest-client",
        level: int = logging.INFO,
        format_string: Optional[str] = None,
        log_to_console: bool = True,
        log_file: Optional[str] = None,
    ):
        """Initialize the logger.

        Args:
            name: Logger name
            level: Minimum logging level
            format_string: Custom format string for log messages
            log_to_console: Whether to log to console
            log_file: Optional file path to log to
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        # Clear any existing handlers
        if self.logger.handlers:
            self.logger.handlers.clear()

        # Default format
        if format_string is None:
            format_string = "[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s"

        formatter = logging.Formatter(format_string)

        # Console handler
        if log_to_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

        # File handler
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log a debug message.

        Args:
            message: The message to log
            **kwargs: Additional context to include in the log
        """
        self._log(self.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        """Log an info message.

        Args:
            message: The message to log
            **kwargs: Additional context to include in the log
        """
        self._log(self.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log a warning message.

        Args:
            message: The message to log
            **kwargs: Additional context to include in the log
        """
        self._log(self.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        """Log an error message.

        Args:
            message: The message to log
            **kwargs: Additional context to include in the log
        """
        self._log(self.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs: Any) -> None:
        """Log a critical message.

        Args:
            message: The message to log
            **kwargs: Additional context to include in the log
        """
        self._log(self.CRITICAL, message, **kwargs)

    def _log(self, level: int, message: str, **kwargs: Any) -> None:
        """Internal method to handle logging with context.

        Args:
            level: Log level
            message: The message to log
            **kwargs: Additional context to include in the log
        """
        if kwargs:
            context_str = " ".join([f"{k}={v}" for k, v in kwargs.items()])
            message = f"{message} - {context_str}"
        self.logger.log(level, message)


class DefaultLogger(Logger):
    """Default logger implementation for grpy-rest-client.

    Provides a pre-configured logger with reasonable defaults for the REST client.
    """

    def __init__(
        self,
        name: str = "grpy-rest-client",
        level: int = logging.INFO,
        log_file: Optional[str] = None,
    ):
        """Initialize the default logger.

        Args:
            name: Logger name
            level: Minimum logging level
            log_file: Optional file path to log to
        """
        super().__init__(
            name=name,
            level=level,
            format_string="[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s",
            log_to_console=True,
            log_file=log_file,
        )
