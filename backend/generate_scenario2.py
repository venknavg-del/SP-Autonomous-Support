import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import json
import base64

# ---------------------------------------------------------
# SCENARIO 2: INFRASTRUCTURE (DB Pool Exhaustion)
# ---------------------------------------------------------

# 1. Create Email (.eml)
msg = MIMEMultipart('related')
msg['Subject'] = 'Severity 2: Application Unresponsive, DB Timeouts'
msg['From'] = 'pagerduty@company.com'
msg['To'] = 'support@company.com'

textBody = """
Automated Alert: Database connection pool utilization has been consistently above 95% threshold for the last 15 minutes.
Application nodes are throwing connection timeout exceptions.
Please review the attached DB Metrics graph.
"""
msg.attach(MIMEText(textBody, 'plain'))

# Create a mock 1x1 blue pixel image to simulate a DB chart screenshot
img = MIMEImage(base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="))
img.add_header('Content-ID', '<db_metrics_chart>')
img.add_header('Content-Disposition', 'inline', filename='db_chart.png')
msg.attach(img)

with open("data/emails/scenario2_db_infra.eml", "wb") as f:
    f.write(msg.as_bytes())

# 2. Create Logs (.json)
logs2 = [
  {"timestamp": "2024-05-20T11:15:00Z", "level": "WARN", "message": "HikariPool-1 - Connection is not available, request timed out after 30000ms."},
  {"timestamp": "2024-05-20T11:15:05Z", "level": "ERROR", "message": "Failed to authenticate user: db connection timeout"}
]
with open("data/logs/scenario2_logs.json", "w") as f:
    json.dump(logs2, f, indent=2)

# 3. Create Codebase File (.tf)
tf_config = """# Terraform DB Configuration
resource "aws_db_instance" "production_db" {
  allocated_storage    = 100
  engine               = "postgres"
  engine_version       = "15.3"
  instance_class       = "db.r5.large"
  name                 = "prod_db_main"
  
  # Max connections tuned too low for current traffic
  parameter_group_name = "default.postgres15"
}

# In parameter_group:
# max_connections = 100
"""
with open("data/codebase/db_config.tf", "w") as f:
    f.write(tf_config)

print("Scenario 2 (Infra/DB) generated successfully.")
