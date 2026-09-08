class SegmentationError(Exception):
    """Base exception for segmentation-related failures."""


class FileProcessingError(SegmentationError):
    """Raised when a source text file cannot be processed."""


class InvalidQuestionFormatError(SegmentationError):
    """Raised when a question line cannot be parsed."""
