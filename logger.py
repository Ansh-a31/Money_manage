# logger_config.py
import logging

# Configure the logger only once
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)

# Create a named logger
logger = logging.getLogger("my_app_logger")
