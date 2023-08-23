from datetime import datetime, timedelta

from dotmagic.utils import seconds

from src import config


class Entry:
    def __init__(self, entry: dict):
        self.__entry = entry
        self.__entry["created_at"] = entry.get("created_at", datetime.now().isoformat())
        self.__entry_id_tag = config.required.ENTRY_ID_TAG

    @property
    def id(self):
        return self.__entry[self.__entry_id_tag]

    @property
    def dict(self):
        return self.__entry

    @property
    def is_expired(self):
        return datetime.now() - datetime.fromisoformat(self.created_at) > timedelta(
            seconds=seconds(config.ENTRY_EXPIRE_TIME or "3d")
        )

    def __getitem__(self, key):
        return self.__entry[key]

    def __getattr__(self, key):
        try:
            return self.__entry[key]
        except KeyError:
            return None

    def __contains__(self, key):
        return key in self.__entry

    def __repr__(self):
        return f"<Entry {self.id}>"

    def __str__(self):
        return self.__repr__()
