import logging
import pathlib
import warnings
import datetime as dt
from hashlib import md5
from timeit import default_timer
from typing import Any

from aiopenapi3 import OpenAPI, FileSystemLoader
from aiopenapi3._types import ResponseDataType, ResponseHeadersType
from aiopenapi3.errors import HTTPServerError as base_HTTPServerError
from aiopenapi3.errors import HTTPClientError as base_HTTPClientError
from aiopenapi3.request import OperationIndex, RequestBase
from esi.aiopenapi3.client import SpecCachingClient
from esi.rate_limiting import ESIRateLimitBucket, ESIRateLimits, interval_to_seconds
from httpx import (
    AsyncClient, Client, HTTPStatusError, RequestError, Response, Timeout,
)
from tenacity import (
    AsyncRetrying, Retrying, retry_if_exception, stop_after_attempt,
    wait_combine, wait_exponential,
)

from django.core.cache import cache
from django.utils.text import slugify

from esi import app_settings
from esi.exceptions import HTTPClientError, HTTPServerError, HTTPNotModified
from esi.aiopenapi3.plugins import (
    Add304ContentType, DjangoESIInit, PatchCompatibilityDatePlugin,
    Trim204ContentType, MinifySpec
)
from esi.exceptions import ESIErrorLimitException
from esi.models import Token
from esi.signals import esi_request_statistics
from esi.stubs import ESIClientStub

from . import __title__, __url__, __version__
from .helpers import pascal_case_string

logger = logging.getLogger(__name__)

ETAG_EXPIRY = 60 * 60 * 24 * 7  # 7 days


def _time_to_expiry(expires_header: str) -> int:
    """Calculate cache TTL from Expires header
    Args:
        expires_header (str): The value of the Expires header '%a, %d %b %Y %H:%M:%S %Z'
    Returns:
        int: The cache TTL in seconds
    """
    try:
        expires_dt = dt.datetime.strptime(str(expires_header), '%a, %d %b %Y %H:%M:%S %Z')
        if expires_dt.tzinfo is None:
            expires_dt = expires_dt.replace(tzinfo=dt.timezone.utc)
        return max(int((expires_dt - dt.datetime.now(dt.timezone.utc)).total_seconds()), 0)
    except ValueError:
        return 0


def _httpx_exceptions(exc: BaseException) -> bool:
    """
    Helper function for HTTP Retries, what various exceptions and status codes should we retry on.
    ESI has some weird behaviours
    """
    if isinstance(exc, ESIErrorLimitException):
        return False
    if isinstance(exc, RequestError):
        return True
    if isinstance(exc, HTTPStatusError) and getattr(exc.response, "status_code", None) in {502, 503, 504}:
        return True
    return False


def http_retry_sync() -> Retrying:
    return Retrying(
        retry=retry_if_exception(_httpx_exceptions),
        wait=wait_combine(
            wait_exponential(multiplier=1, min=1, max=10),
        ),
        stop=stop_after_attempt(3),
        reraise=True,
    )


async def http_retry_async() -> AsyncRetrying:  # pragma: no cover
    return AsyncRetrying(
        retry=retry_if_exception(_httpx_exceptions),
        wait=wait_combine(
            wait_exponential(multiplier=1, min=1, max=10),
        ),
        stop=stop_after_attempt(3),
        reraise=True,
    )


def _load_plugins(app_name, tags: list[str] = [], operations: list[str] = []):
    """Load the plugins to make ESI work with this lib.

    Args:
        app_name (str): app name to use for internal etags
    """
    return [
        PatchCompatibilityDatePlugin(),
        Trim204ContentType(),
        Add304ContentType(),
        DjangoESIInit(app_name),
        MinifySpec(tags, operations)
    ]


def _load_aiopenapi_client_sync(
        spec_url: str,
        compatibility_date: str,
        app_name: str,
        user_agent: str,
        tenant: str,
        spec_file: str | None = None,
        tags: list[str] = [],
        operations: list[str] = []) -> OpenAPI:
    """Create an OpenAPI3 Client from Spec

    Args:
        spec_url (str): _description_
        compatibility_date (str): _description_
        app_name (str): _description_
        user_agent (str): _description_
        tenant (str): _description_
        spec_file (str | None, optional): _description_. Defaults to None.

    Returns:
        OpenAPI: aiopenapi3 Client Class
    """
    headers = {
        "User-Agent": user_agent,
        "X-Tenant": tenant,
        "X-Compatibility-Date": compatibility_date
    }

    def session_factory(**kwargs) -> Client:
        kwargs.pop("headers", None)
        return SpecCachingClient(
            headers=headers,
            timeout=Timeout(
                connect=app_settings.ESI_REQUESTS_CONNECT_TIMEOUT,
                read=app_settings.ESI_REQUESTS_READ_TIMEOUT,
                write=app_settings.ESI_REQUESTS_WRITE_TIMEOUT,
                pool=app_settings.ESI_REQUESTS_POOL_TIMEOUT
            ),
            http2=True,
            **kwargs
        )
    if spec_file:
        return OpenAPI.load_file(
            url=spec_url,
            path=spec_file,
            session_factory=session_factory,
            loader=FileSystemLoader(pathlib.Path(spec_file)),
            use_operation_tags=True,
            plugins=_load_plugins(app_name, tags, operations)
        )
    else:
        return OpenAPI.load_sync(
            url=spec_url,
            session_factory=session_factory,
            use_operation_tags=True,
            plugins=_load_plugins(app_name, tags, operations)
        )


