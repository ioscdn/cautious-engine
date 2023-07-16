import logging
import os
import sys

import pickledb
from dotenv import load_dotenv

from .rclone import Rclone

load_dotenv()
DEBUG = "--debug" in sys.argv or os.getenv("DEBUG", "False").lower() == "true"
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="[%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

try:
    HTTP_URL = os.environ["HTTP_URL"]  # Required
    RSS_URL = os.environ["RSS_URL"]  # Required
    RCLONE_CONFIG_PATH = os.getenv("RCLONE_CONFIG_PATH")  # Optional
    RCLONE_DEST = os.getenv("RCLONE_DEST")  # Optional
    RETRY_FOR_MINUTES = os.getenv("RETRY_FOR_MINUTES")  # Optional
    SEEDRCC_EMAIL = os.getenv("SEEDRCC_EMAIL")  # Optional
    SEEDRCC_PASSWORD = os.getenv("SEEDRCC_PASSWORD")  # Optional
    TORRENT_URL = os.getenv("TORRENT_URL")  # Optional
except KeyError as e:
    log.error(f"Missing environment variable: {e}")
    sys.exit(1)

db = pickledb.load("rss-data.json", True)
if "--reset-db" in sys.argv:
    db.deldb()

rclone = Rclone(config_path=RCLONE_CONFIG_PATH, default_dest=RCLONE_DEST, debug=DEBUG)
