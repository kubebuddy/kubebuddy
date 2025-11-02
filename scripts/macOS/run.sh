#!/bin/bash

# Activate virtual environment
source buddyenv/bin/activate

# Default values
HOST="127.0.0.1"
PORT="8000"

# Parse named arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --host)
            # Check if the next argument exists AND doesn't start with '-' (isn't another flag)
            if [[ -n "$2" && "$2" != -* ]]; then
                HOST="$2"
                shift # Consume --host flag
                shift # Consume the value for --host
            else
                # Error if $2 is missing or looks like another flag
                echo "Error: --host requires a value." >&2
                exit 1
            fi
            ;;
        --port)
            # Check if the next argument exists AND doesn't start with '-'
            if [[ -n "$2" && "$2" != -* ]]; then
                PORT="$2"
                shift # Consume --port flag
                shift # Consume the value for --port
            else
                # Error if $2 is missing or looks like another flag
                echo "Error: --port requires a value." >&2
                exit 1
            fi
            ;;
        *)
            echo "Unknown parameter passed: $1" >&2
            exit 1
            ;;
    esac
    
done

# Run the server
python manage.py runserver "$HOST:$PORT"

