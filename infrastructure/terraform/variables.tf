variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
  
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "db_username" {
  description = "Database username"
  type        = string
  sensitive   = true
}

variable "db_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}

variable "rds_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "ecs_cpu" {
  description = "ECS task CPU units (1024 = 1 vCPU)"
  type        = number
  default     = 512
  
  validation {
    condition     = contains([256, 512, 1024, 2048, 4096], var.ecs_cpu)
    error_message = "ECS CPU must be one of: 256, 512, 1024, 2048, 4096."
  }
}

variable "ecs_memory" {
  description = "ECS task memory in MiB"
  type        = number
  default     = 1024
  
  validation {
    condition     = contains([512, 1024, 2048, 3072, 4096, 5120, 6144, 7168, 8192], var.ecs_memory)
    error_message = "ECS memory must be one of: 512, 1024, 2048, 3072, 4096, 5120, 6144, 7168, 8192."
  }
}

variable "ecs_desired_count" {
  description = "Desired number of ECS tasks"
  type        = number
  default     = 1
  
  validation {
    condition     = var.ecs_desired_count >= 1
    error_message = "ECS desired count must be at least 1."
  }
}

variable "ecs_min_count" {
  description = "Minimum number of ECS tasks for auto-scaling"
  type        = number
  default     = 1
  
  validation {
    condition     = var.ecs_min_count >= 1
    error_message = "ECS min count must be at least 1."
  }
}

variable "ecs_max_count" {
  description = "Maximum number of ECS tasks for auto-scaling"
  type        = number
  default     = 5
  
  validation {
    condition     = var.ecs_max_count >= var.ecs_min_count
    error_message = "ECS max count must be greater than or equal to min count."
  }
}

variable "certificate_arn" {
  description = "ARN of the SSL certificate for HTTPS"
  type        = string
  default     = ""
}

variable "ecr_repository_url" {
  description = "URL of the ECR repository for the backend image"
  type        = string
  default     = ""
}

variable "openai_api_key_arn" {
  description = "ARN of the OpenAI API key in Secrets Manager"
  type        = string
  default     = ""
}

# Tags
variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default = {
    Project     = "EduMate-AI"
    ManagedBy   = "Terraform"
    Environment = "dev"
  }
}
