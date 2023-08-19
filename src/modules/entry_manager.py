from datetime import datetime
from time import mktime
from typing import List

from src import config

from .database import ThreadSafePickleDB
from .entry import Entry


class EntriesManager:
    def __init__(self, database: ThreadSafePickleDB):
        self.database = database
        self.compare_method = config.required.ENTRY_COMPARE_METHOD
        self.__create_database_entries()

    def __create_database_entries(self):
        if not self.database.exists("entries"):
            self.database.dcreate("entries")
        if self.compare_method == "last_published_date":
            if not self.database.exists("last_published_date"):
                if config.ENTRY_LAST_PUBLISHED_DATE:
                    self.database.set(
                        "last_published_date",
                        config.ENTRY_LAST_PUBLISHED_DATE,
                    )
                else:
                    self.database.set(
                        "last_published_date", datetime.fromtimestamp(0).isoformat()
                    )
        elif self.compare_method == "previous_entries":
            if not self.database.exists("previous_entries"):
                self.database.lcreate("previous_entries")
        else:
            raise ValueError(
                    f"Invalid compare method: {self.compare_method}, valid methods are: last_published_date, previous_entries")  # fmt: skip

    def __remove_entry(self, entry_id: str):
        if self.database.dget("entries", entry_id):
            self.database.dpop("entries", entry_id)
        else:
            raise KeyError(
                    f"Entry with id {entry_id} not found in database")  # fmt: skip

    def __save_entries(self, entries: List[Entry], name: str = "entries"):
        for entry in entries:
            self.database.dadd(name, (entry.id, entry.dict))

    def __dicts_to_entries(self, dicts: List[dict | Entry]) -> List[Entry]:
        return [Entry(_dict) if type(_dict) != Entry else _dict for _dict in dicts]

    def __get_last_published_date(self):
        return datetime.fromisoformat(self.database.get("last_published_date"))

    def __set_last_published_date(self, date: datetime):
        self.database.set("last_published_date", date.isoformat())

    def __struct_time_to_datetime(self, struct_time):
        return datetime.fromtimestamp(mktime(struct_time))

    def __get_previous_entries(self):
        return self.database.lgetall("previous_entries")

    def __add_previous_entry(self, entry_id: str):
        self.database.ladd("previous_entries", entry_id)

    def __remove_previous_entry(self, entry_id: str):
        self.database.lremvalue("previous_entries", entry_id)

    def get_entries(self, name: str = "entries"):
        for entry in self.database.dvals(name):
            entry = Entry(entry)
            if entry.expired:
                self.__remove_entry(entry.id)
            else:
                yield entry

    def set_success(self, entry_id: str):
        return self.__remove_entry(entry_id)

    def set_failed(self, entry_id: str):
        entry = self.database.dget("entries", entry_id)
        self.__remove_entry(entry_id)
        entry["is_failed"] = True
        self.__save_entries([Entry(entry)])

    def save_new_entries(self, entries: List[dict | Entry]):
        entries = self.__dicts_to_entries(entries)

        if self.compare_method == "last_published_date":
            last_published_date = self.__get_last_published_date()
            new_entries = list(
                filter(
                    lambda e: self.__struct_time_to_datetime(e.published_parsed)
                    > last_published_date,
                    entries,
                )
            )
            new_entries = sorted(new_entries, key=lambda x: x.published_parsed)
            if new_entries:
                self.__save_entries(new_entries)
                self.__set_last_published_date(
                    self.__struct_time_to_datetime(new_entries[-1].published_parsed)
                )

        elif self.compare_method == "previous_entries":
            previous_entries = self.__get_previous_entries()
            new_entries = []

            entries_ids = [entry.id for entry in entries]
            for entry_id in previous_entries:
                if entry_id not in entries_ids:
                    self.__remove_previous_entry(entry_id)

            for entry in entries:
                if entry.id not in previous_entries:
                    self.__add_previous_entry(entry.id)
                    new_entries.append(entry)
            self.__save_entries(new_entries)
