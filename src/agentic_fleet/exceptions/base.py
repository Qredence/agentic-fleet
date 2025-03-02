"""
Base exceptions for Agentic Fleet.
"""


class AgenticFleetError(Exception):
    """
    Base exception for all Agentic Fleet errors.

    All custom exceptions should inherit from this class.
    """

    def __init__(self, message: str = "An error occurred in Agentic Fleet"):
        self.message = message
        super().__init__(self.message)


class AgenticFleetAPIError(AgenticFleetError):
    """
    Base exception for API-related errors.

    This includes errors related to API requests, responses, and validation.
    """

    def __init__(self, message: str = "An API error occurred", status_code: int = 500):
        self.status_code = status_code
        super().__init__(message)


class AgenticFleetDatabaseError(AgenticFleetError):
    """
    Base exception for database-related errors.

    This includes errors related to database connections, queries, and integrity.
    """

    def __init__(self, message: str = "A database error occurred"):
        super().__init__(message)


class AgenticFleetConfigError(AgenticFleetError):
    """
    Base exception for configuration-related errors.

    This includes errors related to loading configuration files, environment variables, etc.
    """

    def __init__(self, message: str = "A configuration error occurred"):
        super().__init__(message)
