#!/bin/bash
set -e

echo "Installing dependencies..."

if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    brew install sqlcmd jq
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    curl -sSL https://packages.microsoft.com/keys/microsoft.asc | sudo tee /etc/apt/trusted.gpg.d/microsoft.asc
    sudo add-apt-repository -y "$(curl -sSL https://packages.microsoft.com/config/ubuntu/22.04/prod.list)"
    sudo apt-get update
    sudo ACCEPT_EULA=Y apt-get install -y sqlcmd jq
fi

chmod +x scripts/*.sh

echo "✅ Setup complete"
