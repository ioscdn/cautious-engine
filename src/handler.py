import logging
from time import time
from urllib.parse import urlparse

import feedparser
import requests
from dotmagic.utils import seconds

from . import config
from .modules.entry_manager import LastPublishDateManager
from .rclone import Rclone
from .seedr import Seedrcc

log = logging.getLogger(__name__)


class Handler:
    def __init__(self):
        self.rss_url = config.required.RSS_URL
        self.channel = config.CHANNEL or urlparse(self.rss_url).netloc
        self.entries_manager = LastPublishDateManager(config.DB_PATH, self.channel)

        self.rclone = Rclone(
            config_path=config.RCLONE_CONFIG_PATH,
            default_dest=config.RCLONE_DEST,
            rate_limit_errors=config.RCLONE_RATE_LIMIT_ERRORS.strip().split("\n")
            if config.RCLONE_RATE_LIMIT_ERRORS
            else None,
            rate_limit_wait_time=seconds(config.RCLONE_RATE_LIMIT_WAIT_TIME or "15m"),
        )

        self.seedr = None
        if config.SEEDRCC_EMAIL and config.SEEDRCC_PASSWORD:
            try:
                self.seedr = Seedrcc(config.SEEDRCC_EMAIL, config.SEEDRCC_PASSWORD)
                self.seedr.delete_all()
            except Exception as err:
                log.error(f"Seedrcc login failed: {err}")
                self.seedr = None

        self.HTTP_URL = config.required.HTTP_URL
        self.TORRENT_URL = config.required.TORRENT_URL if self.seedr else None

    def rclone_copy(self, entry):
        link = config.required.HTTP_URL.format(name=entry.title)
        rclone_copy = self.rclone.copyurl(link)
        return rclone_copy == 0

    def seedr_copy(self, entry, tag):
        link = config.required.TORRENT_URL.format(name=entry.title)
        result = False
        try:
            tor = self.seedr.download(link, filter_ext=[".mp4", ".mkv"])
            if tor.status == "finished":
                log.debug(f"{tag} Downloaded {link}")
                links = tor.download_links
                if not links:
                    result = True
                else:
                    for file in links:
                        log.debug(f"{tag} Copying {file['name']}")
                        result = self.rclone.copyurl(file["url"]) == 0
            tor.delete()
        except TimeoutError as e:
            raise TimeoutError(f"{tag} Seedrcc Timeout: {e}")
        except Exception as e:
            raise Exception(f"{tag} Seedrcc failed: {e}")
        finally:
            try:
                tor.delete()
            except:
                pass
        return result

    def check_url(self, url: str):
        try:
            r = requests.head(url)
            return r.status_code == 200
        except:
            return False

    def handle(self, entry, tag):
        start_time = time()
        log.info(f"{tag} Copying: {entry.title}")
        result = self.rclone_copy(entry)
        if not result:
            check_url = self.check_url(self.HTTP_URL.format(name=entry.title))
            if check_url:
                log.info(f"{tag} Rclone failed")
            if not check_url and self.seedr:
                try:
                    log.info(f"{tag} http failed, using seedrcc...")
                    result = self.seedr_copy(entry, tag)
                except Exception as e:
                    log.debug(f"{tag} Seedrcc failed: {e}")
        if result:
            log.info(
                f"{tag} Copied Successfully in {int(time() - start_time)}s: {entry.title}"
            )
        return result

    def feed(self):
        feed = feedparser.parse(self.rss_url)
        entries = [
            {
                "title": entry.title,
                "published_parsed": entry.published_parsed,
            }
            for entry in feed.entries
        ]
        return entries
