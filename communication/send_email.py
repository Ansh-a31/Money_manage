from Algo.credentials import EMAIL_ADDRESS, EMAIL_PASSWORD, RECIPIENT
from Algo.logger import logger

import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
    
def send_email_price_alert(body: str, subject: str = "Price Alert") -> bool:
    try:
        sender = EMAIL_ADDRESS
        password = EMAIL_PASSWORD.replace(" ", "") if EMAIL_PASSWORD else ""
        
        # Ensure recipients is a list of clean email strings
        if isinstance(RECIPIENT, list):
            recipients = [r.strip() for r in RECIPIENT if r.strip()]
        elif isinstance(RECIPIENT, str):
            recipients = [r.strip() for r in RECIPIENT.split(",") if r.strip()]
        else:
            recipients = [str(RECIPIENT)]

        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = sender
        msg['To'] = ', '.join(recipients)

        with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=15) as smtp_server:
            smtp_server.login(sender, password)
            smtp_server.sendmail(sender, recipients, msg.as_string())

        logger.info(f"[send_email_price_alert]: Alert email sent successfully to {recipients}")
        return True
    except smtplib.SMTPServerDisconnected as e:
        logger.error(
            f"[send_email_price_alert]: Connection unexpectedly closed by Gmail SMTP. "
            f"Google responded with 'WebLoginRequired' (534 5.7.9). "
            f"Please generate a fresh App Password or unlock your Google account via browser: {e}"
        )
        return False
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"[send_email_price_alert]: SMTP authentication failed: {e}. Check email/password.")
        return False
    except Exception as e:
        logger.error(f"[send_email_price_alert]: Failed to send email alert: {e}")
        return False


def send_mail_with_attachment(body: str, email_subject: str) -> bool:
    try:
        sender_email = EMAIL_ADDRESS
        sender_password = EMAIL_PASSWORD.replace(" ", "") if EMAIL_PASSWORD else ""
        recipient_email = "anshumanpep1111@gmail.com"
        subject = email_subject

        with open(body, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f"attachment; filename= '{body}'",
        )

        message = MIMEMultipart()
        message['Subject'] = subject
        message['From'] = sender_email
        message['To'] = recipient_email
        html_part = MIMEText(body)
        message.attach(html_part)
        message.attach(part)

        with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=15) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, [recipient_email], message.as_string())

        logger.info("[send_mail_with_attachment]: Email with attachment sent successfully!")
        return True
    except Exception as e:
        logger.error(f"[send_mail_with_attachment]: Failed to send email with attachment: {e}")
        return False
