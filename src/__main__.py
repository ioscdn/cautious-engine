from src import (DEBUG, HTTP_URL, RETRY_FOR_MINUTES, RSS_URL, SEEDRCC_EMAIL,
                 SEEDRCC_PASSWORD, TORRENT_URL, db, log, rclone)

from .rss import RSSSync
from .seedr import Seedrcc


def link_process(entry, using_seedr):
    if using_seedr:
        return TORRENT_URL.format(name=entry["title"])
    else:
        return HTTP_URL.format(name=entry["title"])


if SEEDRCC_EMAIL and SEEDRCC_PASSWORD:
    seedr = Seedrcc(SEEDRCC_EMAIL, SEEDRCC_PASSWORD)
    seedr.delete_all()
else:
    seedr = None

rss = RSSSync(
    rss_url=RSS_URL,
    db=db,
    rclone=rclone,
    link_process=link_process,
    retry_minutes=RETRY_FOR_MINUTES,
    debug=DEBUG,
    seedr=seedr,
)

if __name__ == "__main__":
    rss.check_new_entries()
    rss.check_failed_entries()
    db.dump()
