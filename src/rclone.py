import logging
import subprocess


class Rclone:
    def __init__(
        self, config_path=None, default_dest=None, rclone_path="rclone", debug=False
    ) -> None:
        self.args = [rclone_path]
        if config_path:
            self.args.extend(["--config", config_path])
        self.default_dest = default_dest or "dest:"
        self.log = logging.getLogger(__name__)
        self.debug = debug
        if debug:
            self.log.setLevel(logging.DEBUG)
        self.log.debug(f"Rclone args: {self.args}")
        self.log.debug(f"Rclone default dest: {self.default_dest}")

    def rclone(self, args):
        self.log.debug(f"Running rclone {' '.join(args)}")
        process = subprocess.run([*self.args, *args], capture_output=True, text=True)
        if process.returncode != 0 and self.debug:
            self.log.warning(process.stdout.strip())
            self.log.warning(process.stderr.strip())
        return process.returncode

    def copyurl(self, url, dest=None, ignore_existing=True, auto_filename=True):
        args = [
            "copyurl",
            url,
            dest or self.default_dest,
        ]
        if ignore_existing:
            args.append("--ignore-existing")
        if auto_filename:
            args.append("--auto-filename")
        return self.rclone(args)
