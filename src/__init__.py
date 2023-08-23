import logging
import sys

from dotmagic.config import Config

config = Config(default=".env.sample")

DEBUG = "--debug" in sys.argv or config.DEBUG.lower() == "true"

logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="[%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)
