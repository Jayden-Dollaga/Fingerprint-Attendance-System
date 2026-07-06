###############################################################################
#  logger.py
#  AS608 Fingerprint Attendance System
#
#  Centralized logging system. Use this instead of print() everywhere.
#  Logs can be redirected to files without changing any code.
#
#  Usage:
#    from core.logger import log
#    log.info("System started")
#    log.success("Enrollment complete")
#    log.warning("Low confidence")
#    log.error("Connection failed")
###############################################################################

import logging
import os
from datetime import datetime
from pathlib import Path

# Import config to check if file logging is enabled
from config import LOG_TO_FILE, LOG_FOLDER, ENABLE_DEBUG_LOGGING

# Create logs folder if needed
if LOG_TO_FILE:
    log_dir = Path(LOG_FOLDER)
    log_dir.mkdir(parents=True, exist_ok=True)


class ColorFormatter(logging.Formatter):
    """Custom formatter with colors for console output."""
    
    # ANSI color codes
    COLORS = {
        'DEBUG':    '\033[36m',      # Cyan
        'INFO':     '\033[37m',      # White
        'SUCCESS':  '\033[92m',      # Bright Green
        'WARNING':  '\033[93m',      # Bright Yellow
        'ERROR':    '\033[91m',      # Bright Red
        'CRITICAL': '\033[95m',      # Bright Magenta
        'RESET':    '\033[0m',       # Reset
    }
    
    def format(self, record):
        # Get color for this level
        levelname = record.levelname
        if levelname == 'SUCCESS':
            levelname = 'SUCCESS'
        
        color = self.COLORS.get(levelname, self.COLORS['INFO'])
        reset = self.COLORS['RESET']
        
        # Build message
        timestamp = datetime.now().strftime("%H:%M:%S")
        message = f"{color}[{timestamp}] [{levelname:8}]{reset} {record.getMessage()}"
        
        return message


class Logger:
    """Centralized logger for the entire application."""
    
    # Custom log level for success messages
    SUCCESS_LEVEL = 25
    logging.addLevelName(SUCCESS_LEVEL, "SUCCESS")
    
    def __init__(self):
        self.logger = logging.getLogger("FingerprintAttendance")
        self.logger.setLevel(logging.DEBUG if ENABLE_DEBUG_LOGGING else logging.INFO)
        
        # Clear any existing handlers
        self.logger.handlers.clear()
        
        # ── Console handler (always enabled) ──────────────────────────────────
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG if ENABLE_DEBUG_LOGGING else logging.INFO)
        console_formatter = ColorFormatter()
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # ── File handler (optional, configured in config.py) ──────────────────
        if LOG_TO_FILE:
            today = datetime.now().strftime("%Y-%m-%d")
            log_file = Path(LOG_FOLDER) / f"{today}.log"
            
            file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            
            # File format (no colors)
            file_formatter = logging.Formatter(
                '%(asctime)s [%(levelname)-8s] %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
            
            # Print startup message
            print(f"[Logger]  : Logging to {log_file}")
    
    def debug(self, message):
        """Log debug message (only if ENABLE_DEBUG_LOGGING is True)."""
        self.logger.debug(message)
    
    def info(self, message):
        """Log info message."""
        self.logger.info(message)
    
    def success(self, message):
        """Log success message (green)."""
        self.logger.log(self.SUCCESS_LEVEL, message)
    
    def warning(self, message):
        """Log warning message (yellow)."""
        self.logger.warning(message)
    
    def error(self, message):
        """Log error message (red)."""
        self.logger.error(message)
    
    def critical(self, message):
        """Log critical message (magenta)."""
        self.logger.critical(message)


# Global logger instance — use this everywhere
log = Logger()
