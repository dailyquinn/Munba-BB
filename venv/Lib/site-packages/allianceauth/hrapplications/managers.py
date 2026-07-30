from django.contrib.auth.models import User
from django.db import models
from typing import Optional


class ApplicationManager(models.Manager):

    def pending_requests_count_for_user(self, user: User) -> Optional[int]:
        """Returns the number of pending group requests for the given user"""
        if user.is_superuser:
            return self.filter(approved__isnull=True).count()
        elif user.has_perm("auth.human_resources"):
            main_character = user.profile.main_character
            if main_character:
                return (
                    self
                    .select_related("form__corp")
                    .filter(form__corp__corporation_id=main_character.corporation_id)
                    .filter(approved__isnull=True)
                    .count()
                )
            else:
                return None
        else:
            return None
