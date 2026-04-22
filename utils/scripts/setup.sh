#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Installing dependencies..."

# Use sudo only if not already root
SUDO=""
if [ "$(id -u)" -ne 0 ]; then
    SUDO="sudo"
fi

install_aws_cli_linux() {
    if command -v aws &> /dev/null; then
        echo "  aws CLI already installed ($(aws --version 2>&1))"
        return 0
    fi

    # Try the official v2 binary installer first.
    echo "  Installing AWS CLI v2..."
    local arch AWS_PKG tmpdir
    arch="$(uname -m)"
    case "$arch" in
        x86_64) AWS_PKG="awscli-exe-linux-x86_64.zip" ;;
        aarch64|arm64) AWS_PKG="awscli-exe-linux-aarch64.zip" ;;
        *) AWS_PKG="" ;;
    esac

    if [ -n "$AWS_PKG" ]; then
        tmpdir="$(mktemp -d)"
        if curl -fsSL --retry 3 --retry-delay 2 \
                "https://awscli.amazonaws.com/${AWS_PKG}" -o "$tmpdir/awscliv2.zip"; then
            unzip -q "$tmpdir/awscliv2.zip" -d "$tmpdir"
            $SUDO "$tmpdir/aws/install" --update
            rm -rf "$tmpdir"
            return 0
        fi
        rm -rf "$tmpdir"
        echo "  ⚠ AWS CLI v2 installer unreachable — falling back to pip-based v1." >&2
    fi

    # Fallback: install AWS CLI v1 via `uv tool` (works without outbound
    # access to awscli.amazonaws.com — pulls from PyPI instead).
    if command -v uv &> /dev/null; then
        uv tool install awscli
    else
        echo "  ⚠ Cannot install AWS CLI: uv not available and v2 installer unreachable." >&2
        return 1
    fi
}

if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    brew install sqlcmd jq
    if ! command -v aws &> /dev/null; then
        brew install awscli
    fi
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux

    # Base packages that ship in Ubuntu's default repos.
    need_base=()
    command -v jq    &> /dev/null || need_base+=(jq)
    command -v curl  &> /dev/null || need_base+=(curl)
    command -v unzip &> /dev/null || need_base+=(unzip)
    if [ ${#need_base[@]} -gt 0 ]; then
        $SUDO apt-get update
        $SUDO apt-get install -y "${need_base[@]}"
    fi

    # sqlcmd — pull from Microsoft's apt repo. Write the sources list
    # directly so we don't depend on add-apt-repository / python3-apt.
    # Wrapped so a failure here doesn't abort the rest of setup.
    install_sqlcmd_linux() {
        if command -v sqlcmd &> /dev/null; then
            return 0
        fi
        echo "  Installing sqlcmd..."
        UBUNTU_CODENAME_VER="$(. /etc/os-release && echo "${VERSION_ID}")"
        $SUDO install -d -m 0755 /etc/apt/keyrings
        curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
            | $SUDO gpg --dearmor -o /etc/apt/keyrings/microsoft.gpg
        $SUDO chmod a+r /etc/apt/keyrings/microsoft.gpg
        echo "deb [arch=amd64,arm64,armhf signed-by=/etc/apt/keyrings/microsoft.gpg] https://packages.microsoft.com/ubuntu/${UBUNTU_CODENAME_VER}/prod $(. /etc/os-release && echo "${VERSION_CODENAME}") main" \
            | $SUDO tee /etc/apt/sources.list.d/mssql-release.list > /dev/null
        # Only refresh the MS list so unrelated broken PPAs don't fail us.
        $SUDO apt-get update -o Dir::Etc::sourcelist="sources.list.d/mssql-release.list" \
                             -o Dir::Etc::sourceparts="-" \
                             -o APT::Get::List-Cleanup="0"
        $SUDO env ACCEPT_EULA=Y apt-get install -y sqlcmd
    }
    if ! install_sqlcmd_linux; then
        echo "  ⚠ sqlcmd install failed — continuing; queries will fail until sqlcmd is available."
    fi

    install_aws_cli_linux
fi

chmod +x "$SCRIPT_DIR"/*.sh

echo "✅ Setup complete"
