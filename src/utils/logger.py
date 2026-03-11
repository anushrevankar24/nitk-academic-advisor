"""Logging utility for chunk tracking and general logging."""

import logging
import sys
from pathlib import Path
from typing import Optional
from .config import LOG_LEVEL, LOG_FORMAT, LOG_DIR, CHUNK_LOG_FILE


def setup_logger(
    name: str,
    log_file: Optional[Path] = None,
    level: str = LOG_LEVEL,
    format_string: str = LOG_FORMAT
) -> logging.Logger:
    """
    Set up a logger with both file and console handlers.
    
    Args:
        name: Logger name
        log_file: Optional path to log file (if None, only console logging)
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        format_string: Log format string
        
    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    formatter = logging.Formatter(format_string)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (if log file specified)
    if log_file:
        # Ensure log directory exists
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_chunk_logger() -> logging.Logger:
    """
    Get logger specifically for chunk tracking.
    
    Returns:
        Chunk logger configured to write to chunks_loaded.log
    """
    return setup_logger(
        name="chunk_tracker",
        log_file=CHUNK_LOG_FILE,
        level="INFO"
    )

