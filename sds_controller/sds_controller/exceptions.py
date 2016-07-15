"""
Exceptions raised by the Crystal Controller code.
"""


class CrystalControllerException(Exception):
    """Base exception class for distinguishing our own exception classes."""
    pass


class SwiftClientError(CrystalControllerException):
    """Exception to be raised when something goes wrong in a Swift call."""
    pass


class StorletNotFoundException(CrystalControllerException):
    """Exception to be raised when a storlet file is not found."""
    pass


class FileSynchronizationException(CrystalControllerException):
    """Exception to be raised when a file synchronization between controller and Swift nodes fails."""
    pass

