"""
Migration to AA Framework API method
"""

from django.conf import settings
from django.db import migrations, models

import allianceauth.framework.api.user


class Migration(migrations.Migration):

    dependencies = [
        ("fleetactivitytracking", "0006_auto_20180803_0430"),
    ]

    operations = [
        migrations.AlterField(
            model_name="fatlink",
            name="creator",
            field=models.ForeignKey(
                on_delete=models.SET(allianceauth.framework.api.user.get_sentinel_user),
                to=settings.AUTH_USER_MODEL
            ),
        ),
    ]
