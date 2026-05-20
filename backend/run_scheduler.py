import os
import sys
import time
import logging

# Ensure the project root directory is in the search path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from backend.db import init_db
from backend.services.scheduler import start_scheduler

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
