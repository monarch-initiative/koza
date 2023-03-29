import sys
import loguru

LOGURU_FORMAT = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name: <16}</cyan> | <level>{message}</level>"

def get_logger(verbose: bool = False, filename=None):
    logger = loguru.logger
    logger.remove()
    logger.add(
        sink=sys.stderr,
        level="INFO" if (verbose is None) else "DEBUG" if (verbose == True) else "WARNING",
        format=LOGURU_FORMAT,
        colorize=True,
    )
    if filename:
        logger.add(
            sink=filename,
            level="DEBUG",
            format="LOGURU_FORMAT",
            colorize=True,
        )
    return logger
