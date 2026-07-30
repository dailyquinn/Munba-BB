"""
Custom static files storage for Alliance Auth.

This module defines a custom static files storage class for
Alliance Auth, named `AaManifestStaticFilesStorage`.

Using `ManifestStaticFilesStorage` will give us a hashed name for
our static files, which is useful for cache busting.

This storage class extends Django's `ManifestStaticFilesStorage` to ignore missing files,
which the original class does not handle, and log them in debug mode.
It is useful for handling cases where static files may not exist, such as when a
CSS file references a background image that is not present in the static files directory.

With debug mode enabled, it will print a message for each missing file when running `collectstatic`,
which can help identify issues with static file references during development.
"""

from django.conf import settings
from django.contrib.staticfiles.storage import ManifestStaticFilesStorage


class AaManifestStaticFilesStorage(ManifestStaticFilesStorage):
    """
    Custom static files storage that ignores missing files.
    """

    @classmethod
    def _cleanup_name(cls, name: str) -> str:
        """
        Clean up the name by removing quotes.
        This method is used to ensure that the name does not contain any quotes,
        which can cause issues with file paths.

        :param name: The name of the static file.
        :type name: str
        :return: The cleaned-up name without quotes.
        :rtype: str
        """

        # Remove quotes from the name
        return name.replace('"', "").replace("'", "")

    def __init__(self, *args, **kwargs):
        """
        Initialize the static files storage, ignoring missing files.

        :param args:
        :type args:
        :param kwargs:
        :type kwargs:
        """

        self.missing_files = []

        super().__init__(*args, **kwargs)

    def hashed_name(self, name, content=None, filename=None):
        """
        Generate a hashed name for the given static file, ignoring missing files.

        Ignore missing files, e.g. non-existent background image referenced from css.
        Returns the original filename if the referenced file doesn't exist.

        :param name: The name of the static file to hash.
        :type name: str
        :param content: The content of the static file, if available.
        :type content: bytes | None
        :param filename: The original filename of the static file, if available.
        :type filename: str | None
        :return: The hashed name of the static file, or the original name if the file is missing.
        :rtype: str
        """

        try:
            clean_name = self._cleanup_name(name)

            return super().hashed_name(clean_name, content, filename)
        except ValueError as e:
            if settings.DEBUG:
                # In debug mode, we log the missing file message
                message = e.args[0].split(" with ")[0]
                self.missing_files.append(message)
                # print(f'\x1b[0;30;41m{message}\x1b[0m')

            return name

    def post_process(self, *args, **kwargs):
        """
        Post-process the static files, printing any missing files in debug mode.

        :param args:
        :type args:
        :param kwargs:
        :type kwargs:
        :return:
        :rtype:
        """

        yield from super().post_process(*args, **kwargs)

        if settings.DEBUG:
            # In debug mode, print the missing files
            for message in sorted(set(self.missing_files)):
                print(f"\x1b[0;30;41m{message}\x1b[0m")
