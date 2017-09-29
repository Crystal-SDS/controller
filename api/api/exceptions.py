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


class AnalyticsJobSubmissionException(CrystalControllerException):
    """Exception to be raised when something goes wrong in job submission."""
    pass


class ProjectNotFound(CrystalControllerException):
    """Exception to be raised when a dynamic policy is created with a Non-existing project."""
    pass


class ProjectNotCrystalEnabled(CrystalControllerException):
    """Exception to be raised when a dynamic policy is created with a Non-crystal-enabled project."""
    pass
