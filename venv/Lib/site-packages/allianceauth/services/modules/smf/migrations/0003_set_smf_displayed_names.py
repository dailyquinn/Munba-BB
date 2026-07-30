from django.db import migrations
from ..manager import SmfManager

def on_migrate(apps, schema_editor):
    SmfUser = apps.get_model("smf", "SmfUser")
    db_alias = schema_editor.connection.alias
    all_smf_users = SmfUser.objects.using(db_alias).all()

    for smf_user in all_smf_users:
        try:
            auth_user = smf_user.user
        except:
            pass
        else:
            SmfManager.update_display_name(auth_user)

def on_migrate_zero(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('smf', '0002_service_permissions'),
    ]

    operations = [
        migrations.RunPython(on_migrate, on_migrate_zero),
    ]