async def _load_aiopenapi_client_async(
        spec_url: str,
        compatibility_date: str,
        app_name: str,
        user_agent: str,
        tenant: str,
        spec_file: str | None = None) -> OpenAPI:  # pragma: no cover
    """Create an OpenAPI3 Client from Spec Async

    Args:
        spec_url (str): _description_
        compatibility_date (str): _description_
        user_agent (str): _description_
        tenant (str): _description_
        spec_file (str | None, optional): _description_. Defaults to None.

    Returns:
        OpenAPI: aiopenapi3 Client Class
    """
    headers = {
        "User-Agent": user_agent,
        "X-Tenant": tenant,
        "X-Compatibility-Date": compatibility_date
    }

    def session_factory(**kwargs) -> AsyncClient:
        kwargs.pop("headers", None)
        return AsyncClient(
            headers=headers,
            timeout=Timeout(
                connect=app_settings.ESI_REQUESTS_CONNECT_TIMEOUT,
                read=app_settings.ESI_REQUESTS_READ_TIMEOUT,
                write=app_settings.ESI_REQUESTS_WRITE_TIMEOUT,
                pool=app_settings.ESI_REQUESTS_POOL_TIMEOUT
            ),
            http2=True,
            **kwargs
        )
    if spec_file:
        # TODO find a async way to load from file?
        return OpenAPI.load_file(
            url=spec_url,
            path=spec_file,
            session_factory=session_factory,
            use_operation_tags=True,
            plugins=_load_plugins(app_name)
        )
    else:
        return await OpenAPI.load_async(
            url=spec_url,
            session_factory=session_factory,
            use_operation_tags=True,
            plugins=_load_plugins(app_name)
        )


def _build_user_agent(ua_appname: str, ua_version: str, ua_url: str | None = None) -> str:
    """
    AppName/1.2.3 (foo@example.com; +https://gitlab.com/) Django-ESI/1.2.3 (+https://gitlab.com/allianceauth/django-esi)
    Contact Email will be inserted from app_settings.
    Args:
        ua_appname (str): Application Name, PascalCase
        ua_version (str): Application Version, SemVer
        ua_url (str | None): Application URL (Optional)
    Returns:
        str: User-Agent string
    """

    # Enforce PascalCase for `ua_appname` and strip whitespace
    sanitized_ua_appname = pascal_case_string(ua_appname)
    sanitized_appname = pascal_case_string(__title__)

    return (
        f"{sanitized_ua_appname}/{ua_version} "
        f"({app_settings.ESI_USER_CONTACT_EMAIL}{f'; +{ua_url})' if ua_url else ')'} "
        f"{sanitized_appname}/{__version__} (+{__url__})"
    )


def _get_spec_url() -> str:
    return f"{app_settings.ESI_API_URL}meta/openapi.json"


def esi_client_factory_sync(
        compatibility_date: str,
        ua_appname: str, ua_version: str, ua_url: str | None = None,
        spec_file: str | None = None,
        tenant: str = "tranquility",
        tags: list[str] = [], operations: list[str] = [],
        **kwargs) -> OpenAPI:
    """Generate a new OpenAPI ESI client.
    Args:
        compatibility_date (str): "YYYY-MM-DD" The latest version of ESI your client is tested with
        ua_appname (str): Application Name, PascalCase
        ua_version (str): Application Version, SemVer
        ua_url (str, optional): Application URL (Optional). Defaults to None.
        spec_file (str | None, optional): Specification file path (Optional). Defaults to None.
        tenant (str, optional): Tenant ID (Optional). Defaults to "tranquility".
    Returns:
        OpenAPI: OpenAPI ESI Client
    """
    user_agent = _build_user_agent(ua_appname, ua_version, ua_url)
    spec_url = _get_spec_url()
    return _load_aiopenapi_client_sync(
        spec_url,
        compatibility_date,
        ua_appname,
        user_agent,
        tenant,
        spec_file,
        tags,
        operations
    )


async def esi_client_factory_async(
        compatibility_date: str,
        ua_appname: str, ua_version: str, ua_url: str | None = None,
        spec_file: str | None = None,
        tenant: str = "tranquility",
        **kwargs) -> OpenAPI:  # pragma: no cover
    """Generate a new OpenAPI ESI client.
    Args:
        compatibility_date (str): "YYYY-MM-DD" The latest version of ESI your client is tested with
        ua_appname (str): Application Name, PascalCase
        ua_version (str): Application Version, SemVer
        ua_url (str | None, optional): Application URL (Optional). Defaults to None.
        spec_file (str | None, optional): Specification file path (Optional). Defaults to None.
        tenant (str, optional): Tenant ID (Optional). Defaults to "tranquility".
    Returns:
        OpenAPI: OpenAPI ESI Client
    """
    user_agent = _build_user_agent(ua_appname, ua_version, ua_url)
    spec_url = _get_spec_url()
    return await _load_aiopenapi_client_async(spec_url, compatibility_date, ua_appname, user_agent, tenant, spec_file)


