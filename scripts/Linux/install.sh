#!/bin/bash

set -e  # Exit immediately if a command exits with a non-zero status

echo "Installing KubeBuddy: AI Powered Kubernetes Dashboard"

# Function to print error and exit
function error_exit {
  echo "Error: $1"
  exit 1
}

# Find latest installed python3 version >= 3.10
PYTHON_BIN=$(compgen -c | grep -E '^python3\.[0-9]+$' | sort -V | tail -n1)

if [[ -z "$PYTHON_BIN" ]]; then
  error_exit "No suitable Python3 version found. Please install Python 3.10 or newer."
fi

PYTHON_VERSION=$($PYTHON_BIN -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.10"

if [[ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]]; then
  error_exit "Python version must be >= 3.10. Found version: $PYTHON_VERSION"
fi

echo "Using Python binary: $PYTHON_BIN (version $PYTHON_VERSION)"

# Check pip
if ! command -v pip &> /dev/null; then
  error_exit "pip is not installed. Please install pip before proceeding."
fi

# Check venv module
if ! $PYTHON_BIN -m venv --help &> /dev/null; then
  error_exit "venv module is not available. Please ensure Python was installed with venv support."
fi

echo "All dependencies are satisfied!"
echo "--------------------------------"

echo "Creating Virtual Environment..."
$PYTHON_BIN -m venv buddyenv

source ./buddyenv/bin/activate

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Installation complete!"

echo "Setting up project..."
python manage.py makemigrations main

echo "Creating Database..."
python manage.py migrate

# K8sGPT installation
read -p "Do you want to install K8sGPT (Enter "yes" to confirm) ? " -r

if [[ $REPLY =~ ^[Yy][Ee]?[Ss]?$ ]]
then
  echo "Installing K8sGPT..."
	if command -v dpkg &> /dev/null; then
      curl -LO https://github.com/k8sgpt-ai/k8sgpt/releases/download/v0.4.17/k8sgpt_amd64.deb
      dpkg -i k8sgpt_amd64.deb
      echo "K8sGPT installed successfully."
  elif command -v rpm &> /dev/null; then
      rpm -ivh https://github.com/k8sgpt-ai/k8sgpt/releases/download/v0.4.17/k8sgpt_amd64.rpm
      echo "K8sGPT installed successfully."
  elif command -v apk &> /dev/null; then
      wget https://github.com/k8sgpt-ai/k8sgpt/releases/download/v0.4.17/k8sgpt_amd64.apk
      apk add --allow-untrusted k8sgpt_amd64.apk
      echo "K8sGPT installed successfully."
  else
      echo "Unknown or unsupported Linux distro. Please install K8sGPT manually."
  fi
else
	echo
fi

echo "-----------------------------------------------------------------------------------------------"
echo "KubeBuddy is ready to go! Run the following command to start the server:"
echo "bash run.sh --port <port_number> --host <host_address>"
echo "Both --host and --port are optional. Defaults are host=127.0.0.1 and port=8000."
echo "Example: bash run.sh --port 8080 --host 0.0.0.0"
