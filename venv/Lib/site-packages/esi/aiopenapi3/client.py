import datetime as dt
import logging
from hashlib import md5

from httpx import URL, Client, Response
from httpx._client import USE_CLIENT_DEFAULT, UseClientDefault
from httpx._types import (
    AuthTypes, CookieTypes, HeaderTypes, QueryParamTypes, RequestExtensions,
    TimeoutTypes,
)

from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)


class SpecCachingClient(Client):
    REQUIRED_OPENAPI_KEYS = {"components", "info", "openapi", "paths", "servers", "tags"}

    @staticmethod
    def _is_spec(url: URL | str) -> bool:
        return "https://esi.evetech.net/meta/openapi" in str(url)

    @staticmethod
    def _get_seconds_to_dt() -> int:
        """
        Get the number of seconds until 11:30 AM the next day.

        :return:
        :rtype:
        """

        expire_time = timezone.now()
        target = expire_time.replace(hour=11, minute=30, second=0, microsecond=0)

        if expire_time >= target:
            target += dt.timedelta(days=1)

        return int((target - expire_time).total_seconds())

    def _get_spec_cache(self, url):
        cached_response = cache.get(self._get_api_cache_key(url), False)
        if cached_response and not self._spec_contains_expected_elements(cached_response):
            cache.delete(self._get_api_cache_key(url))
            logger.warning("Purged invalid cached ESI OpenAPI spec for %s", url)
            return False
        return cached_response

    def _set_spec_cache(self, url, body) -> None:
        ttl = self._get_seconds_to_dt()
        cache.set(self._get_api_cache_key(url), body, ttl)

    def _raise_for_invalid_spec_response(self, response: Response) -> None:
        if not isinstance(response, Response):
            raise TypeError("Invalid ESI OpenAPI spec response object")

        # Should we raise a custom rate limit expired for a 429 here?
        # or stick with HTTP errors, since we aren't even in the client yet.

        if not response.is_success:
            response.raise_for_status()

        if not self._spec_contains_expected_elements(response):
            raise ValueError("Invalid ESI OpenAPI spec response payload")

    def _spec_contains_expected_elements(self, response: Response) -> bool:
        if not isinstance(response, Response) or not response.is_success:
            return False

        try:
            payload = response.json()
        except ValueError:
            return False

        if not isinstance(payload, dict) or not self.REQUIRED_OPENAPI_KEYS.issubset(payload):
            return False

        return True

    def _get_api_cache_key(self, url: str) -> str:
        """
            provide a unique token for the spec url with compat date.
        """
        compat_date = self.headers.get("X-Compatibility-Date", None)
        return f"ESI_API_CACHE_{md5(f'{url}-{compat_date}'.encode()).hexdigest()}"

    def get(
        self,
        url: URL | str,
        *,
        params: QueryParamTypes | None = None,
        headers: HeaderTypes | None = None,
        cookies: CookieTypes | None = None,
        auth: AuthTypes | UseClientDefault | None = USE_CLIENT_DEFAULT,
        follow_redirects: bool | UseClientDefault = USE_CLIENT_DEFAULT,
        timeout: TimeoutTypes | UseClientDefault = USE_CLIENT_DEFAULT,
        extensions: RequestExtensions | None = None,
    ) -> Response:
        if self._is_spec(url):
            _spec = self._get_spec_cache(url)
            if not _spec:
                _spec = super().get(
                    url,
                    params=params,
                    headers=headers,
                    cookies=cookies,
                    auth=auth,
                    follow_redirects=follow_redirects,
                    timeout=timeout,
                    extensions=extensions
                )
                self._raise_for_invalid_spec_response(_spec)
                self._set_spec_cache(url, _spec)
            return _spec
        return super().get(
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            timeout=timeout,
            extensions=extensions
        )
