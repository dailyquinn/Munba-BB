import datetime
import logging

from django import forms
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import Timer

logger = logging.getLogger(__name__)


class TimerForm(forms.ModelForm):
    class Meta:
        model = Timer
        fields = ('details', 'system', 'planet_moon', 'structure', 'timer_type', 'objective', 'important', 'corp_timer')

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        if 'instance' in kwargs and kwargs['instance'] is not None:
            # Do conversion from db datetime to days/hours/minutes
            # for appropriate fields
            current_time = timezone.now()
            td = kwargs['instance'].eve_time - current_time
            initial = kwargs.pop('initial', dict())
            if 'days_left' not in initial:
                initial.update({'days_left': td.days})
            if 'hours_left' not in initial:
                initial.update({'hours_left': td.seconds // 3600})
            if 'minutes_left' not in initial:
                initial.update({'minutes_left': td.seconds // 60 % 60})
            kwargs.update({'initial': initial})
        super().__init__(*args, **kwargs)

    details = forms.CharField(max_length=254, required=True, label=_('Details'))
    system = forms.CharField(max_length=254, required=True, label=_("System"))
    planet_moon = forms.CharField(max_length=254, label=_("Planet/Moon"), required=False, initial="")
    structure = forms.ChoiceField(choices=Timer.Structure.choices, required=True, label=_("Structure Type"))
    timer_type = forms.ChoiceField(choices=Timer.TimerType.choices, label=_("Timer Type"))
    objective = forms.ChoiceField(choices=Timer.Objective.choices, required=True, label=_("Objective"))
    absolute_checkbox = forms.BooleanField(label=_("Absolute Timer"), required=False, initial=False)
    absolute_time = forms.CharField(required=False,label=_("Date and Time"))
    days_left = forms.IntegerField(required=False, label=_("Days Remaining"), validators=[MinValueValidator(0)])
    hours_left = forms.IntegerField(required=False, label=_("Hours Remaining"),
                                    validators=[MinValueValidator(0), MaxValueValidator(23)])
    minutes_left = forms.IntegerField(required=False, label=_("Minutes Remaining"), validators=[MinValueValidator(0), MaxValueValidator(59)])
    important = forms.BooleanField(label=_("Important"), required=False)
    corp_timer = forms.BooleanField(label=_("Corp-Restricted"), required=False)

    def save(self, commit=True):
        timer = super().save(commit=False)

        # Get character
        character = self.user.profile.main_character
        corporation = character.corporation
        logger.debug(f"Determined timer save request on behalf of character {character} corporation {corporation}")

        days_left = self.cleaned_data['days_left']
        hours_left = self.cleaned_data['hours_left']
        minutes_left = self.cleaned_data['minutes_left']
        absolute_time = self.cleaned_data['absolute_time']

        if days_left or hours_left or minutes_left:
            # Calculate future time
            future_time = datetime.timedelta(days=days_left, hours=hours_left, minutes=minutes_left)
            current_time = timezone.now()
            eve_time = current_time + future_time
            logger.debug(f"Determined timer EVE time is {eve_time} - current time {current_time}, adding {future_time}")
        elif absolute_time:
            # Use absolute time
            eve_time = absolute_time
        else:
            raise ValueError("Either future time or absolute time must be provided.")

        timer.eve_time = eve_time
        timer.eve_character = character
        timer.eve_corp = corporation
        timer.user = self.user

        if commit:
            timer.save()

        return timer
