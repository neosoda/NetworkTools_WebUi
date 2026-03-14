
import smtplib
import requests
import logging
from email.mime.text import MIMEText
from email.utils import formatdate

logger = logging.getLogger(__name__)

class AlertManager:
    @staticmethod
    def send_teams_alert(webhook_url, title, message, color="0076D7"):
        if not webhook_url: return
        payload = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": color,
            "summary": title,
            "sections": [{
                "activityTitle": title,
                "activitySubtitle": formatdate(localtime=True),
                "text": message
            }]
        }
        try:
            requests.post(webhook_url, json=payload, timeout=5)
            logger.info("Teams alert sent.")
        except Exception as e:
            logger.error(f"Failed to send Teams alert: {e}")

    @staticmethod
    def send_email_alert(config, subject, body):
        smtp_server = config.get("smtp_server")
        smtp_port = config.get("smtp_port", 587)
        sender = config.get("sender_email")
        receiver = config.get("receiver_email")
        
        if not sender or not receiver: return
        
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = sender
        msg['To'] = receiver
        
        try:
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(sender, config.get("sender_password", ""))
                server.sendmail(sender, [receiver], msg.as_string())
            logger.info("Email alert sent.")
        except Exception as e:
            logger.error(f"Failed to send Email alert: {e}")
