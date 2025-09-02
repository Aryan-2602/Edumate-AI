# EduMate-AI Deployment Guide

This guide will walk you through deploying the complete EduMate-AI platform, including the backend API, frontend application, and all supporting infrastructure.

## 🏗️ Architecture Overview

The platform consists of:
- **Frontend**: Next.js application deployed on Vercel
- **Backend**: FastAPI application deployed on AWS ECS Fargate
- **Database**: PostgreSQL on AWS RDS
- **Storage**: AWS S3 for document storage
- **Vector Database**: Chroma running alongside the backend
- **AI/LLM**: OpenAI GPT-4 via API
- **Authentication**: Firebase Authentication
- **Monitoring**: Sentry, Weights & Biases, CloudWatch

## 📋 Prerequisites

Before starting deployment, ensure you have:

- [ ] AWS CLI configured with appropriate permissions
- [ ] Terraform installed (v1.0+)
- [ ] Docker installed and running
- [ ] Node.js 18+ and npm
- [ ] Python 3.11+
- [ ] Firebase project created
- [ ] OpenAI API key
- [ ] GitHub repository with access to secrets
- [ ] Vercel account and project

## 🚀 Deployment Steps

### 1. Environment Setup

#### 1.1 Clone and Setup Repository
```bash
git clone <your-repo-url>
cd EduMate-AI
```

#### 1.2 Create Environment Files

**Backend (.env)**
```bash
cd backend
cp .env.example .env
# Edit .env with your values
```

**Frontend (.env.local)**
```bash
cd frontend
cp .env.example .env.local
# Edit .env.local with your values
```

### 2. Firebase Configuration

#### 2.1 Create Firebase Project
1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Create a new project
3. Enable Authentication with Google provider
4. Download service account key

#### 2.2 Configure Firebase in Frontend
```bash
# In frontend/.env.local
NEXT_PUBLIC_FIREBASE_API_KEY=your_api_key
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=your_project.firebaseapp.com
NEXT_PUBLIC_FIREBASE_PROJECT_ID=your_project_id
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=your_project.appspot.com
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=your_sender_id
NEXT_PUBLIC_FIREBASE_APP_ID=your_app_id
```

### 3. AWS Infrastructure Deployment

#### 3.1 Configure AWS CLI
```bash
aws configure
# Enter your AWS Access Key ID, Secret Access Key, and region
```

#### 3.2 Create S3 Bucket for Terraform State
```bash
aws s3 mb s3://edumate-ai-terraform-state
aws s3api put-bucket-versioning \
  --bucket edumate-ai-terraform-state \
  --versioning-configuration Status=Enabled
```

#### 3.3 Store OpenAI API Key in Secrets Manager
```bash
aws secretsmanager create-secret \
  --name "openai-api-key" \
  --description "OpenAI API Key for EduMate-AI" \
  --secret-string "your-openai-api-key-here"
```

#### 3.4 Deploy Infrastructure with Terraform
```bash
cd infrastructure/terraform

# Copy and edit variables
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values

# Initialize Terraform
terraform init

# Plan deployment
terraform plan

# Deploy infrastructure
terraform apply
```

#### 3.5 Note Infrastructure Outputs
After successful deployment, note the outputs:
- ALB DNS name
- RDS endpoint
- S3 bucket name
- ECS cluster name

### 4. Backend Deployment

#### 4.1 Build and Test Locally
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest

# Test locally
uvicorn app.main:app --reload
```

#### 4.2 Build Docker Image
```bash
# Build image
docker build -t edumate-ai-backend .

# Test locally
docker run -p 8000:8000 edumate-ai-backend
```

#### 4.3 Push to ECR
```bash
# Get ECR login token
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <your-account-id>.dkr.ecr.us-east-1.amazonaws.com

# Tag image
docker tag edumate-ai-backend:latest <your-account-id>.dkr.ecr.us-east-1.amazonaws.com/edumate-ai-backend:latest

# Push image
docker push <your-account-id>.dkr.ecr.us-east-1.amazonaws.com/edumate-ai-backend:latest
```

### 5. Frontend Deployment

#### 5.1 Configure Environment Variables
```bash
cd frontend

# In .env.local, add backend API URL
NEXT_PUBLIC_API_URL=https://<your-alb-dns-name>
```

#### 5.2 Test Locally
```bash
# Install dependencies
npm install

# Run tests
npm test

# Start development server
npm run dev
```

#### 5.3 Deploy to Vercel
```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel --prod
```

### 6. CI/CD Pipeline Setup

#### 6.1 Configure GitHub Secrets
Go to your GitHub repository → Settings → Secrets and variables → Actions, and add:

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`
- `VERCEL_TOKEN`
- `VERCEL_ORG_ID`
- `VERCEL_PROJECT_ID`

