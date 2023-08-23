import logging

from .handler import Handler
from .worker import WorkerManager

log = logging.getLogger(__name__)


handler = Handler()

worker = WorkerManager(
    get_entries=handler.feed,
    handle_entry=handler.handle,
    entries_manager=handler.entries_manager,
)

if __name__ == "__main__":
    worker.check_new_entries()
