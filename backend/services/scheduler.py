import csv
import logging
import os
import time
from apscheduler.schedulers.background import BackgroundScheduler
import requests

try:
    from backend.db import get_all_apis, add_log
    from backend.services.alert import send_alert_email
except ImportError:
    from db import get_all_apis, add_log
    from alert import send_alert_email

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Dictionary to track consecutive failures to avoid spamming
consecutive_failures = {}
# Dictionary to track alert status so we don't alert multiple times for the same prolonged outage
alert_sent_for = {}

CSV_LOG_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../logs/logs.csv")
)

def log_to_csv(api_name, status, response_time, state):
    try:
        file_exists = os.path.isfile(CSV_LOG_PATH)
        os.makedirs(os.path.dirname(CSV_LOG_PATH), exist_ok=True)
        with open(CSV_LOG_PATH, 'a', newline='') as csvfile:
            fieldnames = ['timestamp', 'api_name', 'status_code', 'response_time', 'state']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            
            from datetime import datetime
            dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            writer.writerow({
                'timestamp': dt,
                'api_name': api_name,
                'status_code': status,
                'response_time': response_time,
                'state': state
            })
    except Exception as e:
        logger.error(f"Error logging to CSV: {e}")

def check_api(api):
    api_id = api['id']
    name = api['name']
    url = api['url']
    threshold_ms = api['threshold_ms']
    
    start_time = time.time()
    try:
        response = requests.get(url, timeout=10)
        response_time_ms = int((time.time() - start_time) * 1000)
        status_code = response.status_code
        
        if 200 <= status_code < 400:
            if response_time_ms > threshold_ms:
                state = "SLOW"
                consecutive_failures[api_id] = 0
                
                # Check for continuous slow
                if alert_sent_for.get(api_id) != "SLOW":
                    send_alert_email(name, url, "SLOW", f"Response time {response_time_ms}ms exceeded threshold {threshold_ms}ms.")
                    alert_sent_for[api_id] = "SLOW"
            else:
                state = "OK"
                consecutive_failures[api_id] = 0
                if api_id in alert_sent_for:
                    del alert_sent_for[api_id] # Recovered, clear alert state
        else:
            state = "FAIL"
            consecutive_failures[api_id] = consecutive_failures.get(api_id, 0) + 1
            
    except requests.exceptions.RequestException as e:
        response_time_ms = int((time.time() - start_time) * 1000)
        status_code = 0 # 0 indicates failure to connect
        state = "FAIL"
        consecutive_failures[api_id] = consecutive_failures.get(api_id, 0) + 1
        
    add_log(api_id, status_code, response_time_ms, state)
    log_to_csv(name, status_code, response_time_ms, state)
    
    # Alert logic: 3 consecutive failures
    if consecutive_failures.get(api_id, 0) >= 3 and alert_sent_for.get(api_id) != "FAIL":
        send_alert_email(name, url, "FAIL", "API has failed 3 consecutive times.")
        alert_sent_for[api_id] = "FAIL"

scheduler = BackgroundScheduler()
# We will use this dictionary to track when an API was last checked
last_checked = {}

def dynamic_scheduler():
    apis = get_all_apis()
    current_time = time.time()
    for api in apis:
        api_id = api['id']
        interval = api['interval_seconds']
        if api_id not in last_checked or (current_time - last_checked[api_id]) >= interval:
            check_api(api)
            last_checked[api_id] = current_time

def start_scheduler():
    # Adding to scheduler to run every 5 seconds to provide tight looping
    # over intervals which may be set higher like 60s
    scheduler.add_job(dynamic_scheduler, 'interval', seconds=5)
    scheduler.start()
    logger.info("Scheduler started.")

def shutdown_scheduler():
    scheduler.shutdown()
