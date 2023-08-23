import logging
import subprocess
from datetime import datetime, timedelta

log = logging.getLogger(__name__)


class Rclone:
    def __init__(
        self,
        config_path=None,
        default_dest=None,
        rclone_path="rclone",
        rate_limit_errors: list = None,
        rate_limit_wait_time: int = 600,
    ) -> None:
        self.args = [rclone_path]

        if config_path:
            self.args.extend(["--config", config_path])

        self.default_dest = default_dest or "dest:"
        self.rate_limit_errors = rate_limit_errors or []
        self.rate_limit_wait_time = timedelta(seconds=rate_limit_wait_time)
        self.is_rate_limited = False

        log.debug(f"Rclone args: {self.args}")
        log.debug(f"Rclone default dest: {self.default_dest}")

    def rclone(self, args):
        cmd = [*self.args, *args]
        log.debug(f"Running rclone: {' '.join(cmd)}")

        if self.is_rate_limited and datetime.now() < self.is_rate_limited:
            log.warning(
                f"Rate limited, waiting until {self.is_rate_limited.isoformat()}"
            )
            return 1

        process = subprocess.run(cmd, capture_output=True, text=True)

        if process.returncode != 0:
            log.debug(process.stdout.strip())
            log.debug(process.stderr.strip())

            for rate_limit_message in self.rate_limit_errors:
                if rate_limit_message in process.stderr:
                    self.is_rate_limited = datetime.now() + self.rate_limit_wait_time
                    log.warning(
                        f"Rate limited, waiting until {self.is_rate_limited.isoformat()}"
                    )

        return process.returncode

    def copyurl(
        self,
        url,
        dest=None,
        ignore_existing=True,
        auto_filename=True,
        retries=1,
        low_level_retries=5,
    ):
        args = []
        if retries:
            args.extend(["--retries", str(retries)])
        if low_level_retries:
            args.extend(["--low-level-retries", str(low_level_retries)])
        args.extend(
            [
                "copyurl",
                url,
                dest or self.default_dest,
            ]
        )
        if ignore_existing:
            args.append("--ignore-existing")
        if auto_filename:
            args.append("--auto-filename")
        return self.rclone(args)
