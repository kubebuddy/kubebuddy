import os
import logging
from pathlib import Path
import datetime

# Defining directory where logs are to be stored
# Defining complete path to Log file
# Defining Log file name
LOGGING_DIR = os.path.join(os.path.dirname(Path(__file__).resolve().parent),'logs')
FILE_NAME = "KubeBuddy.log"
# {DATE}_KubeBuddy.log
LOG_FILE_PATH = os.path.join(LOGGING_DIR,FILE_NAME)

# # Defining file handler to save log data and set level to DEBUG
# file_handler = logging.FileHandler(LOG_FILE_PATH)
# file_handler.setLevel(logging.DEBUG)

timed_rotating_file_handler = logging.handlers.TimedRotatingFileHandler(
    LOG_FILE_PATH,
    when='S',
    interval = 5,
    backupCount=0,
    encoding='utf8',
)

timed_rotating_file_handler.setLevel(logging.DEBUG)

# Defining format of log data and setting it to file_handler
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

timed_rotating_file_handler.setFormatter(formatter)

# Defining logger, setting level and adding file handler
logger = logging.getLogger('app_logger')
logger.setLevel(logging.DEBUG)
logger.addHandler(timed_rotating_file_handler)