from django import forms
from django.contrib import admin
from django.core.exceptions import ObjectDoesNotExist
from .providers import ObjectNotFound

from .models import EveAllianceInfo
from .models import EveCharacter
from .models import EveCorporationInfo
from .models import EveFactionInfo


class EveEntityExistsError(forms.ValidationError):
    def __init__(self, entity_type_name, id):
        super().__init__(
            message=f'{entity_type_name} with ID {id} already exists.')


class EveEntityNotFoundError(forms.ValidationError):
    def __init__(self, entity_type_name, id):
        super().__init__(
            message=f'{entity_type_name} with ID {id} not found.')


class EveEntityForm(forms.ModelForm):
    id = forms.IntegerField(min_value=1)
    entity_model_class = None

    def clean_id(self):
        raise NotImplementedError()

    def save(self, commit=True):
        raise NotImplementedError()

    def save_m2m(self):
        pass


def get_faction_choices():
    # use a method to avoid making an ESI call when the app loads
    # restrict to only those factions a player can join for faction warfare
    player_factions = [x for x in EveFactionInfo.provider.get_all_factions() if x['militia_corporation_id']]
    return [(x['faction_id'], x['name']) for x in player_factions]



class EveFactionForm(EveEntityForm):
    id = forms.ChoiceField(
        choices=get_faction_choices,
        label="Name"
    )

    def clean_id(self):
        try:
            assert self.Meta.model.provider.get_faction(self.cleaned_data['id'])
        except (AssertionError, ObjectNotFound):
            raise EveEntityNotFoundError('faction', self.cleaned_data['id'])
        if self.Meta.model.objects.filter(faction_id=self.cleaned_data['id']).exists():
            raise EveEntityExistsError('faction', self.cleaned_data['id'])
        return self.cleaned_data['id']

    def save(self, commit=True):
        faction = self.Meta.model.provider.get_faction(self.cleaned_data['id'])
        return self.Meta.model.objects.create(faction_id=faction.id, faction_name=faction.name)

    class Meta:
        fields = ['id']
        model = EveFactionInfo


class EveCharacterForm(EveEntityForm):
    entity_type_name = 'character'

    def clean_id(self):
        try:
            assert self.Meta.model.provider.get_character(self.cleaned_data['id'])
        except (AssertionError, ObjectNotFound):
            raise EveEntityNotFoundError(self.entity_type_name, self.cleaned_data['id'])
        if self.Meta.model.objects.filter(character_id=self.cleaned_data['id']).exists():
            raise EveEntityExistsError(self.entity_type_name, self.cleaned_data['id'])
        return self.cleaned_data['id']

    def save(self, commit=True):
        return self.Meta.model.objects.create_character(self.cleaned_data['id'])

    class Meta:
        fields = ['id']
        model = EveCharacter


class EveCorporationForm(EveEntityForm):
    entity_type_name = 'corporation'

    def clean_id(self):
        try:
            assert self.Meta.model.provider.get_corporation(self.cleaned_data['id'])
        except (AssertionError, ObjectNotFound):
            raise EveEntityNotFoundError(self.entity_type_name, self.cleaned_data['id'])
        if self.Meta.model.objects.filter(corporation_id=self.cleaned_data['id']).exists():
            raise EveEntityExistsError(self.entity_type_name, self.cleaned_data['id'])
        return self.cleaned_data['id']

    def save(self, commit=True):
        return self.Meta.model.objects.create_corporation(self.cleaned_data['id'])

    class Meta:
        fields = ['id']
        model = EveCorporationInfo


class EveAllianceForm(EveEntityForm):
    entity_type_name = 'alliance'

    def clean_id(self):
        try:
            assert self.Meta.model.provider.get_alliance(self.cleaned_data['id'])
        except (AssertionError, ObjectNotFound):
            raise EveEntityNotFoundError(self.entity_type_name, self.cleaned_data['id'])
        if self.Meta.model.objects.filter(alliance_id=self.cleaned_data['id']).exists():
            raise EveEntityExistsError(self.entity_type_name, self.cleaned_data['id'])
        return self.cleaned_data['id']

    def save(self, commit=True):
        return self.Meta.model.objects.create_alliance(self.cleaned_data['id'])

    class Meta:
        fields = ['id']
        model = EveAllianceInfo


@admin.register(EveFactionInfo)
class EveFactionInfoAdmin(admin.ModelAdmin):
    search_fields = ['faction_name']
    list_display = ('faction_name',)
    ordering = ('faction_name',)

    def has_change_permission(self, request, obj=None):
        return False

    def get_form(self, request, obj=None, **kwargs):
        if not obj or not obj.pk:
            return EveFactionForm
        return super().get_form(request, obj=obj, **kwargs)


@admin.register(EveCorporationInfo)
class EveCorporationInfoAdmin(admin.ModelAdmin):
    search_fields = ['corporation_name']
    list_display = ('corporation_name', 'alliance')
    list_select_related = ('alliance',)
    list_filter = (('alliance', admin.RelatedOnlyFieldListFilter),)
    ordering = ('corporation_name',)

    def has_change_permission(self, request, obj=None):
        return False

    def get_form(self, request, obj=None, **kwargs):
        if not obj or not obj.pk:
            return EveCorporationForm
        return super().get_form(request, obj=obj, **kwargs)


@admin.register(EveAllianceInfo)
class EveAllianceInfoAdmin(admin.ModelAdmin):
    search_fields = ['alliance_name']
    list_display = ('alliance_name',)
    ordering = ('alliance_name',)

    def has_change_permission(self, request, obj=None):
        return False

    def get_form(self, request, obj=None, **kwargs):
        if not obj or not obj.pk:
            return EveAllianceForm
        return super().get_form(request, obj=obj, **kwargs)


@admin.register(EveCharacter)
class EveCharacterAdmin(admin.ModelAdmin):
    search_fields = [
        'character_name',
        'corporation_name',
        'alliance_name',
        'character_ownership__user__username'
    ]
    list_display = (
        'character_name', 'corporation_name', 'alliance_name', 'faction_name', 'user', 'main_character'
    )
    list_select_related = (
        'character_ownership', 'character_ownership__user__profile__main_character'
    )
    list_filter = (
        'corporation_name',
        'alliance_name',
        'faction_name',
        (
            'character_ownership__user__profile__main_character',
            admin.RelatedOnlyFieldListFilter
        ),
    )
    ordering = ('character_name', )

    def has_change_permission(self, request, obj=None):
        return False

    @staticmethod
    def user(obj):
        try:
            return obj.character_ownership.user
        except (AttributeError, ObjectDoesNotExist):
            return None

    @staticmethod
    def main_character(obj):
        try:
            return obj.character_ownership.user.profile.main_character
        except (AttributeError, ObjectDoesNotExist):
            return None

    def get_form(self, request, obj=None, **kwargs):
        if not obj or not obj.pk:
            return EveCharacterForm
        return super().get_form(request, obj=obj, **kwargs)
