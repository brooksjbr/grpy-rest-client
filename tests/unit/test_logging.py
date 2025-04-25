import io
import logging
import sys
from unittest.mock import patch

from src.grpy.logging import DefaultLogger, Logger


class TestLogger:
    """Test the Logger class."""

    def test_logger_initialization(self):
        """Test that the logger initializes correctly."""
        logger = Logger(name="test-logger")
        assert logger.logger.name == "test-logger"
        assert logger.logger.level == logging.INFO
        assert len(logger.logger.handlers) > 0

    def test_logger_levels(self):
        """Test that the logger supports different log levels."""
        logger = Logger(name="test-logger", level=logging.DEBUG)
        assert logger.logger.level == logging.DEBUG

        logger = Logger(name="test-logger", level=logging.WARNING)
        assert logger.logger.level == logging.WARNING

    def test_log_methods(self):
        """Test that the log methods work correctly."""
        logger = Logger(name="test-logger")

        with patch.object(logger.logger, "log") as mock_log:
            logger.debug("Debug message")
            mock_log.assert_called_with(logging.DEBUG, "Debug message")

            logger.info("Info message")
            mock_log.assert_called_with(logging.INFO, "Info message")

            logger.warning("Warning message")
            mock_log.assert_called_with(logging.WARNING, "Warning message")

            logger.error("Error message")
            mock_log.assert_called_with(logging.ERROR, "Error message")

            logger.critical("Critical message")
            mock_log.assert_called_with(logging.CRITICAL, "Critical message")

    def test_log_with_context(self):
        """Test logging with additional context."""
        logger = Logger(name="test-logger")

        with patch.object(logger.logger, "log") as mock_log:
            logger.info("Request completed", status=200, duration=0.5)
            mock_log.assert_called_with(logging.INFO, "Request completed - status=200 duration=0.5")


class TestDefaultLogger:
    """Test the DefaultLogger class."""

    def test_default_logger_initialization(self):
        """Test that the default logger initializes with correct defaults."""
        logger = DefaultLogger()
        assert logger.logger.name == "grpy-rest-client"
        assert logger.logger.level == logging.INFO
        assert len(logger.logger.handlers) > 0

    def test_default_logger_output(self):
        """Test that the default logger outputs correctly formatted messages."""
        # Capture stdout
        captured_output = io.StringIO()
        sys.stdout = captured_output

        logger = DefaultLogger(level=logging.DEBUG)
        logger.debug("Test debug message")
        logger.info("Test info message")

        # Reset stdout
        sys.stdout = sys.__stdout__

        output = captured_output.getvalue()
        assert "[DEBUG]" in output
        assert "[INFO]" in output
        assert "[grpy-rest-client]" in output
        assert "Test debug message" in output
        assert "Test info message" in output
