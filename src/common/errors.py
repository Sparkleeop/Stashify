import json

class APIError(Exception):

    def __init__(self, code, message, status_code=400, details=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details

def validation_error(message="Invalid input.", details=None):
    return APIError("VALIDATION_ERROR", message, 400, details)