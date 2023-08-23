import threading

from pickledb import PickleDB


class ThreadSafePickleDB(PickleDB):
    def __init__(self, location, auto_dump=True, sig=True):
        super().__init__(location, auto_dump, sig)
        self._lock = threading.RLock()

    def get(self, *args, **kwargs):
        with self._lock:
            return super().get(*args, **kwargs)

    def set(self, *args, **kwargs):
        with self._lock:
            return super().set(*args, **kwargs)

    def exists(self, *args, **kwargs):
        with self._lock:
            return super().exists(*args, **kwargs)

    def dcreate(self, *args, **kwargs):
        with self._lock:
            return super().dcreate(*args, **kwargs)

    def dadd(self, *args, **kwargs):
        with self._lock:
            return super().dadd(*args, **kwargs)

    def dpop(self, *args, **kwargs):
        with self._lock:
            return super().dpop(*args, **kwargs)

    def dgetall(self, *args, **kwargs):
        with self._lock:
            return super().dgetall(*args, **kwargs)

    def dvals(self, name):
        with self._lock:
            return super().dvals(name)

    def lcreate(self, *args, **kwargs):
        with self._lock:
            return super().lcreate(*args, **kwargs)

    def ladd(self, *args, **kwargs):
        with self._lock:
            return super().ladd(*args, **kwargs)

    def lpop(self, *args, **kwargs):
        with self._lock:
            return super().lpop(*args, **kwargs)

    def lgetall(self, *args, **kwargs):
        with self._lock:
            return super().lgetall(*args, **kwargs)

    def lget(self, *args, **kwargs):
        with self._lock:
            return super().lget(*args, **kwargs)

    def lremvalue(self, *args, **kwargs):
        with self._lock:
            return super().lremvalue(*args, **kwargs)
