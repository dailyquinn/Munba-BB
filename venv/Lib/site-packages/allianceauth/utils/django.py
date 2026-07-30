import sys
from copy import copy
from pathlib import Path


class StartupCommand:
    """Information about the command this Django instance was started with."""

    def __init__(self) -> None:
        self._argv = copy(sys.argv)

    @property
    def argv(self) -> list:
        """Return raw list of command line arguments."""
        return self._argv

    @property
    def script_name(self) -> str:
        """Return the base script name."""
        path = Path(self._argv[0])
        return path.name

    @property
    def is_management_command(self) -> bool:
        return self.script_name == "manage.py"
