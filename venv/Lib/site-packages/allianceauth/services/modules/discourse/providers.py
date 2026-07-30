from pydiscourse import DiscourseClient
from django.conf import settings

class DiscourseAPIClient():
    _client = None

    def __init__(self):
        pass

    @property
    def client(self):
        if not self._client:
            self._client = DiscourseClient(
                                settings.DISCOURSE_URL,
                                api_username=settings.DISCOURSE_API_USERNAME,
                                api_key=settings.DISCOURSE_API_KEY)
        return self._client

discourse = DiscourseAPIClient()
