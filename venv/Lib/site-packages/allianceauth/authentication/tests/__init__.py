from django.db.models.signals import (
    m2m_changed,
    post_save,
    pre_delete,
    pre_save
)
from django.urls import reverse
from unittest import mock

MODULE_PATH = 'allianceauth.authentication'


def patch(target, *args, **kwargs):
    return mock.patch(f'{MODULE_PATH}{target}', *args, **kwargs)


def get_admin_change_view_url(obj: object) -> str:
    """returns URL to admin change view for given object"""
    return reverse(
        'admin:{}_{}_change'.format(
            obj._meta.app_label, type(obj).__name__.lower()
        ),
        args=(obj.pk,)
    )


def get_admin_search_url(ModelClass: type) -> str:
    """returns URL to search URL for model of given object"""
    return '{}{}/'.format(
        reverse('admin:app_list', args=(ModelClass._meta.app_label,)),
        ModelClass.__name__.lower()
    )
