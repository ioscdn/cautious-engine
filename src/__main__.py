import os
import sys
from datetime import datetime, timedelta
from time import mktime, time

import feedparser

from src import HTTP_URL, RETRY_FOR_MINUTES, RSS_URL, db, log, rclone


def get_last_checked_on():
    if db.exists("last_checked_on"):
        return datetime.fromisoformat(db.get("last_checked_on"))
    elif os.getenv("LAST_CHECKED_ON"):
        return datetime.fromisoformat(os.getenv("LAST_CHECKED_ON"))
    else:
        return datetime.fromtimestamp(0)


def copy(name):
    return rclone.copyurl(HTTP_URL.format(name=name))


def struct_time_to_datetime(struct_time):
    return datetime.fromtimestamp(mktime(struct_time))


def save_failed_entry(entry):
    if not db.exists("failed_entries"):
        db.dcreate("failed_entries")
    db.dadd("failed_entries", (entry.title, datetime.now().isoformat()))


def check_failed_entries():
    if db.exists("failed_entries"):
        failed_entries = list(db.dkeys("failed_entries"))
        if len(failed_entries) > 0:
            log.info(f"Found {len(failed_entries)} failed entries")
            for i, entry in enumerate(failed_entries):
                if datetime.now() - datetime.fromisoformat(
                    db.dget("failed_entries", entry)
                ) > timedelta(minutes=RETRY_FOR_MINUTES):
                    log.debug(f"Entry {entry} is older than 1 day, skipping...")
                    db.dpop("failed_entries", entry)
                else:
                    log.info(f"[{i+1}/{len(failed_entries)}] Retrying: {entry}")
                    start_time = time()
                    rclone_copy = copy(entry)
                    time_taken = int(time() - start_time)
                    if rclone_copy == 0:
                        log.info(
                            f"Copied successfully in {time_taken} seconds: {entry}"
                        )
                        db.dpop("failed_entries", entry)
                    else:
                        log.debug("Copy failed, skipping entry...")
        else:
            log.debug("No failed entries found")
            db.drem("failed_entries")


def check_for_new_items():
    feed = feedparser.parse(RSS_URL)
    feed.entries = filter(
        lambda x: struct_time_to_datetime(x.published_parsed) > get_last_checked_on(),
        feed.entries,
    )
    feed.entries = sorted(feed.entries, key=lambda x: x.published_parsed)
    total_entries = len(feed.entries)
    if total_entries == 0:
        log.info("No new items found")
    else:
        successfull_copies = 0
        log.info(f"Found {total_entries} new items")
        for i, entry in enumerate(feed.entries):
            if not "--dry-run" in sys.argv:
                log.info(f"[{i+1}/{total_entries}] Copying: {entry.title}")
                start_time = time()
                rclone_copy = copy(entry.title)
                time_taken = int(time() - start_time)
                if rclone_copy == 0:
                    log.info(
                        f"Copied successfully in {time_taken} seconds: {entry.title}"
                    )
                    successfull_copies += 1
                else:
                    log.error("Copy failed, adding entry to database...")
                    save_failed_entry(entry)
                db.set(
                    "last_checked_on",
                    datetime.fromtimestamp(mktime(entry.published_parsed)).isoformat(),
                )
            else:
                log.info(f"[{i+1}/{total_entries}] Skip Copying: {entry.title}")
                db.set(
                    "last_checked_on",
                    datetime.fromtimestamp(mktime(entry.published_parsed)).isoformat(),
                )
        log.info(f"Copied {successfull_copies} new items successfully")


if __name__ == "__main__":
    check_failed_entries()
    check_for_new_items()
    db.dump()