class BaseEsiOperation():
    def __init__(self, operation, api: OpenAPI) -> None:
        self.method, self.url, self.operation, self.extra = operation
        self.api = api
        self.token: Token | None = None
        self.bucket: ESIRateLimitBucket | None = None

        self._args = []
        self._kwargs = {}

        self._set_bucket()

    def __call__(self, *args, **kwargs) -> "BaseEsiOperation":
        self._args = args
        self._kwargs = kwargs
        return self

    def _unnormalize_parameters(self, params: dict[str, Any]) -> dict[str, Any]:
        """UN-Normalize Pythonic parameter names back to OpenAPI names.

        Converts pythonic keys like "Accept_Language" to "Accept-Language" when/if
        a non pythonic (usually) hyphenated form exists in the operation's parameter list. Performs
        case-insensitive matching and only rewrites when there's a known
        parameter with hyphens, leaving normal snake_case params (e.g.
        "type_id") untouched.
        Args:
            params: Raw parameters collected from the call
        Returns:
            dict: Parameters with keys aligned to the OpenAPI spec
        """
        try:
            spec_param_names = [p.name for p in getattr(self.operation, "parameters", [])]
        except Exception:
            spec_param_names = []

        # Exact and case-insensitive lookup maps
        spec_param_set = set(spec_param_names)
        spec_param_map_ci = {n.lower(): n for n in spec_param_names}

        normalized: dict[str, Any] = {}
        for k, v in params.items():
            # Fast path: exact match
            if k in spec_param_set:
                normalized[k] = v
                continue

            # Try hyphen variant
            k_dash = k.replace("_", "-")
            if k_dash in spec_param_set:
                normalized[k_dash] = v
                continue

            # Case-insensitive fallbacks
            kl = k.lower()
            if kl in spec_param_map_ci:
                normalized[spec_param_map_ci[kl]] = v
                continue

            k_dash_l = k_dash.lower()
            if k_dash_l in spec_param_map_ci:
                normalized[spec_param_map_ci[k_dash_l]] = v
                continue

            # Unknown to the spec; pass through as-is (aiopenapi3 will validate)
            normalized[k] = v

        return normalized

    def _etag_key(self) -> str:
        """Generate a key name used to cache etag responses based on app_name and cache_key
        Returns:
            str: Key
        """
        # ignore the token this will break the cache
        return f"{slugify(self.api.app_name)}_etag_{self._cache_key()}"  # type: ignore app_name is added by a plugin

    def _cache_key(self) -> str:
        """Generate a key name used to cache responses based on method, url, args, kwargs
        Returns:
            str: Key
        """
        # ignore the token this will break the cache
        ignore_keys = [
            "token",
        ]
        _kwargs = {key: value for key, value in self._kwargs.items() if key not in ignore_keys}
        data = (self.method + self.url + str(self._args) + str(_kwargs)).encode('utf-8')
        str_hash = md5(data).hexdigest()  # nosec B303
        return f'esi_{str_hash}'

    def _extract_body_param(self) -> Token | None:
        """Pop the request body from parameters to be able to check the param validity
        Returns:
            Any | None: the request body
        """
        _body = self._kwargs.pop("body", None)
        if _body and not getattr(self.operation, "requestBody", False):
            raise ValueError("Request Body provided on endpoint with no request body parameter.")
        return _body

    def _extract_token_param(self) -> Token | None:
        """Pop token from parameters or use the Client wide token if set
        Returns:
            Token | None: The token to use for the request
        """
        _token = self._kwargs.pop("token", None)
        if _token and not getattr(self.operation, "security", False):
            raise ValueError("Token provided on public endpoint")
        return self.token or _token

    def _has_page_param(self) -> bool:
        """Check if this operation supports Offset Based Pagination.
        Returns:
            bool: True if page parameters are present, False otherwise
        """
        return any(p.name == "page" for p in self.operation.parameters)

    def _has_cursor_param(self) -> bool:
        """Check if this operation supports Cursor Based Pagination.
        Returns:
            bool: True if cursor parameters are present, False otherwise
        """
        return any(p.name == "before" or p.name == "after" for p in self.operation.parameters)

    def _get_cache(self, cache_key: str, etag: str | None) -> tuple[ResponseHeadersType | None, Any, Response | None]:
        """Retrieve cached response and validate expiry
        Args:
            cache_key (str): The cache key to retrieve
        Returns:
            tuple[ResponseHeadersType | None, Any, Response | None]: The cached response,
            or None if not found or expired
        """
        if not app_settings.ESI_CACHE_RESPONSE:
            return None, None, None

        try:
            cached_response = cache.get(cache_key)
        except Exception as e:
            logger.error(f"Cache retrieve failed {e}", exc_info=True)
            return None, None, None

        if cached_response:
            logger.debug(f"Cache Hit {self.url}")
            expiry = _time_to_expiry(str(cached_response.headers.get('Expires')))

            # force check to ensure cache isn't expired
            if expiry < 0:
                logger.warning("Cache expired by %d seconds, forcing expiry", expiry)
                return None, None, None

            # check if etag is same before building models from cache
            if etag:
                if cached_response.headers.get('ETag') == etag:
                    # refresh/store the etag's TTL
                    self._send_signal(
                        status_code=0,  # this is a cached response less a 304
                        headers=cached_response.headers,
                        latency=0
                    )
                    self._store_etag(cached_response.headers)
                    raise HTTPNotModified(
                        status_code=304,
                        headers=cached_response.headers
                    )

            # build models
            headers, data = self.parse_cached_request(cached_response)
            return headers, data, cached_response

        return None, None, None

    def _store_etag(self, headers: dict):
        """
            Store response etag in cache for 7 days
        """
        if "ETag" in headers:
            cache.set(self._etag_key(), headers["ETag"], timeout=ETAG_EXPIRY)

    def _update_etag_ttl(self):
        """
            reset etag ttl in cache.
        """
        cache.expire(self._etag_key(), timeout=ETAG_EXPIRY)

    def _clear_etag(self):
        """ Delete the cached etag for this operation.
        """
        try:
            cache.delete(self._etag_key())
        except Exception as e:
            logger.error(f"Failed to delete etag {e}", exc_info=True)

    def _store_cache(self, cache_key: str, response) -> None:
        """ Store the response in cache for expiry TTL.
        Args:
            cache_key (str): The cache key to store the response under
            response (Response): The response object to cache
        """
        if not app_settings.ESI_CACHE_RESPONSE:
            return

        expires = response.headers.get("Expires")
        ttl = _time_to_expiry(expires) if expires else 0
        if ttl > 0:
            try:
                cache.set(cache_key, response, ttl)
            except Exception as e:
                logger.error(f"Failed to cache {e}", exc_info=True)

    def _clear_cache(self):
        """ Delete the cached data for this operation.
        """
        try:
            cache.delete(self._cache_key())
        except Exception as e:
            logger.error(f"Failed to delete cache {e}", exc_info=True)

    def _validate_token_scopes(self, token: Token) -> None:
        """Validate that the token provided has the required scopes for this ESI operation.
        """
        token_scopes = set(token.scopes.all().values_list("name", flat=True))
        try:
            required_scopes = set(getattr(getattr(self.operation, "security", [])[0], "root", {}).get("OAuth2", []))
        except KeyError:
            required_scopes = []
        missing_scopes = [x for x in required_scopes if x not in token_scopes]
        if len(missing_scopes) > 0:
            raise ValueError(f"Token Missing Scopes - {missing_scopes}")

    def parse_cached_request(self, cached_response) -> tuple[ResponseHeadersType, ResponseDataType]:
        req = self.api.createRequest(
            f"{self.operation.tags[0]}.{self.operation.operationId}"
        )
        return req._process_request(cached_response)

    def _set_bucket(self):
        """Setup the rate bucket"""
        _rate_limit = getattr(self.operation, "extensions", {}).get("rate-limit", False)
        if _rate_limit:
            _key = _rate_limit["group"]
            if self.token:
                _key = f"{_key}:{self.token.character_id}"
            self.bucket = ESIRateLimitBucket(
                _key,
                _rate_limit["max-tokens"],
                interval_to_seconds(_rate_limit["window-size"])
            )

    def _send_signal(self, status_code: int, headers: dict = {}, latency: float = 0) -> None:
        """
            Dispatch the esi request statistics signal
        """
        esi_request_statistics.send(
            sender=self.__class__,
            operation=self.operation.operationId,
            status_code=status_code,
            headers=headers,
            latency=latency,
            bucket=self.bucket.slug if self.bucket else ""
        )


