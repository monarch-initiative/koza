import sys
import loguru

LOGURU_FORMAT = "<green>{time:YYYY-MM-DD_HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name: <16}</cyan> | <level>{message}</level>"
LOGURU_FORMAT_SIMPLE = "{time:YYYY-MM-DD_HH:mm:ss} | {level: <8} | {name: <16} | {message}"

def get_logger(name: str = None, verbose: bool = None):
    logger = loguru.logger
    logger.remove()
    logger.add(
        sink = sys.stderr,
        level = "INFO" if (verbose is None) else "DEBUG" if (verbose == True) else "WARNING",
        format = LOGURU_FORMAT,
        colorize = True,
    )
    if name:
        fp = f"logs/{name}"
        logger.add(
            sink = fp + "_{time:YYYYMMDD_HHmmss}.koza.log",
            level = "DEBUG",
            format = LOGURU_FORMAT_SIMPLE,
            colorize = True
        )
    return logger