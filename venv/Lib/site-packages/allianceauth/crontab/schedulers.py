from django.core.exceptions import ObjectDoesNotExist
from django_celery_beat.schedulers import (
    DatabaseScheduler
)
from django_celery_beat.models import CrontabSchedule
from django.db.utils import OperationalError, ProgrammingError

from celery import schedules
from celery.utils.log import get_logger

from allianceauth.crontab.models import CronOffset
from allianceauth.crontab.utils import offset_cron

logger = get_logger(__name__)


class OffsetDatabaseScheduler(DatabaseScheduler):
    """
    Customization of Django Celery Beat, Database Scheduler
    Takes the Celery Schedule from local.py and applies our AA Framework Cron Offset, if apply_offset is true
    Otherwise it passes it through as normal
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def update_from_dict(self, mapping):
        s = {}

        try:
            cron_offset = CronOffset.get_solo()
        except (OperationalError, ProgrammingError, ObjectDoesNotExist) as exc:
            # This is just incase we haven't migrated yet or something
            logger.warning(
                "OffsetDatabaseScheduler: Could not fetch CronOffset (%r). "
                "Defering to DatabaseScheduler",
                exc
            )
            return super().update_from_dict(mapping)

        for name, entry_fields in mapping.items():
            try:
                apply_offset = entry_fields.pop("apply_offset", False)  # Ensure this pops before django tries to save to ORM
                entry = self.Entry.from_entry(name, app=self.app, **entry_fields)

                if apply_offset:
                    entry_fields.update({"apply_offset": apply_offset})  # Reapply this as its gets pulled from config inconsistently.
                    schedule_obj = entry.schedule
                    if isinstance(schedule_obj, schedules.crontab):
                        offset_cs = CrontabSchedule.from_schedule(offset_cron(schedule_obj))
                        offset_cs, created = CrontabSchedule.objects.get_or_create(
                            minute=offset_cs.minute,
                            hour=offset_cs.hour,
                            day_of_month=offset_cs.day_of_month,
                            month_of_year=offset_cs.month_of_year,
                            day_of_week=offset_cs.day_of_week,
                            timezone=offset_cs.timezone,
                        )
                        entry.schedule = offset_cron(schedule_obj)  # This gets passed into Celery Beats Memory, important to keep it in sync with the model/DB
                        entry.model.crontab = offset_cs
                        entry.model.save()
                        logger.debug(f"Offset applied for '{name}' due to 'apply_offset' = True.")

                if entry.model.enabled:
                    s[name] = entry

            except Exception as e:
                logger.exception("Error updating schedule for %s: %r", name, e)

        self.schedule.update(s)