class EsiOperation(BaseEsiOperation):
    def __skip__process__headers__(
        self, result, headers: dict[str, str], expected_response
    ):
        """Return all headers always"""
        return headers

    def _make_request(
            self,
            parameters: dict[str, Any],
            etag: str | None = None) -> RequestBase.Response:

        reset = cache.get("esi_error_limit_reset")
        if reset is not None:
            # Hard exception here if there is still an open Error Limit
            # developers need to either decorators.wait_for_esi_error_limit_reset()
            # or handle this by pushing their celery tasks back
            raise ESIErrorLimitException(reset=reset)

        if self.bucket:
            """Check Rate Limit"""
            ESIRateLimits.check_bucket(self.bucket)

        retry = http_retry_sync()

        def __func():
            req = self.api.createRequest(f"{self.operation.tags[0]}.{self.operation.operationId}")

            # We want all headers from ESI
            # don't check/parse them against the spec and return them all
            # TODO Investigate if this is a bug with aiopenapi or a spec compliance issue
            req._process__headers = self.__skip__process__headers__

            if self.token:
                self.api.authenticate(OAuth2=True)  # make the lib happy
                if isinstance(self.token, str):
                    # Fallback older Django-ESI Behaviour
                    # Deprecated
                    req.req.headers["Authorization"] = f"Bearer {self.token}"
                    warnings.warn(
                        "Passing an Access Token string directly is deprecated."
                        "Doing so will Skip Validation of Scopes"
                        "Please use a Token object instead.",
                        DeprecationWarning,
                        stacklevel=2
                    )
                else:
                    self._validate_token_scopes(self.token)
                    req.req.headers["Authorization"] = f"Bearer {self.token.valid_access_token()}"
            if etag:
                req.req.headers["If-None-Match"] = etag
            _response = req.request(data=self.body, parameters=self._unnormalize_parameters(parameters))

            if self.bucket and "x-ratelimit-remaining" in _response.result.headers:
                logger.debug(
                    "ESI Rate-Limit: "
                    f"'{_response.result.headers.get('x-ratelimit-group')}' - "
                    f"Used {_response.result.headers.get('x-ratelimit-used')} - "
                    f"{_response.result.headers.get('x-ratelimit-remaining')} / "
                    f"({_response.result.headers.get('x-ratelimit-limit')})"
                )
                ESIRateLimits.set_bucket(
                    self.bucket,
                    _response.result.headers.get("x-ratelimit-remaining")
                )

            return _response
        return retry(__func)

    def result(
            self,
            use_etag: bool = True,
            return_response: bool = False,
            force_refresh: bool = False,
            use_cache: bool = True,
            store_cache: bool = True,
            **extra) -> tuple[Any, Response] | Any:
        """Executes the request and returns the response from ESI for the current operation.

        Keyword Arguments:
            use_etag -- Use the inbuilt e-tag matching system (default True)
            return_response -- return the headers and request information (default False)
            force_refresh -- ignore etag and cache and force a re-fetch from ESI (default False)
            use_cache -- check cache prior to fetching from ESI (default True)
            store_cache -- store the returned data from ESI in cache (default True)

        Raises:
            ESIErrorLimitException: _description_
            ESIBucketLimitException: _description_
            HTTPNotModified: _description_
            HTTPServerError: _description_
            HTTPClientError: _description_
        Returns:
            _type_: _description_
        """
        _t = default_timer()
        self.token = self._extract_token_param()

        if self.token:
            self._set_bucket()

        self.body = self._extract_body_param()
        parameters = self._kwargs | extra
        cache_key = self._cache_key()
        etag_key = self._etag_key()
        etag = None

        if force_refresh:
            self._clear_cache()
            self._clear_etag()

        if use_etag:
            etag = cache.get(etag_key)

        headers, data, response = self._get_cache(cache_key, etag=etag) if use_cache else (None, None, None)

        if response and use_cache:
            expiry = _time_to_expiry(str(headers.get('Expires')))
            if expiry < 0:
                logger.warning(
                    "cache expired by %d seconds, Forcing expiry", expiry
                )
                response = None
                headers = None
                data = None

        if not response:
            logger.debug(f"Cache Miss {self.url}")
            try:
                headers, data, response = self._make_request(parameters, etag)
            # Shim our exceptions into Django-ESI
            except base_HTTPServerError as e:
                self._send_signal(
                    status_code=e.status_code,
                    headers=e.headers,
                    latency=default_timer() - _t
                )
                raise HTTPServerError(
                    status_code=e.status_code,
                    headers=e.headers,
                    data=e.data
                )

            except base_HTTPClientError as e:
                self._send_signal(
                    status_code=e.status_code,
                    headers=e.headers,
                    latency=default_timer() - _t
                )

                if e.status_code == 420:
                    reset = e.headers.get("X-RateLimit-Reset", None)
                    if reset:
                        reset = int(reset)
                        cache.set("esi_error_limit_reset", reset, timeout=reset)
                    raise ESIErrorLimitException(reset=reset)

                raise HTTPClientError(
                    status_code=e.status_code,
                    headers=e.headers,
                    data=e.data
                )

            self._send_signal(
                status_code=response.status_code,
                headers=response.headers,
                latency=default_timer() - _t
            )

            # store the ETAG in cache if using it.
            if use_etag:
                self._store_etag(response.headers)

            # Throw a 304 exception for catching.
            if response.status_code == 304:
                # refresh/store the etag's TTL
                self._update_etag_ttl()
                raise HTTPNotModified(
                    status_code=304,
                    headers=response.headers
                )

            # last step store cache after 304 logic, we dont want to catch the 304 `None` responses
            if store_cache:
                self._store_cache(cache_key, response)

        else:
            # send signal for cached data too
            self._send_signal(
                status_code=0,
                headers=response.headers,
                latency=default_timer() - _t
            )

        return (data, response) if return_response else data

    def results(
            self,
            use_etag: bool = True,
            return_response: bool = False,
            force_refresh: bool = False,
            use_cache: bool = True,
            store_cache: bool = True,
            **extra) -> tuple[list[Any], Response | Any | None] | list[Any]:
        all_results: list[Any] = []
        last_response: Response | None = None
        """Executes the request and returns the response from ESI for the current
        operation. Response will include all pages if there are more available.

        Keyword Arguments:
            use_etag -- Use the inbuilt e-tag matching system (default True)
            return_response -- return the headers and request information (default False)
            force_refresh -- ignore etag and cache and force a re-fetch from ESI (default False)
            use_cache -- check cache prior to fetching from ESI (default True)
            store_cache -- store the returned data from ESI in cache (default True)

        Raises:
            ESIErrorLimitException: _description_
            ESIBucketLimitException: _description_
            HTTPNotModified: _description_
            HTTPServerError: _description_
            HTTPClientError: _description_
        Returns:
            _type_: _description_
        """
        if self._has_page_param():
            current_page = 1
            total_pages = 1
            count_pages_etag_hit = 0
            force_refetch = False
            last_headers = None
            while current_page <= total_pages:
                self._kwargs["page"] = current_page
                try:
                    data, response = self.result(
                        # use cache where we can, but ignore etags if we are re-fetching
                        use_etag=use_etag and not force_refetch,
                        return_response=True,
                        force_refresh=force_refresh,
                        use_cache=use_cache,
                        store_cache=store_cache,
                        **extra
                    )
                    last_response = response
                    all_results.extend(data if isinstance(data, list) else [data])
                    total_pages = int(response.headers.get("X-Pages", 1))
                    logger.debug(
                        f"ESI Page Fetched {self.url} - {current_page}/{total_pages}"
                    )
                    current_page += 1

                except HTTPNotModified as e:
                    count_pages_etag_hit += 1
                    total_pages = int(e.headers.get("X-Pages", 1))
                    logger.debug(
                        f"ESI Page hit ETAG {self.url} - {current_page}/{total_pages}"
                    )
                    current_page += 1
                    last_headers = e.headers

                if (
                    current_page > total_pages and
                    count_pages_etag_hit != total_pages and
                    count_pages_etag_hit > 0
                ):
                    # Not all pages hit etag, so refetch all
                    force_refetch = True
                    current_page = 1
                    count_pages_etag_hit = 0
                    all_results = []
                    last_response = None

                elif (
                    current_page > total_pages and
                    count_pages_etag_hit == total_pages
                ):
                    # All etags hit raise 304
                    raise HTTPNotModified(
                        status_code=304,
                        headers=last_headers
                    )

        elif self._has_cursor_param():
            # Untested, there are no cursor based endpoints in ESI
            params = self._kwargs.copy()
            params.update(extra)
            for cursor_param in ("after", "before"):
                if params.get(cursor_param):
                    break
            else:
                cursor_param = "after"
            while True:
                data, response = self.result(
                    use_etag=use_etag,
                    return_response=True,
                    force_refresh=force_refresh,
                    use_cache=use_cache,
                    store_cache=store_cache,
                    **params
                )
                last_response = response
                if not data:
                    break
                all_results.extend(data if isinstance(data, list) else [data])
                cursor_token = {k.lower(): v for k, v in response.headers.items()}.get(cursor_param)
                if not cursor_token:
                    break
                params[cursor_param] = cursor_token

        else:
            data, response = self.result(
                use_etag=use_etag,
                return_response=True,
                force_refresh=force_refresh,
                use_cache=use_cache,
                store_cache=store_cache,
                **extra
            )
            all_results.extend(data if isinstance(data, list) else [data])
            last_response = response

        return (all_results, last_response) if return_response else all_results

    def results_localized(
            self,
            languages: list[str] | str | None = None,
            **kwargs
    ) -> dict[str, list[Any]]:
        """Executes the request and returns the response from ESI for all default languages and pages (if any).
        Args:
            languages: (list[str], str, optional) language(s) to return instead of default languages
        Raises:
            ValueError: Invalid or Not Supported Language Code ...
        Returns:
            dict[str, list[Any]]: Dict of all responses with the language code as keys.
        """
        if not languages:
            my_languages = list(app_settings.ESI_LANGUAGES)
        else:
            my_languages = []
            for lang in dict.fromkeys(languages):
                if lang not in app_settings.ESI_LANGUAGES:
                    raise ValueError('Invalid or Not Supported Language Code: %s' % lang)
                my_languages.append(lang)

        return {
            language: self.results(accept_language=language, **kwargs)
            for language in my_languages
        }

    def required_scopes(self) -> list[str]:
        """Return a simple list of scopes required for an endpoint. #Requires loading and processing a client
        Returns:
            list[str]: List of Scopes Required
        """
        try:
            if not getattr(self.operation, "security", False):
                return []  # No Scopes Required
            else:
                return list(getattr(getattr(self.operation, "security", [])[0], "root", {}).get("OAuth2", []))
        except (IndexError, KeyError):
            return []


