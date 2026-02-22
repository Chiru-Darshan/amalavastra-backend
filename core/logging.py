"""
Logging Configuration Module
Centralized logging setup with structured logging support
"""
import logging
import sys
from datetime import datetime
from typing import Any, Dict
import json

from core.config import settings


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, "extra_data"):
            log_data["extra"] = record.extra_data
        
        return json.dumps(log_data)


class RequestContextFilter(logging.Filter):
    """Filter to add request context to log records"""
    
    def __init__(self):
        super().__init__()
        self.request_id = None
        self.user_id = None
    
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = getattr(self, "request_id", None)
        record.user_id = getattr(self, "user_id", None)
        return True


def setup_logging() -> logging.Logger:
    """Configure application logging"""
    
    # Create logger
    logger = logging.getLogger("saree_api")
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    
    if settings.ENVIRONMENT == "production":
        # Use JSON formatting in production
        console_handler.setFormatter(JSONFormatter())
    else:
        # Use simple formatting in development
        console_handler.setFormatter(
            logging.Formatter(settings.LOG_FORMAT)
        )
    
    logger.addHandler(console_handler)
    
    # Add context filter
    context_filter = RequestContextFilter()
    logger.addFilter(context_filter)
    
    return logger


# Create global logger instance
logger = setup_logging()


def log_request(method: str, path: str, status_code: int, duration_ms: float, user_id: str = None):
    """Log HTTP request details"""
    logger.info(
        f"{method} {path} - {status_code} - {duration_ms:.2f}ms",
        extra={
            "extra_data": {
                "method": method,
                "path": path,
                "status_code": status_code,
                "duration_ms": duration_ms,
                "user_id": user_id
            }
        }
    )


def log_security_event(event_type: str, details: Dict[str, Any], severity: str = "INFO"):
    """Log security-related events"""
    log_method = getattr(logger, severity.lower(), logger.info)
    log_method(
        f"Security Event: {event_type}",
        extra={
            "extra_data": {
                "event_type": event_type,
                "security": True,
                **details
            }
        }
    )