#### 6.2 Push to Main Branch
The CI/CD pipeline will automatically:
- Run tests
- Build Docker images
- Deploy to AWS ECS
- Deploy frontend to Vercel

### 7. Post-Deployment Configuration

#### 7.1 Update DNS (Optional)
If you have a custom domain:
1. Create Route 53 hosted zone
2. Update ALB listener with SSL certificate
3. Configure domain in Vercel

#### 7.2 Configure Monitoring
1. **Sentry**: Add DSN to backend environment
2. **Weights & Biases**: Add API key to backend environment
3. **CloudWatch**: Already configured via Terraform

#### 7.3 Test Endpoints
```bash
# Health check
curl https://<your-alb-dns-name>/health

# API docs
curl https://<your-alb-dns-name>/docs
```

## 🔧 Configuration Details

### Backend Environment Variables
```bash
# Required
OPENAI_API_KEY=your_openai_api_key
DATABASE_URL=postgresql://user:pass@host:5432/db

# Optional
SENTRY_DSN=your_sentry_dsn
WANDB_API_KEY=your_wandb_api_key
AWS_S3_BUCKET=your_s3_bucket_name
```

### Frontend Environment Variables
```bash
# Required
NEXT_PUBLIC_FIREBASE_API_KEY=your_firebase_api_key
NEXT_PUBLIC_API_URL=https://your-backend-url

# Optional
NEXT_PUBLIC_GA_ID=your_google_analytics_id
```

## 🧪 Testing

### Backend Testing
```bash
cd backend
pytest --cov=app --cov-report=html
```

### Frontend Testing
```bash
cd frontend
npm test -- --coverage
```

### Integration Testing
```bash
# Test API endpoints
curl -X POST https://your-api-url/api/v1/ai/ask \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-token" \
  -d '{"question": "What is machine learning?"}'
```

## 📊 Monitoring and Maintenance

### Health Checks
- Backend: `/health` endpoint
- Frontend: Vercel health monitoring
- Database: RDS monitoring
- Load Balancer: ALB health checks

### Logs
- Backend: CloudWatch logs
- Frontend: Vercel logs
- Infrastructure: CloudTrail

### Scaling
- ECS auto-scaling based on CPU utilization
- Manual scaling via AWS console or CLI

## 🚨 Troubleshooting

### Common Issues

#### Backend Won't Start
1. Check environment variables
2. Verify database connectivity
3. Check CloudWatch logs
4. Verify ECS task definition

#### Frontend Build Fails
1. Check Node.js version
2. Verify environment variables
3. Check for TypeScript errors
4. Verify dependencies

#### Infrastructure Deployment Fails
1. Check AWS credentials
2. Verify S3 bucket exists
3. Check IAM permissions
4. Review Terraform logs

### Debug Commands
```bash
# Check ECS service status
aws ecs describe-services --cluster edumate-ai-cluster --services edumate-ai-backend

# Check CloudWatch logs
aws logs describe-log-streams --log-group-name /ecs/edumate-ai-backend

# Check RDS status
aws rds describe-db-instances --db-instance-identifier edumate-ai-dev
```

## 🔒 Security Considerations

### Secrets Management
- Use AWS Secrets Manager for sensitive data
- Never commit secrets to version control
- Rotate API keys regularly

### Network Security
- VPC with private subnets for backend
- Security groups with minimal required access
- HTTPS enforcement via ALB

### Data Protection
- S3 bucket encryption enabled
- RDS encryption enabled
- VPC flow logs enabled

## 📈 Scaling Considerations

### Performance
- Monitor ECS CPU and memory usage
- Adjust task definition resources as needed
- Use CloudWatch alarms for proactive scaling

### Cost Optimization
- Use Spot instances for non-critical workloads
- Monitor RDS instance size
- Set up billing alerts

## 🔄 Updates and Maintenance

### Backend Updates
1. Update code and test locally
2. Build new Docker image
3. Push to ECR
4. Update ECS service

### Frontend Updates
1. Update code and test locally
2. Push to main branch
3. Vercel auto-deploys

### Infrastructure Updates
1. Update Terraform configuration
2. Run `terraform plan`
3. Run `terraform apply`

## 📞 Support

For deployment issues:
1. Check CloudWatch logs
2. Review GitHub Actions logs
3. Check Vercel deployment logs
4. Review Terraform outputs

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Next.js Documentation](https://nextjs.org/docs)
- [AWS ECS Documentation](https://docs.aws.amazon.com/ecs/)
- [Terraform Documentation](https://www.terraform.io/docs)
- [Vercel Documentation](https://vercel.com/docs)
