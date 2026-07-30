import logging

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User, Permission

from .models import UserProfile, CharacterOwnership, OwnershipRecord


logger = logging.getLogger(__name__)


class StateBackend(ModelBackend):
    @staticmethod
    def _get_state_permissions(user_obj):
        """returns permissions for state of given user object"""
        if hasattr(user_obj, "profile") and user_obj.profile:
            return Permission.objects.filter(state=user_obj.profile.state)
        else:
            return Permission.objects.none()

    def get_state_permissions(self, user_obj, obj=None):
        return self._get_permissions(user_obj, obj, 'state')

    def get_all_permissions(self, user_obj, obj=None):
        if not user_obj.is_active or user_obj.is_anonymous or obj is not None:
            return set()
        if not hasattr(user_obj, '_perm_cache'):
            user_obj._perm_cache = self.get_user_permissions(user_obj)
            user_obj._perm_cache.update(self.get_group_permissions(user_obj))
            user_obj._perm_cache.update(self.get_state_permissions(user_obj))
        return user_obj._perm_cache

    def authenticate(self, request=None, token=None, **credentials):
        if not token:
            return None
        try:
            ownership = CharacterOwnership.objects.get(character__character_id=token.character_id)
            if ownership.owner_hash == token.character_owner_hash:
                logger.debug(f'Authenticating {ownership.user} by ownership of character {token.character_name}')
                if ownership.user.profile.main_character:
                    if ownership.user.profile.main_character.character_id == token.character_id:
                        return ownership.user
                    else:  # this is an alt, enforce main only.
                        return None
            else:
                logger.debug(f'{token.character_name} has changed ownership. Creating new user account.')
                ownership.delete()
                return self.create_user(token)
        except CharacterOwnership.DoesNotExist:
            try:
                # insecure legacy main check for pre-sso registration auth installs
                profile = UserProfile.objects.get(main_character__character_id=token.character_id)
                logger.debug(f'Authenticating {profile.user} by their main character {profile.main_character} without active ownership.')
                # attach an ownership
                token.user = profile.user
                CharacterOwnership.objects.create_by_token(token)
                return profile.user
            except UserProfile.DoesNotExist:
                # now we check historical records to see if this is a returning user
                records = OwnershipRecord.objects.filter(owner_hash=token.character_owner_hash).filter(character__character_id=token.character_id)
                if records.exists():
                    # we've seen this character owner before. Re-attach to their old user account
                    user = records[0].user
                    if user.profile.main_character:
                        if user.profile.main_character.character_id != token.character_id:
                            # this is an alt, enforce main only due to trust issues in SSO.
                            return None

                    token.user = user
                    co = CharacterOwnership.objects.create_by_token(token)
                    logger.debug(f'Authenticating {user} by matching owner hash record of character {co.character}')

                    # set this as their main by default as they have none
                    user.profile.main_character = co.character
                    user.profile.save()
                    return user
            logger.debug(f'Unable to authenticate character {token.character_name}. Creating new user.')
            return self.create_user(token)

    def create_user(self, token):
        username = self.iterate_username(token.character_name)  # build unique username off character name
        user = User.objects.create_user(username, is_active=False)  # prevent login until email set
        user.set_unusable_password()  # prevent login via password
        user.save()
        token.user = user
        co = CharacterOwnership.objects.create_by_token(token)  # assign ownership to this user
        user.profile.main_character = co.character  # assign main character as token character
        user.profile.save()
        logger.debug(f'Created new user {user}')
        return user

    @staticmethod
    def iterate_username(name):
        name = str.replace(name, "'", "")
        name = str.replace(name, ' ', '_')
        if User.objects.filter(username__startswith=name).exists():
            u = User.objects.filter(username__startswith=name)
            num = len(u)
            username = f"{name}_{num}"
            while u.filter(username=username).exists():
                num += 1
                username = f"{name}_{num}"
        else:
            username = name
        return username
