#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Load environment
if [ -f "$SCRIPT_DIR/.env" ]; then
    export $(cat "$SCRIPT_DIR/.env" | grep -v '^#' | xargs)
fi

# Validate required vars
DB_NAME="${DB_NAME:?DB_NAME not set}"
SECRET_NAME="${SECRET_NAME:?SECRET_NAME not set}"
INSTANCE_ID="${INSTANCE_ID:?INSTANCE_ID not set}"
RDS_ENDPOINT="${RDS_ENDPOINT:?RDS_ENDPOINT not set}"
LOCAL_PORT="${LOCAL_PORT:-1433}"

# Parse arguments
OUTPUT_FILE=""
QUERY=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -o|--output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        *)
            QUERY="$1"
            shift
            ;;
    esac
done

if [ -z "$QUERY" ]; then
    echo "Usage: $0 <query|file.sql> [-o output.csv]" >&2
    echo "" >&2
    echo "Examples:" >&2
    echo "  $0 \"SELECT TOP 10 * FROM [User]\"" >&2
    echo "  $0 queries/my-query.sql" >&2
    echo "  $0 queries/my-query.sql -o results.csv" >&2
    exit 1
fi

# Function: Check if tunnel is active
check_tunnel() {
    nc -z localhost "$LOCAL_PORT" 2>/dev/null
}

# Function: Ensure tunnel is running
ensure_tunnel() {
    if check_tunnel; then
        echo "✅ Tunnel already active" >&2
        return 0
    fi

    echo "🔌 Starting tunnel..." >&2
    "$SCRIPT_DIR/startup.sh" >&2

    # Wait for tunnel to be ready (up to 10 attempts)
    for i in {1..10}; do
        sleep 2
        if check_tunnel; then
            return 0
        fi
    done

    echo "❌ Failed to establish tunnel" >&2
    exit 1
}

# Function: Get credentials
get_credentials() {
    CREDS=$(bash "$SCRIPT_DIR/get-db-credentials.sh")
    DB_USER=$(echo "$CREDS" | jq -r .username)
    DB_PASS=$(echo "$CREDS" | jq -r .password)
}

# Main execution
ensure_tunnel
get_credentials

# Build sqlcmd command
if [ -n "$OUTPUT_FILE" ]; then
    # CSV output mode
    if [ -f "$QUERY" ]; then
        TMPFILE=$(mktemp)
        printf "SET NOCOUNT ON;\n" > "$TMPFILE"
        cat "$QUERY" >> "$TMPFILE"
        sqlcmd -S "localhost,$LOCAL_PORT" -U "$DB_USER" -P "$DB_PASS" -d "$DB_NAME" \
            -s"," -W -h 0 -i "$TMPFILE" | grep -v "^-" | sed '/^$/d' > "$OUTPUT_FILE"
        rm -f "$TMPFILE"
    else
        sqlcmd -S "localhost,$LOCAL_PORT" -U "$DB_USER" -P "$DB_PASS" -d "$DB_NAME" \
            -s"," -W -h 0 -Q "SET NOCOUNT ON; $QUERY" | grep -v "^-" | sed '/^$/d' > "$OUTPUT_FILE"
    fi
    echo "✅ Results saved to $OUTPUT_FILE" >&2
else
    # Interactive output mode
    if [ -f "$QUERY" ]; then
        sqlcmd -S "localhost,$LOCAL_PORT" -U "$DB_USER" -P "$DB_PASS" -d "$DB_NAME" -i "$QUERY"
    else
        sqlcmd -S "localhost,$LOCAL_PORT" -U "$DB_USER" -P "$DB_PASS" -d "$DB_NAME" -Q "SET NOCOUNT ON; $QUERY"
    fi
fi
