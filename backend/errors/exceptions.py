from rest_framework import status
from rest_framework.exceptions import APIException


class CodedError(APIException):
    """An API error of ours. `params` fill the {placeholders} of the text; `extra` goes into the body."""

    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, code, text, status_code=None, extra=None, **params):
        super().__init__(text, code)
        if status_code is not None:
            self.status_code = status_code
        self.extra = extra or {}
        self.params = params
