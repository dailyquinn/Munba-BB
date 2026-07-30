from django.db import migrations, models
from ..auth_hooks import MumbleService
from allianceauth.services.hooks import NameFormatter

def fwd_func(apps, schema_editor):
    MumbleUser = apps.get_model("mumble", "MumbleUser")
    db_alias = schema_editor.connection.alias
    all_users = MumbleUser.objects.using(db_alias).all()
    for user in all_users:
        display_name = NameFormatter(MumbleService(), user.user).format_name()
        user.display_name = display_name
        user.save()

def rev_func(apps, schema_editor):
    MumbleUser = apps.get_model("mumble", "MumbleUser")
    db_alias = schema_editor.connection.alias
    all_users = MumbleUser.objects.using(db_alias).all()
    for user in all_users:
        user.display_name = None
        user.save()


class Migration(migrations.Migration):

    dependencies = [
        ('mumble', '0008_mumbleuser_display_name'),
    ]

    operations = [
        migrations.RunPython(fwd_func, rev_func),
        migrations.AlterField(
            model_name='mumbleuser',
            name='display_name',
            field=models.CharField(max_length=254, unique=True),
            preserve_default=False,
        ),
    ]
