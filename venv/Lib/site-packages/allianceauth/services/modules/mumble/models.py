import random
import string
from typing import ClassVar
from passlib.hash import bcrypt_sha256

from django.db import models
from django.contrib.auth.models import Group
from allianceauth.services.hooks import NameFormatter
from allianceauth.services.abstract import AbstractServiceModel
import logging

logger = logging.getLogger(__name__)


class MumbleManager(models.Manager):
    HASH_FN = 'bcrypt-sha256'

    @staticmethod
    def get_display_name(user):
        from .auth_hooks import MumbleService
        return NameFormatter(MumbleService(), user).format_name()

    @staticmethod
    def get_username(user):
        return user.profile.main_character.character_name  # main character as the user.username may be incorect

    @staticmethod
    def sanitise_username(username):
        return username.replace(" ", "_")

    @staticmethod
    def generate_random_pass():
        return ''.join([random.choice(string.ascii_letters + string.digits) for n in range(16)])

    @staticmethod
    def gen_pwhash(password):
        return bcrypt_sha256.encrypt(password.encode('utf-8'))

    def create(self, user):
        try:
            username = self.get_username(user)
            logger.debug(f"Creating mumble user with username {username}")
            username_clean = self.sanitise_username(username)
            display_name = self.get_display_name(user)
            password = self.generate_random_pass()
            pwhash = self.gen_pwhash(password)
            logger.debug("Proceeding with mumble user creation: clean username {}, pwhash starts with {}".format(
                username_clean, pwhash[0:5]))
            logger.info(f"Creating mumble user {username_clean}")

            result = super().create(user=user, username=username_clean,
                                                    pwhash=pwhash, hashfn=self.HASH_FN,
                                                    display_name=display_name)
            result.update_groups()
            result.credentials.update({'username': result.username, 'password': password})
            return result
        except AttributeError:  # No Main or similar errors
            return False
        return False

    def user_exists(self, username):
        return self.filter(username=username).exists()


class MumbleUser(AbstractServiceModel):
    user = models.OneToOneField(
        'auth.User',
        primary_key=True,
        on_delete=models.CASCADE,
        related_name='mumble'
    )
    username = models.CharField(max_length=254, unique=True)
    pwhash = models.CharField(max_length=90)
    hashfn = models.CharField(max_length=20, default='sha1')
    groups = models.TextField(blank=True, null=True)
    certhash = models.CharField(
        verbose_name="Certificate Hash",
        max_length=254,
        blank=True,
        null=True,
        editable=False,
        help_text="Hash of Mumble client certificate as presented when user authenticates"
    )
    display_name = models.CharField(
        max_length=254,
        unique=True
    )
    release = models.TextField(
        verbose_name="Mumble Release",
        max_length=254,
        blank=True,
        null=True,
        editable=False,
        help_text="Client release. For official releases, this equals the version. For snapshots and git compiles, this will be something else."
    )
    version = models.IntegerField(
        verbose_name="Mumble Version",
        blank=True,
        null=True,
        editable=False,
        help_text="Client version. Major version in upper 16 bits, followed by 8 bits of minor version and 8 bits of patchlevel. Version 1.2.3 = 0x010203."
    )
    last_connect = models.DateTimeField(
        verbose_name="Last Connection",
        max_length=254,
        blank=True,
        null=True,
        editable=False,
        help_text="Timestamp of the users Last Connection to Mumble"
    )
    last_disconnect = models.DateTimeField(
        verbose_name="Last Disconnection",
        max_length=254,
        blank=True,
        null=True,
        editable=False,
        help_text="Timestamp of the users Last Disconnection to Mumble"
    )

    objects: ClassVar[MumbleManager] = MumbleManager()

    def __str__(self):
        return self.username

    def update_password(self, password=None):
        init_password = password
        logger.debug(f"Updating mumble user %s password.")
        if not password:
            password = MumbleManager.generate_random_pass()
        pwhash = MumbleManager.gen_pwhash(password)
        logger.debug("Proceeding with mumble user {} password update - pwhash starts with {}".format(
            self.user, pwhash[0:5]))
        self.pwhash = pwhash
        self.hashfn = MumbleManager.HASH_FN
        self.save()
        if init_password is None:
            self.credentials.update({'username': self.username, 'password': password})

    def reset_password(self):
        self.update_password()

    def update_groups(self, groups: Group=None):
        if groups is None:
            groups = self.user.groups.all()
        groups_str = [self.user.profile.state.name]
        for group in groups:
            groups_str.append(str(group.name))
        safe_groups = ','.join({g.replace(' ', '-') for g in groups_str})
        logger.info(f"Updating mumble user {self.user} groups to {safe_groups}")
        self.groups = safe_groups
        self.save()
        return True

    def update_display_name(self):
        logger.info(f"Updating mumble user {self.user} display name")
        self.display_name = MumbleManager.get_display_name(self.user)
        self.save()
        return True

    class Meta:
        permissions = (
            ("access_mumble", "Can access the Mumble service"),
            ("view_connection_history", "Can access the connection history of the Mumble service"),
        )
