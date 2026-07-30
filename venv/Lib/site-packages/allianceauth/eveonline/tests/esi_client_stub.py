from bravado.exception import HTTPNotFound


class BravadoResponseStub:
    """Stub for IncomingResponse in bravado, e.g. for HTTPError exceptions"""

    def __init__(
        self, status_code, reason="", text="", headers=None, raw_bytes=None
    ) -> None:
        self.reason = reason
        self.status_code = status_code
        self.text = text
        self.headers = headers if headers else dict()
        self.raw_bytes = raw_bytes

    def __str__(self):
        return f"{self.status_code} {self.reason}"


class BravadoOperationStub:
    """Stub to simulate the operation object return from bravado via django-esi"""

    class RequestConfig:
        def __init__(self, also_return_response):
            self.also_return_response = also_return_response

    class ResponseStub:
        def __init__(self, headers):
            self.headers = headers

    def __init__(self, data, headers: dict = None, also_return_response: bool = False):
        self._data = data
        self._headers = headers if headers else {"x-pages": 1}
        self.request_config = BravadoOperationStub.RequestConfig(also_return_response)

    def result(self, **kwargs):
        if self.request_config.also_return_response:
            return [self._data, self.ResponseStub(self._headers)]
        else:
            return self._data

    def results(self, **kwargs):
        return self.result(**kwargs)


class EsiClientStub:
    """Stub for an ESI client."""
    class Alliance:
        @staticmethod
        def get_alliances_alliance_id(alliance_id):
            data = {
                3001: {
                    "name": "Wayne Enterprises",
                    "ticker": "WYE",
                    "executor_corporation_id": 2001
                }
            }
            try:
                return BravadoOperationStub(data[int(alliance_id)])
            except KeyError:
                response = BravadoResponseStub(
                    404, f"Alliance with ID {alliance_id} not found"
                )
                raise HTTPNotFound(response)

        @staticmethod
        def get_alliances_alliance_id_corporations(alliance_id):
            data = [2001, 2002, 2003]
            return BravadoOperationStub(data)

    class Character:
        @staticmethod
        def get_characters_character_id(character_id):
            data = {
                1001: {
                    "corporation_id": 2001,
                    "name": "Bruce Wayne",
                },
                1002: {
                    "corporation_id": 2001,
                    "name": "Peter Parker",
                },
                1011: {
                    "corporation_id": 2011,
                    "name": "Lex Luthor",
                }
            }
            try:
                return BravadoOperationStub(data[int(character_id)])
            except KeyError:
                response = BravadoResponseStub(
                    404, f"Character with ID {character_id} not found"
                )
                raise HTTPNotFound(response)

        @staticmethod
        def post_characters_affiliation(characters: list):
            data = [
                {'character_id': 1001, 'corporation_id': 2001, 'alliance_id': 3001},
                {'character_id': 1002, 'corporation_id': 2001, 'alliance_id': 3001},
                {'character_id': 1011, 'corporation_id': 2011},
                {'character_id': 1666, 'corporation_id': 1000001},
            ]
            return BravadoOperationStub(
                [x for x in data if x['character_id'] in characters]
            )

    class Corporation:
        @staticmethod
        def get_corporations_corporation_id(corporation_id):
            data = {
                2001: {
                    "ceo_id": 1091,
                    "member_count": 10,
                    "name": "Wayne Technologies",
                    "ticker": "WTE",
                    "alliance_id": 3001
                },
                2002: {
                    "ceo_id": 1092,
                    "member_count": 10,
                    "name": "Wayne Food",
                    "ticker": "WFO",
                    "alliance_id": 3001
                },
                2003: {
                    "ceo_id": 1093,
                    "member_count": 10,
                    "name": "Wayne Energy",
                    "ticker": "WEG",
                    "alliance_id": 3001
                },
                2011: {
                    "ceo_id": 1,
                    "member_count": 3,
                    "name": "LexCorp",
                    "ticker": "LC",
                },
                1000001: {
                    "ceo_id": 3000001,
                    "creator_id": 1,
                    "description": "The internal corporation used for characters in graveyard.",
                    "member_count": 6329026,
                    "name": "Doomheim",
                    "ticker": "666",
                }
            }
            try:
                return BravadoOperationStub(data[int(corporation_id)])
            except KeyError:
                response = BravadoResponseStub(
                    404, f"Corporation with ID {corporation_id} not found"
                )
                raise HTTPNotFound(response)

    class Universe:
        @staticmethod
        def post_universe_names(ids: list):
            data = [
                {"category": "character", "id": 1001, "name": "Bruce Wayne"},
                {"category": "character", "id": 1002, "name": "Peter Parker"},
                {"category": "character", "id": 1011, "name": "Lex Luthor"},
                {"category": "character", "id": 1666, "name": "Hal Jordan"},
                {"category": "corporation", "id": 2001, "name": "Wayne Technologies"},
                {"category": "corporation","id": 2002, "name": "Wayne Food"},
                {"category": "corporation","id": 1000001, "name": "Doomheim"},
            ]
            return BravadoOperationStub([x for x in data if x['id'] in ids])
