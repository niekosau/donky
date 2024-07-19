import configparser
import dataclasses
import logging.config
import logging.handlers
import os
import logging
from donky._logger import CustomLogger, init_logger
from donky.helpers import drop_user_privileges

DEFAULT_NUM_PROC = 4
DEFAULT_LOG_LEVEL = "info"
DEFAULT_LOG_FORMAT = "%(message)s"
LOG_TRACE = 5


class CustomLoggerClass(logging.Logger):

    def __init__(self, name, level=logging.NOTSET):
        super().__init__(name, level)

    def trace(self, msg, *args, **kwargs):
        self.log(LOG_TRACE, msg, *args, **kwargs)


@dataclasses.dataclass()
class DonkySentry():
    """
    Dataclass for sentry_sdk
    """
    dsn: str
    traces_sample_rate: float
    env: str = dataclasses.field(default="dev")
    _logger = logging.getLogger("Donky")

    def __post_init__(self):
        """
        Initialize sentry sdk
        """
        self._logger.info("Initiazing sentry sdk")
        import sentry_sdk
        sentry_sdk.init(
            dsn=self.dsn,
            traces_sample_rate=self.traces_sample_rate,
            environment=self.env,
        )


@dataclasses.dataclass
class Obfuscators():
    """
    Dataclass for obfuscation
    """
    db_type: str
    backup_type: str
    backup_source: str
    obfuscator: str
    obfuscator_source: str
    repository: str
    search_name: str
    registry: str = dataclasses.field(default="docker.io")
    server_version: float = dataclasses.field(default=None)
    tool_version: float = dataclasses.field(default=None)
    image: str = dataclasses.field(default=None)
    backup_file: str = dataclasses.field(default=None)
    compressed: bool = dataclasses.field(default=False)

    def __post_init__(self):
        [self.__setattr__(k, v.strip('\"').strip("\'")) for k, v in self.__dict__.items() if isinstance(v, str)]


@dataclasses.dataclass()
class Donky():
    """
    Dataclass for main config section
    """
    user: str
    container_engine: str
    uid: int = dataclasses.field(default=os.getuid())
    log_level: str = dataclasses.field(default=DEFAULT_LOG_LEVEL)
    log_format: str = dataclasses.field(default=DEFAULT_LOG_FORMAT)
    num_process: int = dataclasses.field(default=4)
    tmp: str = dataclasses.field(default="/tmp")
    obfuscators: dict = dataclasses.field(default_factory=dict, init=False, repr=False)
    _logger: CustomLogger = dataclasses.field(default=None, repr=False)

    def __post_init__(self):
        self.uid = drop_user_privileges(user=self.user)
        self._logger = init_logger(log_level=self.log_level, log_format=self.log_format)


def parse_config(file: str) -> Donky:
    """
    Parse donky config
    """
    config = configparser.RawConfigParser()
    with open(file, "r") as config_file:
        config.read_file(config_file)
    donky = Donky(**config["Donky"])
    config.remove_section("Donky")
    donky._logger.debug("Checking for sentry section")
    if config.has_section("Donky:sentry"):
        DonkySentry(**config["Donky:sentry"])
        config.remove_section("Donky:sentry")
    donky._logger.info("Creating obfuscators classes")
    for section in config.sections():
        obf = Obfuscators(**config[section])
        donky.obfuscators[section] = obf
    return donky
