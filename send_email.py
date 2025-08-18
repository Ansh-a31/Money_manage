EMAIL_ADDRESS = "kanshuman571@gmail.com"
EMAIL_PASSWORD = "aqqg xbbq ocxy vryo"
RECIPIENT = "anshumanpep1111@gmail.com"

import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
    
def send_email_report(body):

    password =EMAIL_PASSWORD
    sender = EMAIL_ADDRESS
    recipients = RECIPIENT
    subject = "Automation script test. "
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = ', '.join(recipients)
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp_server:
       smtp_server.login(sender, password)
       smtp_server.sendmail(sender, recipients, msg.as_string())
    print("Message sent!")


def send_mail_with_attachment(body,email_subject):
    import smtplib
    from email import encoders
    from email.mime.base import MIMEBase
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    sender_email = "kanshuman571@gmail.com"
    sender_password = "aqqg xbbq ocxy vryo"
    recipient_email = "anshuman.kumar1@renewbuy.com"
    subject = email_subject
    # body = "with attachment"


    with open(body, "rb") as attachment:
        # Add the attachment to the message
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

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_email, message.as_string())
    print("Email sent!")
