from django.db import migrations


def remove_permission(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    ContentType = apps.get_model('contenttypes', 'ContentType')
    Permission = apps.get_model('auth', 'Permission')
    ct = ContentType.objects.get_for_model(User)
    Permission.objects.filter(codename="view_fleetup", content_type=ct, name="view_fleetup").delete()


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0016_ownershiprecord'),
    ]

    operations = [
        migrations.RunPython(remove_permission, migrations.RunPython.noop)
    ]
