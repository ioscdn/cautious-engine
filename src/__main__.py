import logging
from time import time

import feedparser

from src import DEBUG, config, rclone

from .modules.entry import Entry
from .rclone import Rclone
from .seedr import Seedrcc
from .worker import WorkerManager

log = logging.getLogger(__name__)

rclone = Rclone(
    config_path=config.RCLONE_CONFIG_PATH,
    default_dest=config.RCLONE_DEST,
    debug=DEBUG,
)

if config.SEEDRCC_EMAIL and config.SEEDRCC_PASSWORD:
    try:
        seedr = Seedrcc(config.SEEDRCC_EMAIL, config.SEEDRCC_PASSWORD)
        seedr.delete_all()
    except Exception as err:
        log.error(f"Seedrcc login failed: {err}")
        seedr = None
else:
    seedr = None


def seedr_copy(entry):
    link = config.required.TORRENT_URL.format(name=entry.title)
    result = False
    try:
        tor = seedr.download(link, filter_ext=[".mp4", ".mkv"])
        if tor.status == "finished":
            log.debug(f"Downloaded {link}")
            for file in tor.download_links:
                log.debug(f"Copying {file['name']}")
                rclone.copyurl(file["url"])
            result = True
        tor.delete()
    except TimeoutError as e:
        raise log.warning(f"Seedrcc Timeout: {e}")
    except Exception as e:
        raise log.warning(f"Seedrcc failed: {e}")
    finally:
        try:
            tor.delete()
        except:
            pass
    return result


def rclone_copy(entry):
    link = config.required.HTTP_URL.format(name=entry.title)
    rclone_copy = rclone.copyurl(link)
    return rclone_copy == 0


def handle_entry(entry: Entry, total: int, current: int):
    start_time = time()
    count = f"[{current}/{total}]"
    log.info(f"{count} Copying: {entry.title}")
    result = rclone_copy(entry)
    if not result and seedr and entry.is_failed:
        try:
            log.info("Rclone failed using seedrcc...")
            result = seedr_copy(entry)
        except Exception as e:
            log.debug(f"Seedrcc failed: {e}")
    if result:
        log.info(
            f"{count} Copied Successfully in {int(time() - start_time)}s: {entry.title}"
        )
    return result


def get_entries():
    feed = feedparser.parse(config.required.RSS_URL)
    entries = [
        {
            "title": entry.title,
            "published_parsed": entry.published_parsed,
        }
        for entry in feed.entries
    ]
    return entries


worker = WorkerManager(
    get_entries=get_entries,
    handle_entry=handle_entry,
)

if __name__ == "__main__":
    worker.check_new_entries()
