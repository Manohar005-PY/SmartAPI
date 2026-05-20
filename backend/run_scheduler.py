import os
import sys
import time
import logging

# Ensure the backend directory is in the search path
backend_dir = os.path.abspath(os.path.dirname(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from db import init_db
from services.scheduler import start_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("run_scheduler")

if __name__ == "__main__":
    logger.info("Initializing database for Scheduler worker...")
    init_db()
    
    logger.info("Starting Scheduler in standalone worker process...")
    start_scheduler()
    
    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler worker stopping...")
