import logging
import os
import sys
from datetime import datetime, timedelta
from time import mktime, time

import feedparser
from pickledb import PickleDB

from .rclone import Rclone


class RSSSync:
    def __init__(
        self,
        rss_url,
        db: PickleDB,
        rclone: Rclone,
        link_process: callable = None,
        retry_minutes=24 * 60,
        debug=False,
    ) -> None:
        self.rss_url = rss_url
        self.db = db
        self.rclone = rclone
        self.log = logging.getLogger(__name__)
        self.link_process = link_process
        if debug:
            self.log.setLevel(logging.DEBUG)
        try:
            if int(retry_minutes) > 0:
                self.retry_minutes = int(retry_minutes)
            else:
                raise ValueError("Retry minutes must be greater than 0")
        except (ValueError, TypeError) as e:
            self.log.debug(
                "Invalid value for retry_minutes, using default value of 24 hours"
            )
            self.retry_minutes = 24 * 60

    @property
    def last_checked_on(self):
        if self.db.exists("last_checked_on"):
            return datetime.fromisoformat(self.db.get("last_checked_on"))
        elif os.getenv("LAST_CHECKED_ON"):
            return datetime.fromisoformat(os.getenv("LAST_CHECKED_ON"))
        else:
            return datetime.fromtimestamp(0)

    def get_dl_link(self, name):
        if self.link_process:
            name = self.link_process(name)
        return name

    def struct_time_to_datetime(self, struct_time):
        return datetime.fromtimestamp(mktime(struct_time))

    def save_failed_entry(self, name):
        if not self.db.exists("failed_entries"):
            self.db.dcreate("failed_entries")
        self.db.dadd("failed_entries", (name, datetime.now().isoformat()))

    def get_failed_entries(self):
        if self.db.exists("failed_entries"):
            failed_entries = list(self.db.dkeys("failed_entries"))

            if len(failed_entries) == 0:
                self.log.debug("No failed entries found")
                self.db.drem("failed_entries")
            else:
                self.log.info(f"Found {len(failed_entries)} failed entries")

            for entry in failed_entries:
                if datetime.now() - datetime.fromisoformat(
                    self.db.dget("failed_entries", entry)
                ) > timedelta(minutes=self.retry_minutes):
                    self.log.info(
                        f"Entry {entry} is older than {self.retry_minutes} minutes, removing..."
                    )
                    self.db.dpop("failed_entries", entry)
                    failed_entries.remove(entry)

            return failed_entries
        else:
            return []

    def clone(self, url):
        return self.rclone.copyurl(url)

    def check_failed_entries(self):
        failed_entries = self.get_failed_entries()

        for i, entry in enumerate(failed_entries):
            self.log.info(f"[{i+1}/{len(failed_entries)}] Retrying: {entry}")
            start_time = time()
            url = self.get_dl_link(entry)
            rclone_copy = self.clone(url)
            time_taken = int(time() - start_time)
            if rclone_copy == 0:
                self.log.info(f"Copied successfully in {time_taken} seconds: {entry}")
                self.db.dpop("failed_entries", entry)
            else:
                self.log.debug("Copy failed, skipping entry...")

    def check_new_entries(self):
        feed = feedparser.parse(self.rss_url)
        feed.entries = filter(
            lambda x: self.struct_time_to_datetime(x.published_parsed)
            > self.last_checked_on,
            feed.entries,
        )
        feed.entries = sorted(feed.entries, key=lambda x: x.published_parsed)
        total_entries = len(feed.entries)
        if total_entries == 0:
            self.log.info("No new items found")
        else:
            successfull_copies = 0
            self.log.info(f"Found {total_entries} new items")
            for i, entry in enumerate(feed.entries):
                if not "--dry-run" in sys.argv:
                    self.log.info(f"[{i+1}/{total_entries}] Copying: {entry.title}")
                    url = self.get_dl_link(entry.title)
                    start_time = time()
                    rclone_copy = self.clone(url)
                    time_taken = int(time() - start_time)
                    if rclone_copy == 0:
                        self.log.info(
                            f"Copied successfully in {time_taken} seconds: {entry.title}"
                        )
                        successfull_copies += 1
                    else:
                        self.log.error("Copy failed, adding entry to database...")
                        self.save_failed_entry(entry.title)
                    self.db.set(
                        "last_checked_on",
                        datetime.fromtimestamp(
                            mktime(entry.published_parsed)
                        ).isoformat(),
                    )
                else:
                    self.log.info(
                        f"[{i+1}/{total_entries}] Skip Copying: {entry.title}"
                    )
                    self.db.set(
                        "last_checked_on",
                        datetime.fromtimestamp(
                            mktime(entry.published_parsed)
                        ).isoformat(),
                    )
            self.log.info(f"Copied {successfull_copies} new items successfully")
