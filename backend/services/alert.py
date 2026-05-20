import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

from backend.config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def send_alert_email(api_name, api_url, issue_type, details):
    """
    Sends an alert email via SMTP based on the configuration.
    issue_type: 'FAIL' or 'SLOW'
    """
    if not Config.SMTP_PASSWORD or not Config.SMTP_USERNAME or Config.SMTP_PASSWORD == "your_app_password":
        logger.warning(f"SMTP not fully configured. Email would have been sent: {api_name} is {issue_type}")
        return

    subject = f"API Alert: {api_name} is {issue_type}"
    body = f"""
    The monitoring system has detected an issue with your API.
    
    API Name: {api_name}
    URL: {api_url}
    Issue: {issue_type}
    Details: {details}
    
    Please check the Smart API Health Monitoring Dashboard for more information.
    """

    msg = MIMEMultipart()
    msg['From'] = Config.SMTP_USERNAME
    msg['To'] = Config.ALERT_RECEIVER
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT)
        server.starttls()
        server.login(Config.SMTP_USERNAME, Config.SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        logger.info(f"Alert email sent successfully for {api_name}.")
    except Exception as e:
        logger.error(f"Failed to send email alert for {api_name}: {e}")
