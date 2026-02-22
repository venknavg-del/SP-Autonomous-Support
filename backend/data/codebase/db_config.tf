# Terraform DB Configuration
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
