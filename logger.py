# logger.py
import logging
from datetime import datetime
import pytz

from database import mongo_client   # Make sure this import is correct


class MongoErrorHandler(logging.Handler):
    """
    Custom handler that pushes ERROR and EXCEPTION logs to MongoDB collection 'error_logs'
    """
    def emit(self, record):
        try:
            if record.levelno < logging.ERROR:
                return

            log_entry = {
                "level": record.levelname,
                "message": record.getMessage(),
                "module": record.module,
                "funcName": record.funcName,
                "lineno": record.lineno,
                "pathname": record.pathname,
                "created_at": datetime.now(pytz.timezone("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S"),
            }

            # If it's an exception, also save the traceback
            if record.exc_info:
                import traceback
                log_entry["traceback"] = "".join(traceback.format_exception(*record.exc_info))

            mongo_client.push(doc=log_entry, collection_name="error_logs")

        except Exception as e:
            # Prevent infinite loop if MongoDB fails
            print(f"[MongoErrorHandler] Failed to save log: {e}")


# ====================== LOGGER SETUP ======================

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)

logger = logging.getLogger("my_app_logger")
logger.setLevel(logging.INFO)

# Add MongoDB Error Handler
mongo_handler = MongoErrorHandler()
mongo_handler.setLevel(logging.ERROR)  # Only ERROR and CRITICAL
logger.addHandler(mongo_handler)