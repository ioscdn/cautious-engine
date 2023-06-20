import os
import random
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from time import mktime, time

import feedparser
import pickledb
from dotenv import load_dotenv

load_dotenv()

HTTP_URL = os.getenv("HTTP_URL")
RSS_URL = os.getenv("RSS_URL")
RCLONE_CONFIG_PATH = os.getenv("RCLONE_CONFIG_PATH")

db = pickledb.load("sync-data.json", True)
if "--reset-db" in sys.argv:
    db.deldb()

def get_last_checked_on():
    if db.exists("last_checked_on"):
        return datetime.fromisoformat(db.get("last_checked_on"))
    else:
        return datetime.fromtimestamp(0)


def rclone(args):
    # print(f"Running rclone {' '.join(args)}")
    process = subprocess.run(["rclone", *args], capture_output=True, text=True)
    if process.returncode != 0:
        print(process.stdout)
        print(process.stderr)
    return process.returncode


def copy(name):
    args = [
        "copyurl",
        HTTP_URL.format(name=name),
        f"dest:",
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
        print("No new items found")
    else:
        print(f"Found {len(feed.entries)} new items")
        for entry in feed.entries:
            if not "--dry-run" in sys.argv:
                print("Syncing:", entry.title)
                start_time = time()
                rclone_copy = copy(entry.title)
                time_taken = int(time() - start_time)
                if rclone_copy == 0:
                    print(f"Synced successfully in {time_taken} seconds: {entry.title}")
                    db.set(
                        "last_checked_on",
                        datetime.fromtimestamp(
                            mktime(entry.published_parsed)
                        ).isoformat(),
                    )
                else:
                    print("Sync failed, exiting...")
                    sys.exit(1)
            else:
                print("Dry run, not syncing:", entry.title)
                db.set(
                    "last_checked_on",
                    datetime.fromtimestamp(mktime(entry.published_parsed)).isoformat(),
                )
        print(f"Synced {len(feed.entries)} new items successfully")


if __name__ == "__main__":
    check_for_new_items()
