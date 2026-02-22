import os
import email
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import json
import base64

# Ensure directories exist
os.makedirs("data/emails", exist_ok=True)
os.makedirs("data/logs", exist_ok=True)
os.makedirs("data/codebase", exist_ok=True)

# ---------------------------------------------------------
# SCENARIO 1: CODE BUG (Payment Exception)
# ---------------------------------------------------------

# 1. Create Email (.eml)
msg = MIMEMultipart('related')
msg['Subject'] = 'Urgent: Site Down, Payment Gateway timeout'
msg['From'] = 'alerting@company.com'
msg['To'] = 'support@company.com'

textBody = """
We are seeing a huge spike in 500 errors on the checkout page. Customers cannot complete their orders.
Logs indicate a NullPointerException in the PaymentService.
See the attached screenshot of the error rate spike.
"""
msg.attach(MIMEText(textBody, 'plain'))

# Create a mock 1x1 red pixel image to simulate a chart screenshot
tiny_red_pixel = b'GIThubMockImageDataPixelRedOnlyForTesting1111'
img = MIMEImage(base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="))
img.add_header('Content-ID', '<error_rate_chart>')
img.add_header('Content-Disposition', 'inline', filename='chart.png')
msg.attach(img)

with open("data/emails/scenario1_payment_bug.eml", "wb") as f:
    f.write(msg.as_bytes())

# 2. Create Logs (.json)
logs1 = [
  {"timestamp": "2024-05-20T10:00:01Z", "level": "ERROR", "message": "NullPointerException in PaymentService.java:145 \n at com.company.PaymentService.process(PaymentService.java:145)"},
  {"timestamp": "2024-05-20T10:00:05Z", "level": "WARN", "message": "Transaction failed after 3 retries for user 7892"}
]
with open("data/logs/scenario1_logs.json", "w") as f:
    json.dump(logs1, f, indent=2)

# 3. Create Codebase File (.java)
java_code = """package com.company;

public class PaymentService {
    public void process(User user, double amount) {
        // BUG: unhandled potential null user object
        if (user.getBalance() < amount) {
            throw new InsufficientFundsException("Not enough funds");
        }
        user.setBalance(user.getBalance() - amount);
        save(user);
    }
}
"""
with open("data/codebase/PaymentService.java", "w") as f:
    f.write(java_code)


print("Successfully generated end-to-end sample data sets (Email with Image, Logs, Source Code).")
