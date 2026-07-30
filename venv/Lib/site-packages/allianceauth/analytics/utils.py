import os
from django.apps import apps
from allianceauth.authentication.models import User
from esi.models import Token


def install_stat_users() -> int:
    """Count and Return the number of User accounts

    Returns
    -------
    int
        The Number of User objects"""
    users = User.objects.count()
    return users


def install_stat_tokens() -> int:
    """Count and Return the number of ESI Tokens Stored

    Returns
    -------
    int
        The Number of Token Objects"""
    tokens = Token.objects.count()
    return tokens


def install_stat_addons() -> int:
    """Count and Return the number of Django Applications Installed

    Returns
    -------
    int
        The Number of Installed Apps"""
    addons = len(list(apps.get_app_configs()))
    return addons


def existence_baremetal_or_docker() -> str:
    """Checks the Installation Type of an install

    Returns
    -------
    str
        existence_baremetal or existence_docker"""
    docker_tag = os.getenv('AA_DOCKER_TAG')
    if docker_tag:
        return "existence_docker"
    return "existence_baremetal"