class EsiOperationAsync(BaseEsiOperation):  # pragma: no cover
    async def _make_request(
            self,
            parameters: dict[str, Any],
            etag: str | None = None
    ) -> RequestBase.Response:

        reset = cache.get("esi_error_limit_reset")
        if reset is not None:
            # Hard exception here if there is still an open rate limit
            # developers need to either decorators.wait_for_esi_error_limit_reset()
            # or handle this by pushing their celery tasks back
            raise ESIErrorLimitException(reset=reset)

        async for attempt in http_retry_async():
            with attempt:
                req = self.api.createRequest(f"{self.operation.tags[0]}.{self.operation.operationId}")
                if self.token:
                    self.api.authenticate(OAuth2=True)  # make the lib happy
                    self._validate_token_scopes(self.token)
                    req.req.headers["Authorization"] = f"Bearer {self.token.valid_access_token()}"
                if etag:
                    req.req.headers["If-None-Match"] = etag
                return req.request(parameters=self._unnormalize_parameters(parameters))
        # Should never be reached because AsyncRetrying always yields at least once
        raise RuntimeError("Retry loop exited without performing a request")

    async def result(
        self,
        etag: str | None = None,
        return_response: bool = False,
        use_cache: bool = True,
        **extra
    ) -> tuple[Any, Response] | Any:
        self.token = self._extract_token_param()
        parameters = self._kwargs | extra
        cache_key = self._cache_key()
        etag_key = f"{cache_key}_etag"

        if not etag and app_settings.ESI_CACHE_RESPONSE:
            etag = cache.get(etag_key)

        headers, data, response = self._get_cache(cache_key, etag)

        if response and use_cache:
            expiry = _time_to_expiry(str(headers.get('Expires')))
            if expiry < 0:
                logger.warning(
                    "cache expired by %d seconds, Forcing expiry", expiry
                )
                response = None
                headers = None
                data = None

        if not response:
            logger.debug(f"Cache Miss {self.url}")
            try:
                headers, data, response = await self._make_request(parameters, etag)
                if response.status_code == 420:
                    reset = response.headers.get("X-RateLimit-Reset", None)
                    cache.set("esi_error_limit_reset", reset, timeout=reset)
                    raise ESIErrorLimitException(reset=reset)
                self._store_cache(cache_key, response)
                self._store_etag(response.headers)
            # Shim our exceptions into Django-ESI
            except base_HTTPServerError as e:
                raise HTTPServerError(
                    status_code=e.status_code,
                    headers=e.headers,
                    data=e.data
                )

            except base_HTTPClientError as e:
                raise HTTPClientError(
                    status_code=e.status_code,
                    headers=e.headers,
                    data=e.data
                )

            # Throw a 304 exception for catching.
            if response.status_code == 304:
                # refresh/store the etag's TTL
                self._store_etag(response.headers)
                raise HTTPNotModified(
                    status_code=304,
                    headers=response.headers
                )

        return (data, response) if return_response else data

    async def results(
            self,
            etag: str | None = None,
            return_response: bool = False,
            use_cache: bool = True,
            **extra
    ) -> tuple[list[Any], Response | Any | None] | list[Any]:
        all_results = []
        last_response = None

        if self._has_page_param():
            current_page = 1
            total_pages = 1
            while current_page <= total_pages:
                self._kwargs["page"] = current_page
                data, response = await self.result(etag=etag, return_response=True, use_cache=use_cache, **extra)
                last_response = response
                all_results.extend(data if isinstance(data, list) else [data])
                total_pages = int(response.headers.get("X-Pages", 1))
                logger.debug(
                    f"ESI Page Fetched {self.url} - {current_page}/{total_pages}"
                )
                current_page += 1
        # elif self._has_cursor_param():
            # TODO
        else:
            data, response = await self.result(etag=etag, return_response=True, use_cache=use_cache, **extra)
            all_results.extend(data if isinstance(data, list) else [data])
            last_response = response

        return (all_results, last_response) if return_response else all_results

    def results_localized(
            self,
            languages: list[str] | str | None = None,
            **extra) -> dict[str, list[Any]]:
        """Executes the request and returns the response from ESI for all default languages and pages (if any).
        Args:
            languages: (list[str], str, optional) language(s) to return instead of default languages
        Raises:
            ValueError: Invalid or Not Supported Language Code ...
        Returns:
            dict[str, list[Any]]: Dict of all responses with the language code as keys.
        """
        if not languages:
            my_languages = list(app_settings.ESI_LANGUAGES)
        else:
            my_languages = []
            for lang in dict.fromkeys(languages):
                if lang not in app_settings.ESI_LANGUAGES:
                    raise ValueError('Invalid or Not Supported Language Code: %s' % lang)
                my_languages.append(lang)

        return {
            language: self.results(accept_language=language, **extra)
            for language in my_languages
        }

    def required_scopes(self) -> list[str]:
        """Return a simple list of scopes required for an endpoint. #Requires loading and processing a client
        Returns:
            list[str]: List of Scopes Required
        """
        try:
            if not getattr(self.operation, "security", False):
                return []  # No Scopes Required
            else:
                return list(getattr(getattr(self.operation, "security", [])[0], "root", {}).get("OAuth2", []))
        except (IndexError, KeyError):
            return []


