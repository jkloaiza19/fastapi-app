# exceptions.py

from fastapi import HTTPException, status


class BaseAppException(Exception):
    """Base exception for the application."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class ValidationError(BaseAppException):
    """Exception raised for validation errors."""
    def __init__(self, field: str, message: str):
        super().__init__(f"Validation error on field '{field}': {message}")


class DatabaseError(BaseAppException):
    """Exception raised for database-related errors."""
    def __init__(self, message: str):
        super().__init__(f"Database error: {message}")


class NotFoundError(BaseAppException):
    """Exception raised when a resource is not found."""
    def __init__(self, resource: str):
        super().__init__(f"{resource} not found")


class HTTPError(HTTPException):
    """Exception for HTTP errors."""
    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)


# Example utility function for raising HTTP exceptions
def raise_http_exception(status_code: int, detail: str):
    raise HTTPException(status_code=status_code, detail=detail)