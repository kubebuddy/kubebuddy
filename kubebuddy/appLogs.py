import os
import logging
from pathlib import Path
import datetime

# Defining directory where logs are to be stored.
LOGGING_DIR = os.path.join(os.path.dirname(Path(__file__).resolve().parent),'logs')
# Defining Log file name
DATE_TIME = str(datetime.date.today()) + '.log'
# Defining complete path to Log file
LOG_FILE_PATH = os.path.join(LOGGING_DIR,DATE_TIME)

# Defining file handler to save log data and set level to DEBUG
file_handler = logging.FileHandler(LOG_FILE_PATH)
file_handler.setLevel(logging.DEBUG)

# Defining format of log data and setting it to file_handler
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

file_handler.setFormatter(formatter)

# Defining logger, setting level and adding file handler
logger = logging.getLogger('app_logger')
logger.setLevel(logging.DEBUG)
logger.addHandler(file_handler)