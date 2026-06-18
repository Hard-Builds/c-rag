class CustomException(Exception):
    def __init__(self, status: int, message: str):
        self.status: int = status
        self.message = message
