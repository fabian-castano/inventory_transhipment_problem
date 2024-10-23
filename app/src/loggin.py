import logging
import os

from pythonjsonlogger import jsonlogger


class CustomFormatter(logging.Formatter):

    green = "\x1b[32;20m"
    grey = "\x1b[37;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"

    FORMATS = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: green + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


app_name = os.getenv('FRUBANA_APP_NAME', 'frubana_app')
env = os.getenv(f'{app_name}_ENV', '')
logger = logging.getLogger(app_name)
logger.propagate = False
default_logging_level = logging.DEBUG
logger.setLevel(default_logging_level)
logging_level = os.getenv(f'{app_name.upper()}_LOG_LEVEL')
if logging_level:
    logger.setLevel(logging.getLevelName(logging_level))
log_handler = None
if 'prod' in env.lower().strip():
    prod_stream_handler = logging.StreamHandler()
    prod_stream_handler.setLevel(logging.DEBUG)
    format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"
    default_msec_format = '%s.%03d'
    json_formatter = jsonlogger.JsonFormatter(fmt=format)
    json_formatter.default_msec_format = default_msec_format
    json_formatter.rename_fields = {
        'asctime': 'timestamp',
        'levelname': 'level',
    }
    prod_stream_handler.setFormatter(json_formatter)
    logger.addHandler(prod_stream_handler)
    log_handler = prod_stream_handler
else:
    custom_stream_handler = logging.StreamHandler()
    custom_stream_handler.setLevel(logging.DEBUG)
    custom_stream_handler.setFormatter(CustomFormatter())
    logger.addHandler(custom_stream_handler)
    log_handler = custom_stream_handler

# Set root logger
logging.getLogger().addHandler(log_handler)