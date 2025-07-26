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


class PlanGenerationError(PipelineError):
    """Exception raised when plan generation fails."""
    pass


class ReportGenerationError(PipelineError):
    """Exception raised when report generation fails."""
    pass


class MetricComparisonError(PipelineError):
    """Exception raised when metric comparison fails."""
    pass


class LLMError(PipelineError):
    """Exception raised when LLM operations fail."""
    pass
