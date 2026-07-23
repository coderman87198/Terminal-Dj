import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DJANGO_BACKEND = ROOT / "django_backend"
if str(DJANGO_BACKEND) not in sys.path:
    sys.path.insert(0, str(DJANGO_BACKEND))

from music.downloader import *
