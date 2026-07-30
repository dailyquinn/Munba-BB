import dataclasses

from aiopenapi3.errors import HTTPServerError as base_HTTPServerError
from aiopenapi3.errors import HTTPClientError as base_HTTPClientError
from aiopenapi3.errors import HTTPError


class ESIErrorLimitException(Exception):
    """ESI Global Error Limit Exceeded
    https://developers.eveonline.com/docs/services/esi/best-practices/#error-limit
    """

    def __init__(self, reset=None, *args, **kwargs) -> None:
        self.reset = reset
        msg = kwargs.get("message") or (
            f"ESI Error limited. Reset in {reset} seconds." if reset else "ESI Error limited."
        )
        super().__init__(msg, *args)


class ESIBucketLimitException(Exception):
    """Endpoint (Bucket) Specific Rate Limit Exceeded"""

    def __init__(self, bucket, reset: float = 0, *args, **kwargs) -> None:
        self.bucket = bucket
        self.reset = reset if reset else self.bucket.window
        msg = kwargs.get("message") or f"ESI bucket limit reached for {bucket}."
        super().__init__(msg, *args)


@dataclasses.dataclass(repr=False)
class HTTPNotModified(HTTPError):
    """The HTTP Status is 304"""

    status_code: int
    headers: dict[str, str]

    def __str__(self):
        return f"""<{self.__class__.__name__} {self.status_code} {self.headers}>"""


@dataclasses.dataclass(repr=False)
class HTTPClientError(base_HTTPClientError):
    """HTTP Response Code 4xx"""
    pass


@dataclasses.dataclass(repr=False)
class HTTPServerError(base_HTTPServerError):
    """HTTP Response Code 5xx"""
    pass
