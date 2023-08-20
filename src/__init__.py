import logging
import sys

from .modules.config import Config
from .modules.database import ThreadSafePickleDB

config = Config(
    default_values={
        "DB_PATH": "rss-data.json",
        "DEBUG": "False",
        "ENTRY_ID_TAG": "title",
        "ENTRY_EXPIRE_HOURS": "72",
        "ENTRY_COMPARE_METHOD": "last_published_date",
        "WORKERS": "5",
    }
)

DEBUG = "--debug" in sys.argv or config.DEBUG.lower() == "true"

logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="[%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)


db = ThreadSafePickleDB(config.required.DB_PATH, True)
if "--reset-db" in sys.argv or config.RESET_DB:
    db.deldb()
