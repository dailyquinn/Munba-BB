import logging
import os

from bravado.exception import HTTPNotFound, HTTPUnprocessableEntity, HTTPError
from jsonschema.exceptions import RefResolutionError

from django.conf import settings
from esi.clients import esi_client_factory

from allianceauth import __version__, __title_useragent__, __url__
from allianceauth.utils.django import StartupCommand


SWAGGER_SPEC_PATH = os.path.join(os.path.dirname(
    os.path.abspath(__file__)), 'swagger.json'
)

# for the love of Bob please add operations you use here. I'm tired of breaking undocumented things.
ESI_OPERATIONS=[
    'get_alliances_alliance_id',
    'get_alliances_alliance_id_corporations',
    'get_corporations_corporation_id',
    'get_characters_character_id',
    'post_characters_affiliation',
    'get_universe_types_type_id',
    'get_universe_factions',
    'post_universe_names',
]


logger = logging.getLogger(__name__)


class ObjectNotFound(Exception):
    def __init__(self, obj_id, type_name):
        self.id = obj_id
        self.type = type_name

    def __str__(self):
        return f'{self.type} with ID {self.id} not found.'


class Entity:
    def __init__(self, id=None, name=None, **kwargs):
        super().__init__(**kwargs)
        self.id = id
        self.name = name

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<{self.__class__.__name__} ({self.id}): {self.name}>"

    def __bool__(self):
        return bool(self.id)

    def __eq__(self, other):
        return self.id == other.id


class AllianceMixin:
    def __init__(self, alliance_id=None, **kwargs):
        super().__init__(**kwargs)
        self.alliance_id = alliance_id
        self._alliance = None

    @property
    def alliance(self):
        if self.alliance_id:
            if not self._alliance:
                self._alliance = provider.get_alliance(self.alliance_id)
            return self._alliance
        return Entity(None, None)


class FactionMixin:
    def __init__(self, faction_id=None, **kwargs):
        super().__init__(**kwargs)
        self.faction_id = faction_id
        self._faction = None

    @property
    def faction(self):
        if self.faction_id:
            if not self._faction:
                self._faction = provider.get_faction(self.faction_id)
            return self._faction
        return Entity(None, None)


class Corporation(Entity, AllianceMixin, FactionMixin):
    def __init__(self, ticker=None, ceo_id=None, members=None, **kwargs):
        super().__init__(**kwargs)
        self.ticker = ticker
        self.ceo_id = ceo_id
        self.members = members
        self._ceo = None

    @property
    def ceo(self):
        if not self._ceo:
            self._ceo = provider.get_character(self.ceo_id)
        return self._ceo


class Alliance(Entity, FactionMixin):
    def __init__(self, ticker=None, corp_ids=None, executor_corp_id=None, **kwargs):
        super().__init__(**kwargs)
        self.ticker = ticker
        self.corp_ids = corp_ids
        self.executor_corp_id = executor_corp_id
        self._corps = {}

    def corp(self, id):
        assert id in self.corp_ids
        if id not in self._corps:
            self._corps[id] = provider.get_corp(id)
            self._corps[id]._alliance = self
        return self._corps[id]

    @property
    def corps(self):
        return sorted((self.corp(c_id) for c_id in self.corp_ids), key=lambda x: x.name)

    @property
    def executor_corp(self):
        if self.executor_corp_id:
            return self.corp(self.executor_corp_id)
        return Entity(None, None)


class Character(Entity, AllianceMixin, FactionMixin):
    def __init__(self, corp_id=None, **kwargs):
        super().__init__(**kwargs)
        self.corp_id = corp_id
        self._corp = None

    @property
    def corp(self):
        if not self._corp:
            self._corp = provider.get_corp(self.corp_id)
        return self._corp


class ItemType(Entity):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class EveProvider:
    def get_alliance(self, alliance_id):
        """
        :return: an Alliance object for the given ID
        """
        raise NotImplementedError()

    def get_corp(self, corp_id):
        """
        :return: a Corporation object for the given ID
        """
        raise NotImplementedError()

    def get_character(self, character_id):
        """
        :return: a Character object for the given ID
        """
        raise NotImplementedError()

    def get_itemtype(self, type_id):
        """
        :return: an ItemType object for the given ID
        """
        raise NotImplementedError()


