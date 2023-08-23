from typing import List

from .database import ThreadSafePickleDB
from .entry import Entry


class EntriesManager:
    def __init__(
        self,
        database: str = None,
        channel: str = None,
    ):
        self.database = ThreadSafePickleDB(
            database or "entries-data.json", auto_dump=True
        )
        self.channel = channel or "default"
        self.entries_key = "entries:" + channel
        self.__create_database_entries()

    def __create_database_entries(self):
        if not self.database.exists(self.entries_key):
            self.database.dcreate(self.entries_key)

    def remove_entry(self, entry_id: str):
        if self.database.dget(self.entries_key, entry_id):
            self.database.dpop(self.entries_key, entry_id)
        else:
            raise KeyError(
                    f"Entry with id {entry_id} not found in database")  # fmt: skip

    def save_entries(self, entries: List[Entry]):
        for entry in entries:
            self.database.dadd(self.entries_key, (entry.id, entry.dict))

    def dicts_to_entries(self, dicts: List[dict | Entry]) -> List[Entry]:
        return [Entry(_dict) if type(_dict) != Entry else _dict for _dict in dicts]

    def get_entries(self):
        for entry in list(self.database.dvals(self.entries_key)):
            entry = Entry(entry)
            if entry.is_expired:
                self.remove_entry(entry.id)
            else:
                yield entry

    def set_success(self, entry_id: str):
        return self.remove_entry(entry_id)

    def set_failed(self, entry_id: str):
        entry = self.database.dget(self.entries_key, entry_id)
        if not entry.get("is_failed", False):
            self.remove_entry(entry_id)
            entry["is_failed"] = True
            self.save_entries([Entry(entry)])
