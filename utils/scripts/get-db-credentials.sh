#!/bin/bash
set -e

SECRET_NAME="${SECRET_NAME:?SECRET_NAME not set}"
AWS_REGION="${AWS_REGION:-us-east-1}"

aws secretsmanager get-secret-value \
    --secret-id "$SECRET_NAME" \
    --region "$AWS_REGION" \
    --query SecretString \
    --output text
