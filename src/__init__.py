import logging
import sys

from .modules.config import Config
from .modules.database import ThreadSafePickleDB

config = Config(
    default=".env.sample"
)

DEBUG = "--debug" in sys.argv or config.DEBUG.lower() == "true"

logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="[%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)


db = ThreadSafePickleDB(config.required.DB_PATH, True)
if "--reset-db" in sys.argv or config.RESET_DB and config.RESET_DB.lower() == "true":
    db.deldb()
