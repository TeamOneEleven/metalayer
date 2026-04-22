#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ -f "$SCRIPT_DIR/.env" ]; then
    export $(cat "$SCRIPT_DIR/.env" | grep -v '^#' | xargs)
fi

# AWS CLI v1 (pip) only reads AWS_DEFAULT_REGION; v2 reads either.
# Normalize so both work.
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-$AWS_REGION}"

INSTANCE_ID="${INSTANCE_ID:?INSTANCE_ID not set}"
RDS_ENDPOINT="${RDS_ENDPOINT:?RDS_ENDPOINT not set}"

echo "🚀 Starting EC2 instance..."
aws ec2 start-instances --instance-ids "$INSTANCE_ID" > /dev/null
aws ec2 wait instance-running --instance-ids "$INSTANCE_ID"
echo "⏳ Waiting for SSM agent..."
sleep 30

echo "🔌 Starting port forwarding..."
nohup aws ssm start-session --target "$INSTANCE_ID" \
    --document-name AWS-StartPortForwardingSessionToRemoteHost \
    --parameters "{\"portNumber\":[\"1433\"],\"localPortNumber\":[\"${LOCAL_PORT:-1433}\"],\"host\":[\"$RDS_ENDPOINT\"]}" \
    > tunnel.log 2>&1 &

echo $! > tunnel.pid
echo "✅ Tunnel active on localhost:${LOCAL_PORT:-1433}"
