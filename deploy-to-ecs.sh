#!/bin/bash
# Script to build and push ein-simplifier image to ECR for ECS deployment

set -e

# Configuration
AWS_REGION="us-east-2"
AWS_ACCOUNT_ID="043229137585"
ECR_REPO="artixan-ein-simplifier"
IMAGE_NAME="ein-simplifier"
IMAGE_TAG="latest"

# Full ECR image URI
ECR_IMAGE="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO}:${IMAGE_TAG}"

echo "Building Docker image for ECS (linux/amd64)..."
docker build --platform linux/amd64 -t ${IMAGE_NAME}:${IMAGE_TAG} .

echo ""
echo "Logging into ECR..."
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

echo ""
echo "Tagging image for ECR..."
docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${ECR_IMAGE}

echo ""
echo "Pushing image to ECR..."
docker push ${ECR_IMAGE}

echo ""
echo "✓ Image pushed successfully!"
echo ""
echo "Image URI: ${ECR_IMAGE}"
echo ""
echo "Next steps:"
echo "1. Update your ECS task definition to use this image"
echo "2. Create a new task definition revision:"
echo "   aws ecs register-task-definition --cli-input-json file://task-definition.json --region ${AWS_REGION}"
echo "3. Update your service to use the new task definition"
echo "   aws ecs update-service --cluster <cluster-name> --service <service-name> --task-definition <new-task-def> --region ${AWS_REGION}"

