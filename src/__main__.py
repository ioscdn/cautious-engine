from src import DEBUG, HTTP_URL, RETRY_FOR_MINUTES, RSS_URL, db, log, rclone

from .rss import RSSSync


def link_process(name):
    return HTTP_URL.format(name=name)


rss = RSSSync(
    rss_url=RSS_URL,
    db=db,
    rclone=rclone,
    link_process=link_process,
    retry_minutes=RETRY_FOR_MINUTES,
    debug=DEBUG,
)

if __name__ == "__main__":
    rss.check_new_entries()
    rss.check_failed_entries()
    db.dump()
