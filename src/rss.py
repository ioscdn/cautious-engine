import logging
import os
import sys
from datetime import datetime, timedelta
from time import mktime, time
from traceback import print_exc

import feedparser
from pickledb import PickleDB

from .rclone import Rclone
from .seedr import Seedrcc


class RSSSync:
    def __init__(
        self,
        rss_url,
        db: PickleDB,
        rclone: Rclone,
        link_process: callable = None,
        retry_minutes=24 * 60,
        debug=False,
        seedr: Seedrcc = None,
    ) -> None:
        self.seedr = seedr
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

    def struct_time_to_datetime(self, struct_time):
        return datetime.fromtimestamp(mktime(struct_time))

    def save_failed_entry(self, entry):
        if not self.db.exists("failed_entries"):
            self.db.lcreate("failed_entries")
        self.db.ladd(
            "failed_entries",
            {
                "title": entry.title,
                "link": entry.link,
                "published_parsed": entry.published_parsed,
                "expires_on": (
                    datetime.now() + timedelta(minutes=self.retry_minutes)
                ).isoformat(),
            },
        )

    def get_failed_entries(self):
        if self.db.exists("failed_entries"):
            failed_entries = list(self.db.lgetall("failed_entries"))

            if len(failed_entries) == 0:
                self.log.debug("No failed entries found")
                self.db.lremlist("failed_entries")
            else:
                self.log.info(f"Found {len(failed_entries)} failed entries")

            for entry in failed_entries:
                if datetime.now() > datetime.fromisoformat(entry["expires_on"]):
                    self.log.info(
                        f"Entry {entry} is older than {self.retry_minutes} minutes, removing..."
                    )
                    self.db.lremvalue("failed_entries", entry)
                    failed_entries.remove(entry)

            return failed_entries
        else:
            return []

    def get_dl_link(self, entry, using_seedr=False):
        if self.link_process:
            link = self.link_process(entry, using_seedr)
        else:
            link = entry.link
        return link

    def seedr_copy(self, entry):
        now = time()
        link = self.get_dl_link(entry, True)
        result = False
        if self.seedr:
            try:
                tor = self.seedr.add_download(link, filter_ext=[".mp4", ".mkv"])
                self.seedr.wait_for_torrents(tor, timeout=8 * 60)
                if tor.status == "finished":
                    self.log.debug(f"Downloaded {link}")
                    for file in tor.download_links:
                        self.log.debug(f"Copying {file['name']}")
                        self.rclone.copyurl(file["url"])
                    result = True
                tor.delete()
            except TimeoutError as e:
                tor.delete()
                raise Exception(f"Seedrcc timed out: {e}")
            except Exception as e:
                if "tor" in locals():
                    tor.delete()
                raise Exception(e)
        else:
            raise Exception("Seedrcc not initialized...")
        return result, int(time() - now)

    def rclone_copy(self, entry):
        now = time()
        link = self.get_dl_link(entry)
        rclone_copy = self.rclone.copyurl(link)
        return rclone_copy == 0, int(time() - now)

    def check_failed_entries(self):
        failed_entries = self.get_failed_entries()

        for i, entry in enumerate(failed_entries):
            self.log.info(f"[{i+1}/{len(failed_entries)}] Retrying: {entry['title']}")

            result, time_taken = self.rclone_copy(entry)
            if self.seedr and result == False:
                try:
                    self.log.info("Rclone failed using seedrcc...")
                    result, time_taken = self.seedr_copy(entry)
                except Exception as e:
                    self.log.debug(f"Seedrcc failed: {e}")
            if result == True:
                self.log.info(
                    f"Copied successfully in {time_taken} seconds: {entry['title']}"
                )
                self.db.lremvalue("failed_entries", entry)
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
                self.log.info(f"[{i+1}/{total_entries}] Copying: {entry.title}")
                result, time_taken = self.rclone_copy(entry)
                if result == True:
                    self.log.info(
                        f"Copied successfully in {time_taken} seconds: {entry.title}"
                    )
                    successfull_copies += 1
                else:
                    self.log.error("Copy failed, adding entry to database...")
                    self.save_failed_entry(entry)
                self.db.set(
                    "last_checked_on",
                    datetime.fromtimestamp(mktime(entry.published_parsed)).isoformat(),
                )
            self.log.info(f"Copied {successfull_copies} new items successfully")
