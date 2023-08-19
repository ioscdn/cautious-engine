import threading

import pickledb

database_lock = threading.RLock()


class ThreadSafeMeta(type):
    def __new__(cls, name, bases, attrs):
        wrapped_attrs = {}
        for attr_name, attr_value in attrs.items():
            if callable(attr_value):
                wrapped_attrs[attr_name] = cls.wrap_method_with_lock(attr_value)
            else:
                wrapped_attrs[attr_name] = attr_value

        return super().__new__(cls, name, bases, wrapped_attrs)

    @staticmethod
    def wrap_method_with_lock(method):
        def wrapped_method(self, *args, **kwargs):
            with database_lock:
                return method(self, *args, **kwargs)

        return wrapped_method


class ThreadSafePickleDB(pickledb.PickleDB, metaclass=ThreadSafeMeta):
    def __init__(self, location, auto_dump=True, sig=True):
        super().__init__(location, auto_dump, sig)
        self._lock = database_lock
