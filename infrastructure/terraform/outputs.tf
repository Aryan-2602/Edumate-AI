output "vpc_id" {
  description = "The ID of the VPC"
  value       = module.vpc.vpc_id
}

output "vpc_cidr_block" {
  description = "The CIDR block of the VPC"
  value       = module.vpc.vpc_cidr_block
}

output "private_subnets" {
  description = "List of IDs of private subnets"
  value       = module.vpc.private_subnets
}

output "public_subnets" {
  description = "List of IDs of public subnets"
  value       = module.vpc.public_subnets
}

output "nat_gateway_ids" {
  description = "List of NAT Gateway IDs"
  value       = module.vpc.nat_gateway_ids
}

output "alb_dns_name" {
  description = "The DNS name of the load balancer"
  value       = aws_lb.main.dns_name
}

output "alb_zone_id" {
  description = "The canonical hosted zone ID of the load balancer"
  value       = aws_lb.main.zone_id
}

output "alb_arn" {
  description = "The ARN of the load balancer"
  value       = aws_lb.main.arn
}

output "rds_endpoint" {
  description = "The endpoint of the RDS instance"
  value       = aws_db_instance.main.endpoint
}

output "rds_port" {
  description = "The port of the RDS instance"
  value       = aws_db_instance.main.port
}

output "rds_database_name" {
  description = "The name of the RDS database"
  value       = aws_db_instance.main.db_name
}

output "s3_bucket_name" {
  description = "The name of the S3 bucket for documents"
  value       = aws_s3_bucket.documents.bucket
}

output "s3_bucket_arn" {
  description = "The ARN of the S3 bucket for documents"
  value       = aws_s3_bucket.documents.arn
}

output "ecs_cluster_name" {
  description = "The name of the ECS cluster"
  value       = aws_ecs_cluster.main.name
}

output "ecs_cluster_arn" {
  description = "The ARN of the ECS cluster"
  value       = aws_ecs_cluster.main.arn
}

output "ecs_service_name" {
  description = "The name of the ECS service"
  value       = aws_ecs_service.main.name
}

output "ecs_service_arn" {
  description = "The ARN of the ECS service"
  value       = aws_ecs_service.main.id
}

output "ecs_task_definition_arn" {
  description = "The ARN of the ECS task definition"
  value       = aws_ecs_task_definition.main.arn
}

output "cloudwatch_log_group_name" {
  description = "The name of the CloudWatch log group"
  value       = aws_cloudwatch_log_group.main.name
}

output "cloudwatch_log_group_arn" {
  description = "The ARN of the CloudWatch log group"
  value       = aws_cloudwatch_log_group.main.arn
}

output "security_group_ecs_tasks_id" {
  description = "The ID of the ECS tasks security group"
  value       = aws_security_group.ecs_tasks.id
}

output "security_group_alb_id" {
  description = "The ID of the ALB security group"
  value       = aws_security_group.alb.id
}

output "security_group_rds_id" {
  description = "The ID of the RDS security group"
  value       = aws_security_group.rds.id
}

output "iam_role_ecs_execution_role_arn" {
  description = "The ARN of the ECS execution role"
  value       = aws_iam_role.ecs_execution_role.arn
}

output "iam_role_ecs_task_role_arn" {
  description = "The ARN of the ECS task role"
  value       = aws_iam_role.ecs_task_role.arn
}

output "appautoscaling_target_id" {
  description = "The ID of the application auto scaling target"
  value       = aws_appautoscaling_target.ecs_target.resource_id
}

output "appautoscaling_policy_arn" {
  description = "The ARN of the application auto scaling policy"
  value       = aws_appautoscaling_policy.ecs_policy.arn
}

# Connection information for the application
output "application_url" {
  description = "The URL to access the application"
  value       = "https://${aws_lb.main.dns_name}"
}

output "health_check_url" {
  description = "The URL to check application health"
  value       = "https://${aws_lb.main.dns_name}/health"
}

output "api_docs_url" {
  description = "The URL to access the API documentation"
  value       = "https://${aws_lb.main.dns_name}/docs"
}

# Database connection string (without password for security)
output "database_connection_info" {
  description = "Database connection information (without password)"
  value = {
    host     = aws_db_instance.main.endpoint
    port     = aws_db_instance.main.port
    database = aws_db_instance.main.db_name
    username = aws_db_instance.main.username
  }
}

# S3 bucket information
output "s3_bucket_info" {
  description = "S3 bucket information"
  value = {
    name = aws_s3_bucket.documents.bucket
    arn  = aws_s3_bucket.documents.arn
    region = aws_s3_bucket.documents.region
  }
}

# ECS service information
output "ecs_service_info" {
  description = "ECS service information"
  value = {
    cluster_name = aws_ecs_cluster.main.name
    service_name = aws_ecs_service.main.name
    desired_count = aws_ecs_service.main.desired_count
    task_definition_arn = aws_ecs_task_definition.main.arn
  }
}
