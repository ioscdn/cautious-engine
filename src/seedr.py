import logging
import os
from time import time

from seedrcc import Login, Seedr

logging.getLogger("urllib3").setLevel(logging.WARNING)


class Torrent:
    def __init__(self, torrent, seedr: Seedr, filter_ext=None) -> None:
        self.seedr = seedr
        self.torrent_id = torrent["id"]
        self.name = torrent["name"]
        self.size = torrent["size"]
        self.filter_ext = filter_ext

    def get_info(self):
        return f"Torrent ID: {self.torrent_id} | Name: {self.name} | Size: {self.size}"

    def delete(self):
        status = self.status
        if status == "finished":
            self.seedr.deleteFolder(self.folder_id)
        elif status == "deleted":
            pass
        else:
            self.seedr.deleteTorrent(self.torrent_id)

    @property
    def contents(self):
        return self.seedr.listContents()

    @property
    def status(self):
        for torrent in self.contents["torrents"]:
            if torrent["id"] == self.torrent_id:
                return torrent["progress"]

        for folder in self.contents["folders"]:
            if folder["name"] == self.name and folder["size"] == self.size:
                self.folder_id = folder["id"]
                return "finished"

        return "deleted"

    @property
    def download_links(self):
        if not hasattr(self, "folder_id"):
            return None

        folder_contents = self.seedr.listContents(self.folder_id)
        file_links = []
        for file in folder_contents["files"]:
            if self.filter_ext:
                _, ext = os.path.splitext(file["name"])
                if ext.lower() not in self.filter_ext:
                    continue
            name = file["name"]
            link = self.seedr.fetchFile(file["folder_file_id"])
            file_links.append(dict(name=name, url=link["url"]))
        return file_links


class Seedrcc(Seedr):
    def __init__(self, username, password):
        login = Login(username, password)
        login.authorize()
        self.token = login.token
        super().__init__(token=self.token)

    def add_download(self, uri, filter_ext=None) -> Torrent:
        tor = None
        if uri.startswith("magnet"):
            tor = self.addTorrent(magnetLink=uri)
        else:
            tor = self.addTorrent(torrentFile=uri)
        if tor["code"] != 200:
            raise Exception(tor["error"])
        return self.get_torrent(
            torrent_id=tor["user_torrent_id"], filter_ext=filter_ext
        )

    @property
    def contents(self):
        return self.listContents()

    def get_torrent(self, torrent_id, filter_ext=None):
        for torrent in self.contents["torrents"]:
            if torrent["id"] == torrent_id:
                return Torrent(torrent, self, filter_ext=filter_ext)

    def wait_for_torrents(self, torrent: Torrent, timeout: int) -> Torrent:
        now = time()
        while torrent.status != "finished" and torrent.status != "deleted":
            print(time() - now)
            print(timeout)
            if time() - now > timeout:
                raise TimeoutError("Timeout while waiting for torrent to finish")
        return torrent

    def delete_all(self):
        for torrent in self.contents["torrents"]:
            self.deleteTorrent(torrent["id"])

        for folder in self.contents["folders"]:
            self.deleteFolder(folder["id"])

        for file in self.contents["files"]:
            self.deleteFile(file["id"])