class ESITag:
    """
    API Tag Wrapper, providing access to Operations within a tag
    Assets, Characters, etc.
    """

    def __init__(self, operation, api) -> None:
        self._oi = operation._oi
        self._operations = operation._operations
        self.api = api

    def __getattr__(self, name: str) -> EsiOperation:
        if name not in self._operations:
            raise AttributeError(
                f"Operation '{name}' not found in tag '{self._oi}'. "
                f"Available operations: {', '.join(sorted(self._operations.keys()))}"
            )
        return EsiOperation(self._operations[name], self.api)


class ESITagAsync():  # pragma: no cover
    """
    Async API Tag Wrapper, providing access to Operations within a tag
    Assets, Characters, etc.
    """

    def __init__(self, operation, api) -> None:
        self._oi = operation._oi
        self._operations = operation._operations
        self.api = api

    def __getattr__(self, name: str) -> EsiOperationAsync:
        if name not in self._operations:
            raise AttributeError(
                f"Operation '{name}' not found in tag '{self._oi}'. "
                f"Available operations: {', '.join(sorted(self._operations.keys()))}"
            )
        return EsiOperationAsync(self._operations[name], self.api)


class ESIClient(ESIClientStub):
    """
    Base ESI Client, provides access to Tags Assets, Characters, etc.
    or Raw aiopenapi3 via sad smiley ._.
    """

    def __init__(self, api: OpenAPI) -> None:
        self.api = api
        self._tags = set(api._operationindex._tags.keys())

    def __getattr__(self, tag: str) -> ESITag | OperationIndex:
        # underscore returns the raw aiopenapi3 client
        if tag == "_":
            return self.api._operationindex

        # convert pythonic Planetary_Interaction to Planetary Interaction
        if "_" in tag:
            tag = tag.replace("_", " ")

        if tag in set(self.api._operationindex._tags.keys()):
            return ESITag(self.api._operationindex._tags[tag], self.api)

        raise AttributeError(
            f"Tag '{tag}' not found. "
            f"Available tags: {', '.join(sorted(self._tags))}"
        )

    def purge_all_etags(self):
        """ Delete all stored etags from the cache for this application

        TODO: consider making this more config agnostic
        """
        try:
            # new lib
            from django_redis import get_redis_connection
            _client = get_redis_connection("default")
        except (NotImplementedError, ModuleNotFoundError):
            # old lib
            from django.core.cache import caches
            default_cache = caches['default']
            _client = default_cache.get_master_client()  # type: ignore

        keys = _client.keys(f":?:{slugify(self.api.app_name)}_etag_*")  # type: ignore app_name is added by a plugin
        if keys:
            deleted = _client.delete(*keys)

        logger.info(f"Deleted {deleted} etag keys")

        return deleted