class EveSwaggerProvider(EveProvider):
    def __init__(self, token=None, adapter=None):
        if settings.DEBUG or StartupCommand().is_management_command:
            self._client = None
            logger.info('ESI client will be loaded on-demand')
        else:
            logger.info('Loading ESI client')
            try:
                self._client = esi_client_factory(
                    token=token,
                    spec_file=SWAGGER_SPEC_PATH,
                    ua_appname=__title_useragent__,
                    ua_version=__version__,
                    ua_url=__url__
                )
            except (HTTPError, RefResolutionError):
                logger.exception(
                    'Failed to load ESI client on startup. '
                    'Switching to on-demand loading for ESI client.'
                )
                self._client = None

        self._token = token
        self.adapter = adapter or self
        self._faction_list = None  # what are the odds this will change? could cache forever!

    @property
    def client(self):
        if self._client is None:
            self._client = esi_client_factory(
                token=self._token,
                spec_file=SWAGGER_SPEC_PATH,
                ua_appname=__title_useragent__,
                ua_version=__version__,
                ua_url=__url__
            )
        return self._client

    def __str__(self):
        return 'esi'

    def get_alliance(self, alliance_id: int) -> Alliance:
        """Fetch alliance from ESI."""
        try:
            data = self.client.Alliance.get_alliances_alliance_id(alliance_id=alliance_id).result()
            corps = self.client.Alliance.get_alliances_alliance_id_corporations(alliance_id=alliance_id).result()
            model = Alliance(
                id=alliance_id,
                name=data['name'],
                ticker=data['ticker'],
                corp_ids=corps,
                executor_corp_id=data['executor_corporation_id'] if 'executor_corporation_id' in data else None,
                faction_id=data['faction_id'] if 'faction_id' in data else None,
            )
            return model
        except HTTPNotFound:
            raise ObjectNotFound(alliance_id, 'alliance')

    def get_corp(self, corp_id: int) -> Corporation:
        """Fetch corporation from ESI."""
        try:
            data = self.client.Corporation.get_corporations_corporation_id(corporation_id=corp_id).result()
            model = Corporation(
                id=corp_id,
                name=data['name'],
                ticker=data['ticker'],
                ceo_id=data['ceo_id'],
                members=data['member_count'],
                alliance_id=data['alliance_id'] if 'alliance_id' in data else None,
                faction_id=data['faction_id'] if 'faction_id' in data else None,
            )
            return model
        except HTTPNotFound:
            raise ObjectNotFound(corp_id, 'corporation')

    def get_character(self, character_id: int) -> Character:
        """Fetch character from ESI."""
        try:
            character_name = self._fetch_character_name(character_id)
            affiliation = self.client.Character.post_characters_affiliation(characters=[character_id]).result()[0]
            model = Character(
                id=character_id,
                name=character_name,
                corp_id=affiliation['corporation_id'],
                alliance_id=affiliation['alliance_id'] if 'alliance_id' in affiliation else None,
                faction_id=affiliation['faction_id'] if 'faction_id' in affiliation else None,
            )
            return model
        except (HTTPNotFound, HTTPUnprocessableEntity, ObjectNotFound):
            raise ObjectNotFound(character_id, 'character')

    def _fetch_character_name(self, character_id: int) -> str:
        """Fetch character name from ESI."""
        data = self.client.Universe.post_universe_names(ids=[character_id]).result()
        character = data.pop() if data else None
        if (
            not character
            or character["category"] != "character"
            or character["id"] != character_id
        ):
            raise ObjectNotFound(character_id, 'character')
        return character["name"]

    def get_all_factions(self):
        """Fetch all factions from ESI."""
        if not self._faction_list:
            self._faction_list = self.client.Universe.get_universe_factions().result()
        return self._faction_list

    def get_faction(self, faction_id: int):
        """Fetch faction from ESI."""
        faction_id = int(faction_id)
        try:
            if not self._faction_list:
                _ = self.get_all_factions()
            for f in self._faction_list:
                if f['faction_id'] == faction_id:
                    return Entity(id=f['faction_id'], name=f['name'])
            else:
                raise KeyError()
        except (HTTPNotFound, HTTPUnprocessableEntity, KeyError):
            raise ObjectNotFound(faction_id, 'faction')

    def get_itemtype(self, type_id: int) -> ItemType:
        """Fetch inventory item from ESI."""
        try:
            data = self.client.Universe.get_universe_types_type_id(type_id=type_id).result()
            return ItemType(id=type_id, name=data['name'])
        except (HTTPNotFound, HTTPUnprocessableEntity):
            raise ObjectNotFound(type_id, 'type')


provider = EveSwaggerProvider()
