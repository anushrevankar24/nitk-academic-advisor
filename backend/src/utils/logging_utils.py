"""Logging utilities with sensitive data sanitization."""

import logging
import re
import sys
from pathlib import Path
from typing import Optional
from .config import LOG_LEVEL, LOG_FORMAT, LOG_DIR


# Patterns for sensitive data
SENSITIVE_PATTERNS = {
    "api_key": re.compile(
        r"(api[_-]?key|apikey|gemini[_-]?api[_-]?key|authorization|bearer|x-api-key)\s*[:=]\s*['\"]?([a-zA-Z0-9\-._~+/]{20,})['\"]?",
        re.IGNORECASE
    ),
    "url_credentials": re.compile(
        r"https?://([a-zA-Z0-9_-]+):([a-zA-Z0-9_\-$.+!*'(),]{1,}?)@",
        re.IGNORECASE
    ),
    "token": re.compile(
        r"(token|auth|secret|password)\s*[:=]\s*['\"]?([a-zA-Z0-9\-._~+/]{20,})['\"]?",
        re.IGNORECASE
    ),
}


class SanitizingFormatter(logging.Formatter):
    """Custom formatter that removes sensitive data from log messages."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record and sanitize sensitive data."""
        # Format the message
        formatted = super().format(record)
        
        # Sanitize sensitive patterns
        formatted = self._sanitize(formatted)
        
        return formatted
    
    @staticmethod
    def _sanitize(message: str) -> str:
        """Remove sensitive data from message."""
        for pattern_name, pattern in SENSITIVE_PATTERNS.items():
            if pattern_name == "api_key":
                # Replace the actual key with [REDACTED]
                message = pattern.sub(
                    lambda m: f"{m.group(1)}=[REDACTED]",
                    message
                )
            elif pattern_name == "url_credentials":
                # Replace credentials in URLs
                message = pattern.sub(
                    r"https://\1:[REDACTED]@",
                    message
                )
            elif pattern_name == "token":
                # Replace token values
                message = pattern.sub(
                    lambda m: f"{m.group(1)}=[REDACTED]",
                    message
                )
        
        return message


def setup_logger(
    name: str,
    log_file: Optional[Path] = None,
    level: str = LOG_LEVEL,
    format_string: str = LOG_FORMAT,
    sanitize: bool = True
) -> logging.Logger:
    """
    Set up a logger with console and optional file handlers.
    Supports sanitization of sensitive data.
    
    Args:
        name: Logger name
        log_file: Optional path to log file
        level: Logging level
        format_string: Log format string
        sanitize: Whether to sanitize sensitive data
        
    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Choose formatter based on sanitization preference
    if sanitize:
        formatter = SanitizingFormatter(format_string)
    else:
        formatter = logging.Formatter(format_string)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_chunk_logger() -> logging.Logger:
    """Get logger for chunk tracking."""
    chunk_log_file = LOG_DIR / "chunks_loaded.log" if LOG_DIR else None
    return setup_logger(
        name="chunk_tracker",
        log_file=chunk_log_file,
        level="INFO",
        sanitize=True
    )


def get_api_logger() -> logging.Logger:
    """Get logger for API requests."""
    api_log_file = LOG_DIR / "api.log" if LOG_DIR else None
    return setup_logger(
        name="api",
        log_file=api_log_file,
        level=LOG_LEVEL,
        sanitize=True
    )
