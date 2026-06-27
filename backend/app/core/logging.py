import logging
import sys
from logging.handlers import RotatingFileHandler
from app.core.config import settings

def setup_logging():
    """Configures application-wide logging with Console and Rotating File outputs."""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    formatter = logging.Formatter(log_format)
    
    # Root logger config
    root_logger = logging.getLogger()
    
    # Clear existing handlers to prevent duplicate prints
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
        
    root_logger.setLevel(settings.LOG_LEVEL)

    # Console output handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Optional Rotating File handler (caps log sizes at 10MB, retains 3 archives)
    try:
        file_handler = RotatingFileHandler(
            "app.log",
            maxBytes=10 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    except Exception as e:
        # Fallback if file path is not writeable (e.g. running in serverless read-only contexts)
        logging.warning(f"Could not initialize app.log file handler: {e}")

# Run setup during core module load
setup_logging()
logger = logging.getLogger("adaptive-newssphere")
