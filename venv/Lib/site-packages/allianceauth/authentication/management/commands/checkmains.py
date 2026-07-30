from django.core.management.base import BaseCommand
from allianceauth.authentication.models import UserProfile


class Command(BaseCommand):
    help = 'Ensures all main characters have an active ownership'

    def handle(self, *args, **options):
        profiles = UserProfile.objects.filter(main_character__isnull=False).filter(
            main_character__character_ownership__isnull=True)
        if profiles.exists():
            for profile in profiles:
                self.stdout.write(self.style.ERROR(
                    '{} does not have an ownership. Resetting user {} main character.'.format(profile.main_character,
                                                                                                profile.user)))
                profile.main_character = None
                profile.save()
            self.stdout.write(self.style.WARNING(f'Reset {profiles.count()} main characters.'))
        else:
            self.stdout.write(self.style.SUCCESS('All main characters have active ownership.'))