class ESIClientAsync(ESIClientStub):  # pragma: no cover
    """
    Async Base ESI Client, provides access to Tags Assets, Characters, etc.
    or Raw aiopenapi3 via sad smiley ._.
    """

    def __init__(self, api: OpenAPI) -> None:
        self.api = api
        self._tags = set(api._operationindex._tags.keys())

    def __getattr__(self, tag: str) -> ESITagAsync | OperationIndex:
        # underscore returns the raw aiopenapi3 client
        if tag == "_":
            return self.api._operationindex

        # convert pythonic Planetary_Interaction to Planetary Interaction
        if "_" in tag:
            tag = tag.replace("_", " ")

        if tag in set(self.api._operationindex._tags.keys()):
            return ESITagAsync(self.api._operationindex._tags[tag], self.api)

        raise AttributeError(
            f"Tag '{tag}' not found. "
            f"Available tags: {', '.join(sorted(self._tags))}"
        )


class ESIClientProvider:
    """Class for providing a single ESI client instance for a whole app
    * Note that one of either `tags` or `operations` must be provided to reduce memory footprint of the client
    * When `DEBUG=False`, not supplying either will raise an AttributeError.
    Args:
        compatibility_date (str | date): The compatibility date for the ESI client.
        ua_appname (str): Name of the App for generating a User-Agent,
        ua_version (str): Version of the App for generating a User-Agent,
        ua_url (str, Optional): URL To the Source Code or Documentation for generating a User-Agent,
        spec_file (str, Optional): Absolute path to a OpenApi 3.1 spec file to load.
        tenant (str, Optional): The ESI tenant to use (default: "tranquility").
        operations (list[str], Optional*): List of operations to filter the spec down.
        tags (list[str], Optional*): List of tags to filter the spec down.
    Functions:
        client(): ESIClient
        client_async(): ESIClientAsync
    """

    _client: ESIClient | None = None
    _client_async: ESIClientAsync | None = None

    def __init__(
        self,
        compatibility_date: str | dt.date,
        ua_appname: str,
        ua_version: str,
        ua_url: str | None = None,
        spec_file: None | str = None,
        tenant: str = "tranquility",
        operations: list[str] = [],
        tags: list[str] = [],
        **kwargs
    ) -> None:
        if type(compatibility_date) is dt.date:
            self._compatibility_date: str = self._date_to_string(compatibility_date)
        else:
            self._compatibility_date: str = str(compatibility_date)
        self._ua_appname = ua_appname
        self._ua_version = ua_version
        self._ua_url = ua_url
        self._spec_file = spec_file
        self._tenant = tenant
        self._kwargs = kwargs
        self._operations = operations
        self._tags = tags

    @property
    def client(self) -> ESIClient:
        if self._client is None:
            api = esi_client_factory_sync(
                compatibility_date=self._compatibility_date,
                ua_appname=self._ua_appname,
                ua_version=self._ua_version,
                ua_url=self._ua_url,
                spec_file=self._spec_file,
                tenant=self._tenant,
                operations=self._operations,
                tags=self._tags,
                **self._kwargs)
            self._client = ESIClient(api)
        return self._client

    @property
    async def client_async(self) -> ESIClientAsync:  # pragma: no cover
        if self._client_async is None:
            api = await esi_client_factory_async(
                compatibility_date=self._compatibility_date,
                ua_appname=self._ua_appname,
                ua_version=self._ua_version,
                ua_url=self._ua_url,
                spec_file=self._spec_file,
                tenant=self._tenant,
                operations=self._operations,
                tags=self._tags,
                **self._kwargs)
            self._client_async = ESIClientAsync(api)
        return self._client_async

    @classmethod
    def _date_to_string(cls, compatibility_date: dt.date) -> str:
        """Turns a date object in a compatibility_date string"""
        return f"{compatibility_date.year}-{compatibility_date.month:02}-{compatibility_date.day:02}"

    def __str__(self) -> str:
        return f"ESIClientProvider - {self._ua_appname} ({self._ua_version})"
