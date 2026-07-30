from django.db import models

from allianceauth.authentication.models import State


class NameFormatConfig(models.Model):
    service_name = models.CharField(max_length=100, blank=False)
    default_to_username = models.BooleanField(
        default=True,
        help_text=
            'If a user has no main_character, '
            'default to using their Auth username instead.'
    )
    format = models.CharField(
        max_length=100,
        blank=False,
        help_text=
            'For information on constructing name formats '
            'please see the official documentation, '
            'topic "Services Name Formats".'
    )
    states = models.ManyToManyField(
        State,
        help_text=
            "States to apply this format to. You should only have one "
            "formatter for each state for each service."
    )

    def __str__(self):
        return '{}: {}'.format(
            self.service_name, ', '.join([str(x) for x in self.states.all()])
        )
