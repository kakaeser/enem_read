class AppException(Exception):
    """Base exception for application errors"""

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class NotFoundException(AppException):
    """Resource not found exception"""

    def __init__(self, resource: str, identifier):
        message = f"{resource} with id {identifier} not found"
        super().__init__(message, status_code=404)


class ValidationException(AppException):
    """Validation error exception"""

    def __init__(self, message: str):
        super().__init__(message, status_code=422)


class OCRProcessingException(AppException):
    """OCR processing failure exception"""

    def __init__(self, message: str):
        super().__init__(message, status_code=422)
