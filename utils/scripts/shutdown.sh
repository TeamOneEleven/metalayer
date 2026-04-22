#!/bin/bash

if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

if [ -f tunnel.pid ]; then
    echo "🛑 Stopping tunnel..."
    kill $(cat tunnel.pid) 2>/dev/null || true
    rm tunnel.pid
fi

if [ -n "$INSTANCE_ID" ]; then
    echo "🛑 Stopping EC2 instance..."
    aws ec2 stop-instances --instance-ids "$INSTANCE_ID" > /dev/null
    echo "✅ Instance stopped"
fi
