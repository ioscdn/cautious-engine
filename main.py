import logging
import os
import subprocess
import sys
from datetime import datetime
from time import mktime, time

import feedparser
import pickledb
from dotenv import load_dotenv

load_dotenv()
DEBUG = "--debug" in sys.argv or os.getenv("DEBUG").lower() == "true"
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
    if not RCLONE_DEST:
        log.debug("RCLONE_DEST not specified, using default 'dest:'")
        RCLONE_DEST = "dest:"
except KeyError as e:
    log.error(f"Missing environment variable: {e}")
    sys.exit(1)

db = pickledb.load("sync-data.json", True)
if "--reset-db" in sys.argv:
    db.deldb()


def get_last_checked_on():
    if db.exists("last_checked_on"):
        return datetime.fromisoformat(db.get("last_checked_on"))
    else:
        return datetime.fromtimestamp(0)


def rclone(args):
    log.debug(f"Running rclone {' '.join(args)}")
    process = subprocess.run(["rclone", *args], capture_output=True, text=True)
    if process.returncode != 0:
        log.warning(process.stdout)
        log.warning(process.stderr)
    return process.returncode


def copy(name):
    args = [
        "copyurl",
        HTTP_URL.format(name=name),
        RCLONE_DEST,
        "--ignore-existing",
        "--auto-filename",
    ]
    if RCLONE_CONFIG_PATH:
        args = ["--config", RCLONE_CONFIG_PATH, *args]
    return rclone(args)


def struct_time_to_datetime(struct_time):
    return datetime.fromtimestamp(mktime(struct_time))


def check_for_new_items():
    feed = feedparser.parse(RSS_URL)
    feed.entries = filter(
        lambda x: struct_time_to_datetime(x.published_parsed) > get_last_checked_on(),
        feed.entries,
    )
    feed.entries = sorted(feed.entries, key=lambda x: x.published_parsed)
    if len(feed.entries) == 0:
        log.info("No new items found")
    else:
        log.info(f"Found {len(feed.entries)} new items")
        for entry in feed.entries:
            if not "--dry-run" in sys.argv:
                log.info("Syncing:", entry.title)
                start_time = time()
                rclone_copy = copy(entry.title)
                time_taken = int(time() - start_time)
                if rclone_copy == 0:
                    log.info(
                        f"Synced successfully in {time_taken} seconds: {entry.title}"
                    )
                    db.set(
                        "last_checked_on",
                        datetime.fromtimestamp(
                            mktime(entry.published_parsed)
                        ).isoformat(),
                    )
                else:
                    log.error("Sync failed, exiting...")
                    sys.exit(1)
            else:
                log.info("Dry run, not syncing:", entry.title)
                db.set(
                    "last_checked_on",
                    datetime.fromtimestamp(mktime(entry.published_parsed)).isoformat(),
                )
        log.info(f"Synced {len(feed.entries)} new items successfully")


if __name__ == "__main__":
    check_for_new_items()
