import logging
from pathlib import Path

# Defining directory where logs are to be stored
# Defining complete path to Log file
# Defining Log file name
LOGGING_DIR = Path(__file__).resolve().parent / 'logs'
FILE_NAME = "KubeBuddy.log"
LOG_FILE_PATH = LOGGING_DIR / FILE_NAME

# Creating log directory
LOGGING_DIR.mkdir(exist_ok=True)

# Defining file handler to save log data and set level to DEBUG
timed_rotating_file_handler = logging.handlers.TimedRotatingFileHandler(
    LOG_FILE_PATH,
    when='midnight',
    interval = 1,
    backupCount=0,
    encoding='utf8',
)

# Overwriting namer method of timed rotating file handler 
def namer(name):
    return name.replace(".log", "") + ".log"

# Setting logging level to DEBUG, defining suffix for file name change and 
# replacing namer method of timed_rotating_file_handler to custom one
timed_rotating_file_handler.setLevel(logging.DEBUG)
timed_rotating_file_handler.suffix = "%Y-%m-%d"
timed_rotating_file_handler.namer = namer

# Defining format of log data and setting it to file_handler
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
timed_rotating_file_handler.setFormatter(formatter)

# Defining logger, setting level and adding file handler
logger = logging.getLogger('app_logger')
logger.setLevel(logging.DEBUG)
logger.addHandler(timed_rotating_file_handler)