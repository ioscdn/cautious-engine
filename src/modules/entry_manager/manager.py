import os
from datetime import datetime
from time import mktime
from typing import List

from src.modules.entry_manager.entry import Entry

from .base import EntriesManager
from .entry import Entry


class LastPublishDateManager(EntriesManager):
    def __init__(self, database: str = None, channel: str = "default"):
        super().__init__(database, channel)
        self.last_published_date_key = "last_published_date:" + self.channel
        self.ensure_entries()

    def ensure_entries(self):
        if not self.database.exists(self.last_published_date_key):
            self.database.set(
                self.last_published_date_key,
                os.getenv("LAST_PUBLISHED_DATE", datetime.fromtimestamp(0).isoformat()),
            )

    def get_last_published_date(self):
        return datetime.fromisoformat(self.database.get(self.last_published_date_key))

    def set_last_published_date(self, date: datetime):
        self.database.set(self.last_published_date_key, date.isoformat())

    def struct_time_to_datetime(self, struct_time):
        return datetime.fromtimestamp(mktime(struct_time))

    def feed_new_entries(
        self, entries: List[dict | Entry], key_name: str = "published_parsed"
    ):
        entries = super().dicts_to_entries(entries)
        last_published_date = self.get_last_published_date()
        new_entries = list(
            filter(
                lambda e: self.struct_time_to_datetime(e[key_name])
                > last_published_date,
                entries,
            )
        )
        new_entries = sorted(new_entries, key=lambda x: x[key_name])
        if new_entries:
            self.set_last_published_date(
                self.struct_time_to_datetime(new_entries[-1][key_name])
            )

        super().save_entries(new_entries)


class LastEntriesManager(EntriesManager):
    def __init__(
        self,
        database: str = None,
        channel: str = "default",
    ):
        super().__init__(database, channel)
        self.last_entries_key = "last_entries:" + self.channel
        self.ensure_entries()

    def ensure_entries(self):
        if not self.database.exists(self.last_entries_key):
            self.database.lcreate(self.last_entries_key)

    def get_last_entries(self):
        return self.database.lgetall(self.last_entries_key)

    def add_last_entry(self, entry_id: str):
        self.database.ladd(self.last_entries_key, entry_id)

    def remove_last_entry(self, entry_id: str):
        self.database.lremvalue(self.last_entries_key, entry_id)

    def feed_new_entries(self, entries: List[dict | Entry]):
        entries = super().dicts_to_entries(entries)
        last_entries = self.get_last_entries()
        new_entries = []
        entries_ids = [entry.id for entry in entries]
        for entry_id in last_entries:
            if entry_id not in entries_ids:
                self.remove_last_entry(entry_id)

        for entry in entries:
            if entry.id not in last_entries:
                self.add_last_entry(entry.id)
                new_entries.append(entry)

        super().save_entries(new_entries)
