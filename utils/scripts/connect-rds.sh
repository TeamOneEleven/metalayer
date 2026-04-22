#!/bin/bash
set -e

if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

INSTANCE_ID="${INSTANCE_ID:?INSTANCE_ID not set}"
RDS_ENDPOINT="${RDS_ENDPOINT:?RDS_ENDPOINT not set}"
LOCAL_PORT="${LOCAL_PORT:-1433}"

echo "🚀 Starting RDS connection workflow..."

cleanup() {
    echo "🛑 Stopping EC2 instance..."
    aws ec2 stop-instances --instance-ids "$INSTANCE_ID" > /dev/null
    echo "✅ Instance stopped"
}

trap cleanup EXIT

STATE=$(aws ec2 describe-instances --instance-ids "$INSTANCE_ID" \
    --query 'Reservations[0].Instances[0].State.Name' --output text)

if [ "$STATE" != "running" ]; then
    echo "⏳ Starting EC2 instance..."
    aws ec2 start-instances --instance-ids "$INSTANCE_ID" > /dev/null
    aws ec2 wait instance-running --instance-ids "$INSTANCE_ID"
    echo "⏳ Waiting for SSM agent (30s)..."
    sleep 30
else
    echo "✅ Instance already running"
fi

echo "🔌 Starting port forwarding on localhost:$LOCAL_PORT..."
echo "💡 Connect SSMS to: localhost:$LOCAL_PORT"
echo "Press Ctrl+C to disconnect and stop instance"
echo ""

aws ssm start-session --target "$INSTANCE_ID" \
    --document-name AWS-StartPortForwardingSessionToRemoteHost \
    --parameters "{\"portNumber\":[\"1433\"],\"localPortNumber\":[\"$LOCAL_PORT\"],\"host\":[\"$RDS_ENDPOINT\"]}"
