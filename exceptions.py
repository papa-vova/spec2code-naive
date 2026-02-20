"""
Custom exception classes for the SPEC2CODE pipeline.
"""


class PipelineError(Exception):
    """Base exception class for pipeline-related errors."""
    pass


class InputError(PipelineError):
    """Exception raised for input-related errors."""
    pass


class FileNotFoundError(InputError):
    """Exception raised when input file is not found."""
    pass


class EmptyFileError(InputError):
    """Exception raised when input file is empty."""
    pass


