#!/bin/bash

echo "Installing KubeBuddy: AI Powered Kubernetes Dashboard"

echo "Creating Virtual Environment..."

python3 -m venv buddyenv

source ./buddyenv/bin/activate

echo "Installing dependencies..."

pip install -r requirements.txt

echo "Installation complete!"

echo "Setting up project"

python3 manage.py makemigrations main

echo "Creating Database"

python3 manage.py migrate

echo "-----------------------------------------------------------------------------------------------"
echo "KubeBuddy is ready to go! Run the following command to start the server:"
echo "bash run.sh --port <port_number> --host <host_address>"
echo "Both --host and --port are optional. Defaults are host=127.0.0.1 and port=8000."
echo "Example: bash run.sh --port 8080 --host 0.0.0.0"
