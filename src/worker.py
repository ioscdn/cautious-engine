import logging
from queue import Queue
from threading import Lock, Thread
from traceback import format_exc

from src import DEBUG, config, db

from .modules.entry_manager import EntriesManager

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG if DEBUG else logging.INFO)


class WorkerManager:
    def __init__(
        self,
        handle_entry: callable,
        get_entries: callable,
    ) -> None:
        self.em = EntriesManager(db)
        self.handle_entry = handle_entry
        self.get_entries = get_entries
        self.queue = Queue()
        self.total = 0
        self.__completed = 0
        self.__failed = 0
        self._lock = Lock()

    def update_entries(self):
        entries = self.get_entries()
        self.em.save_new_entries(entries)

    def __get_current(self):
        with self._lock:
            self.__completed += 1
            return self.__completed
    
    def __increase_failed(self):
        with self._lock:
            self.__failed += 1
            return self.__failed

    def runners(self):
        while True:
            entry = self.queue.get()
            tag = f"[{self.__get_current()}/{self.total}]"
            try:
                result = self.handle_entry(entry=entry, tag=tag)
                if result:
                    self.em.set_success(entry.id)
                else:
                    self.em.set_failed(entry.id)
                    self.__increase_failed()
                log.debug(f"{tag} Task completed")
            except Exception:
                log.error(format_exc())
            self.queue.task_done()

    def start_threads(self, workers: int):
        for _ in range(workers):
            t = Thread(target=self.runners)
            t.daemon = True
            t.start()

    def check_new_entries(self):
        log.debug("Checking for new entries")
        self.update_entries()

        for entry in self.em.get_entries():
            self.queue.put(entry)

        self.total = self.queue.qsize()
        log.debug("Starting threads")
        log.info(f"Total tasks: {self.total}")
        self.start_threads(config.required.WORKERS)

        self.queue.join()
        log.info(f"[{self.__completed - self.__failed}/{self.total}] Tasks completed successfully")
        db.dump()
