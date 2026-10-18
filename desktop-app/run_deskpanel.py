"""Launcher (used by PyInstaller and by 'Start with Windows' when running from source)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from deskpanel.app import main  # noqa: E402

sys.exit(main())
