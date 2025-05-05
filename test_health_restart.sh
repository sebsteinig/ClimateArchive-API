#!/bin/bash

# Test script for health check and automatic restart functionality

echo "===== HEALTH CHECK & RESTART TEST ====="
echo "This script will test various scenarios to verify Docker's health check"
echo "and automatic restart capabilities for your ClimateArchive API."
echo ""

# Function to check container status
check_container_status() {
  STATUS=$(sudo docker ps -a --filter "name=climate-archive-api" --format "{{.Status}}" | head -n 1)
  HEALTH=$(sudo docker inspect --format='{{.State.Health.Status}}' climate-archive-api 2>/dev/null || echo "Not running")
  
  echo "Container status: $STATUS"
  echo "Health status: $HEALTH"
  echo ""
}

# Test 1: Basic health check
echo "TEST 1: Basic health check"
echo "Checking current container status..."
check_container_status

echo "Testing health endpoint directly..."
curl -s http://localhost:4000/health | jq .
echo ""

# Test 2: View detailed health check results
echo "TEST 2: View detailed health check results from Docker"
sudo docker inspect --format='{{json .State.Health}}' climate-archive-api 2>/dev/null | jq .
echo ""

# Test 3: Crash test
echo "TEST 3: Testing automatic restart after crash"
echo "Triggering intentional crash (via /test/crash endpoint)..."
echo "Before crash:"
check_container_status

echo "Sending crash request..."
curl -s http://localhost:4000/test/crash || echo "API crashed as expected"
echo ""

echo "Waiting 10 seconds for Docker to detect crash and restart container..."
sleep 10

echo "After crash and restart:"
check_container_status

echo "Testing if API is responding again..."
curl -s http://localhost:4000/health | jq . || echo "API still restarting, wait longer"
echo ""

# Test 4: Manually stop and verify restart policy
echo "TEST 4: Testing restart policy after manual kill"
echo "Killing container without stopping it properly..."
sudo docker kill climate-archive-api
echo "Container killed"

echo "Waiting 10 seconds for Docker to restart container..."
sleep 10

echo "After kill and restart:"
check_container_status

echo "Testing if API is responding again..."
curl -s http://localhost:4000/health | jq . || echo "API still restarting, wait longer"
echo ""

echo "===== TESTS COMPLETED ====="
echo "If the container restarted after each test and health status"
echo "returned to 'healthy', then your health check and restart"
echo "functionality is working correctly."
