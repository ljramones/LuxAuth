#!/usr/bin/env bash
set -euo pipefail

echo "=== Creating S3 buckets ==="
awslocal s3 mb s3://auth-platform-raw-evidence
awslocal s3 mb s3://auth-platform-normalized-evidence
awslocal s3 mb s3://auth-platform-reference-library
awslocal s3 mb s3://auth-platform-ml-artifacts

echo "=== Creating SQS queues ==="

# Create dead-letter queue first
awslocal sqs create-queue --queue-name dead-letter-queue
DLQ_ARN=$(awslocal sqs get-queue-attributes \
  --queue-url "$(awslocal sqs get-queue-url --queue-name dead-letter-queue --query QueueUrl --output text)" \
  --attribute-names QueueArn \
  --query 'Attributes.QueueArn' \
  --output text)

echo "DLQ ARN: ${DLQ_ARN}"

# Create processing queues with redrive policy
for QUEUE in image-quality-queue normalization-queue embedding-queue vector-search-queue region-scoring-queue decision-queue; do
  echo "Creating queue: ${QUEUE}"
  awslocal sqs create-queue \
    --queue-name "${QUEUE}" \
    --attributes '{"RedrivePolicy":"{\"deadLetterTargetArn\":\"'"${DLQ_ARN}"'\",\"maxReceiveCount\":\"3\"}"}'
done

echo "=== LocalStack initialization complete ==="
awslocal s3 ls
awslocal sqs list-queues
