import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from contextlib import suppress

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
CREDENTIALS_PATH = os.path.join(BASE_DIR, "data", "emergency_credentials.json")

def _load_credentials():
    if not os.path.exists(CREDENTIALS_PATH):
        return None
    try:
        with open(CREDENTIALS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def dispatch_email_alert(message_body):
    creds = _load_credentials()
    if not creds:
        return False, "Credentials file not found."
    
    email_creds = creds.get("email", {})
    if not email_creds.get("enabled"):
        return False, "Email dispatch is disabled in credentials."
        
    sender = email_creds.get("sender_email")
    password = email_creds.get("sender_app_password")
    recipient = email_creds.get("recipient_email")
    
    if not sender or not password or not recipient or sender == "your-email@gmail.com":
        return False, "Email credentials are not configured completely."

    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = recipient
    msg['Subject'] = "EMERGENCY ALERT: Immediate Action Required"
    msg['X-Priority'] = '1'

    msg.attach(MIMEText(message_body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender, password)
        server.send_message(msg)
        server.quit()
        return True, "Emergency Email sent successfully."
    except Exception as e:
        return False, f"Failed to send email: {e}"

def dispatch_sms_alert(message_body):
    creds = _load_credentials()
    if not creds:
        return False, "Credentials file not found."
        
    sms_creds = creds.get("sms", {})
    if not sms_creds.get("enabled"):
        return False, "SMS dispatch is disabled in credentials."
        
    sid = sms_creds.get("twilio_account_sid")
    token = sms_creds.get("twilio_auth_token")
    from_num = sms_creds.get("twilio_phone_number")
    to_num = sms_creds.get("recipient_phone_number")
    
    if not sid or not token or not from_num or not to_num or sid == "ACyour_twilio_sid_here":
        return False, "SMS credentials are not configured completely."

    try:
        from twilio.rest import Client
        client = Client(sid, token)
        message = client.messages.create(
            body=f"EMERGENCY ALERT\n\n{message_body}",
            from_=from_num,
            to=to_num
        )
        return True, f"Emergency SMS sent successfully (SID: {message.sid})."
    except Exception as e:
        return False, f"Failed to send SMS: {e}"

def trigger_dual_emergency_protocol(location_text):
    message_body = "This is an emergency. Please contact me immediately."
    if location_text:
        message_body += f"\n\nMy saved location is: {location_text}"

    email_success, email_msg = dispatch_email_alert(message_body)
    sms_success, sms_msg = dispatch_sms_alert(message_body)

    results = []
    if email_success:
        results.append("Email sent")
    if sms_success:
        results.append("SMS sent")

    if not results:
        # Both failed or not configured, return False so fallback can trigger
        return False, "Neither Email nor SMS was configured properly."
    
    return True, f"Emergency alerts dispatched: {' and '.join(results)}."
