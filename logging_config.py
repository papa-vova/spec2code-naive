"""
Logging configuration for the SPEC2CODE pipeline.
Provides JSON-formatted logging to stderr with configurable log levels.
"""
import json
import logging
import sys
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
import os


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def __init__(self, execution_id: str = None):
        super().__init__()
        self.execution_id = execution_id or str(uuid.uuid4())[:8]
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        # Base log structure
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "execution_id": self.execution_id
        }
        
        # Add component and step if available
        if hasattr(record, 'component'):
            log_entry["component"] = record.component
        
        if hasattr(record, 'step'):
            log_entry["step"] = record.step
        
        # Add structured data if available
        if hasattr(record, 'data'):
            log_entry["data"] = record.data
        
        # Add duration if available
        if hasattr(record, 'duration_ms'):
            log_entry["duration_ms"] = record.duration_ms
        
        # Add error information for exceptions
        if record.exc_info:
            log_entry["error"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else "Unknown",
                "message": str(record.exc_info[1]) if record.exc_info[1] else "",
                "traceback": self.formatException(record.exc_info)
            }
        
        return json.dumps(log_entry, ensure_ascii=False)


class PipelineLogger:
    """Factory class for creating configured loggers."""
    
    def __init__(self, execution_id: str = None):
        self.execution_id = execution_id or str(uuid.uuid4())[:8]
        self._configured = False
    
    def configure_logging(self, log_level: str = "INFO") -> None:
        """Configure the root logger with JSON formatting to stderr."""
        if self._configured:
            return
        
        # Convert string level to logging constant
        numeric_level = getattr(logging, log_level.upper(), logging.INFO)
        
        # Create JSON formatter
        formatter = JSONFormatter(execution_id=self.execution_id)
        
        # Configure stderr handler
        stderr_handler = logging.StreamHandler(sys.stderr)
        stderr_handler.setFormatter(formatter)
        stderr_handler.setLevel(numeric_level)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(numeric_level)
        
        # Remove any existing handlers to avoid duplicates
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Add our stderr handler
        root_logger.addHandler(stderr_handler)
        
        self._configured = True
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger with the specified name."""
        return logging.getLogger(name)
    
    def log_with_context(self, logger: logging.Logger, level: str, message: str, 
                        component: str = None, step: str = None, 
                        data: Dict[str, Any] = None, duration_ms: float = None) -> None:
        """Log a message with additional context."""
        # Get the logging level
        numeric_level = getattr(logging, level.upper(), logging.INFO)
        
        # Create a custom log record
        record = logger.makeRecord(
            logger.name, numeric_level, "", 0, message, (), None
        )
        
        # Add custom attributes
        if component:
            record.component = component
        if step:
            record.step = step
        if data:
            record.data = data
        if duration_ms is not None:
            record.duration_ms = duration_ms
        
        # Log the record
        logger.handle(record)


def get_log_level_from_env_and_args(args_log_level: str = None, verbose: bool = False) -> str:
    """
    Determine log level from environment variable, CLI args, and defaults.
    
    Priority:
    1. CLI --verbose flag (sets DEBUG)
    2. CLI --log-level argument
    3. SPEC2CODE_LOG_LEVEL environment variable
    4. Default (INFO)
    """
    if verbose:
        return "DEBUG"
    
    if args_log_level:
        return args_log_level.upper()
    
    env_level = os.getenv("SPEC2CODE_LOG_LEVEL")
    if env_level:
        return env_level.upper()
    
    return "INFO"


def setup_pipeline_logging(log_level: str = None, verbose: bool = False, 
                          execution_id: str = None) -> PipelineLogger:
    """
    Set up logging for the pipeline with the specified configuration.
    
    Args:
        log_level: Log level string (DEBUG, INFO, WARNING, ERROR)
        verbose: If True, sets log level to DEBUG
        execution_id: Optional execution ID for tracking
    
    Returns:
        Configured PipelineLogger instance
    """
    # Determine final log level
    final_log_level = get_log_level_from_env_and_args(log_level, verbose)
    
    # Create and configure logger
    pipeline_logger = PipelineLogger(execution_id)
    pipeline_logger.configure_logging(final_log_level)
    
    return pipeline_logger


# Convenience functions for common logging patterns
def log_step_start(logger: logging.Logger, component: str, step: str, message: str, 
                  data: Dict[str, Any] = None) -> None:
    """Log the start of a pipeline step."""
    pipeline_logger = PipelineLogger()
    pipeline_logger.log_with_context(
        logger, "INFO", message, component=component, step=step, data=data
    )


def log_step_complete(logger: logging.Logger, component: str, step: str, message: str,
                     data: Dict[str, Any] = None, duration_ms: float = None) -> None:
    """Log the completion of a pipeline step."""
    pipeline_logger = PipelineLogger()
    pipeline_logger.log_with_context(
        logger, "INFO", message, component=component, step=step, 
        data=data, duration_ms=duration_ms
    )


def log_debug(logger: logging.Logger, message: str, component: str = None, 
             data: Dict[str, Any] = None) -> None:
    """Log a debug message with optional context."""
    pipeline_logger = PipelineLogger()
    pipeline_logger.log_with_context(
        logger, "DEBUG", message, component=component, data=data
    )


def log_error(logger: logging.Logger, message: str, component: str = None, 
             error: Exception = None) -> None:
    """Log an error message with optional exception info."""
    if error:
        logger.error(message, exc_info=True, extra={"component": component})
    else:
        pipeline_logger = PipelineLogger()
        pipeline_logger.log_with_context(
            logger, "ERROR", message, component=component
        )
