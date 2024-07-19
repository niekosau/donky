import logging
import atexit
from multiprocessing import Queue

LOG_TRACE = 5
LOG_LEVELS = [
    "trace",
    "debug",
    "info",
    "warning",
    "error",
    "critical"
]


class CustomLogger(logging.Logger):

    def __init__(self, name, level=logging.NOTSET):
        super().__init__(name, level)
        setattr(logging.Logger, "trace", CustomLogger.trace)

    def trace(self, msg, *args, **kwargs):
        self.log(LOG_TRACE, msg, *args, **kwargs)


def init_logger(log_level: str, log_format: str) -> CustomLogger:
    """
    Initialize logging thread for non blocking logs
    """
    if log_level.lower() not in LOG_LEVELS:
        log_levels = ', '.join(LOG_LEVELS)
        raise ValueError(f"Log level {log_level} not from one of: {log_levels}")
    logging.addLevelName(LOG_TRACE, "TRACE")
    logging.setLoggerClass(CustomLogger)
    logger = logging.getLogger("Donky")
    log_level = logging.getLevelName(log_level.upper())
    logger.setLevel(log_level)
    con_log = logging.StreamHandler()
    format = logging.Formatter(log_format)
    con_log.setFormatter(format)
    log_queue = Queue()
    q_handler = logging.handlers.QueueHandler(log_queue)
    q_listener = logging.handlers.QueueListener(log_queue, con_log)
    q_listener.start()
    atexit.register(q_listener.stop)
    logger.addHandler(q_handler)
    return logger
