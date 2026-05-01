# logger_config.py
import logging

# Configure the logger only once
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)

BOLD = "\033[1m"
RESET = "\033[0m"

# Create a named logger
logger = logging.getLogger("my_app_logger")

