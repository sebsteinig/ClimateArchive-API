#!/bin/bash

# API Monitor Script
# This script checks the health of the Climate Archive API and restarts it if needed

LOG_FILE="/home/ubuntu/api_monitor.log"
DEPLOY_SCRIPT="/home/ubuntu/scripts/deploy_api.sh"
API_URL="http://localhost:4000/health"
MAX_RETRIES=3

# Function to log messages
log_message() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Ensure the log file is writable
touch "$LOG_FILE" 2>/dev/null || {
  # If we can't write to the specified log file, use /tmp
  LOG_FILE="/tmp/api_monitor.log"
  touch "$LOG_FILE"
  log_message "WARNING: Using alternative log file at $LOG_FILE"
}

# Initialize log for this run
log_message "API health check started"

# Check if we're running as root/sudo
if [ "$(id -u)" -ne 0 ]; then
  log_message "Notice: Script not running as root. Docker commands may require sudo."
fi

# Check if API is responding
for i in $(seq 1 $MAX_RETRIES); do
  response=$(curl -s -o /dev/null -w "%{http_code}" $API_URL)
  
  if [[ $response == "200" ]]; then
    log_message "API health check successful (HTTP $response)"
    exit 0
  else
    log_message "Attempt $i: API health check failed (HTTP $response)"
    sleep 5
  fi
done

# If we get here, the API is not responding after multiple attempts
log_message "API is not responding after $MAX_RETRIES attempts. Running deployment script..."

# Run the deployment script - use sudo if we're not already root
if [ "$(id -u)" -ne 0 ]; then
  log_message "Running deployment script with sudo"
  sudo bash "$DEPLOY_SCRIPT" >> "$LOG_FILE" 2>&1
else
  log_message "Running deployment script"
  bash "$DEPLOY_SCRIPT" >> "$LOG_FILE" 2>&1
fi

# Check if deployment was successful
sleep 30
final_check=$(curl -s -o /dev/null -w "%{http_code}" $API_URL)
if [[ $final_check == "200" ]]; then
  log_message "API successfully restarted (HTTP $final_check)"
else
  log_message "WARNING: API still not responding after restart (HTTP $final_check)"
fi
