#!/bin/bash

# Set the image name
IMAGE_NAME="sebsteinig/climatearchive-api:latest"

# Directory where model data is stored
LOCAL_DATA_DIR="/home/ubuntu/model_data"

# Create a temporary docker-compose file with the correct path
cat > docker-compose.temp.yml << EOL
version: '3.8'

services:
  climate-api:
    image: ${IMAGE_NAME}
    container_name: climate-archive-api
    restart: unless-stopped
    ports:
      - "4000:4000"
    volumes:
      - ${LOCAL_DATA_DIR}:/data
    environment:
      - NETCDF_CACHE_SIZE=200
      - NETCDF_CACHE_TTL=2592000
      - API_DEBUG=false
    deploy:
      resources:
        limits:
          memory: 6G
        reservations:
          memory: 2G
      restart_policy:
        condition: any
        delay: 5s
        max_attempts: 3
        window: 120s
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:4000/health", "||", "exit", "1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
EOL

echo "Stopping any existing containers..."
sudo docker stop climate-archive-api || true
echo "Removing any existing containers..."
sudo docker rm climate-archive-api || true

echo "Pulling the latest image..."
sudo docker pull ${IMAGE_NAME}

echo "Starting the container..."
sudo docker run -d --name climate-archive-api \
  --restart unless-stopped \
  -p 4000:4000 \
  -v "${LOCAL_DATA_DIR}:/data" \
  -e NETCDF_CACHE_SIZE=200 \
  -e NETCDF_CACHE_TTL=2592000 \
  -e API_DEBUG=false \
  --memory="6g" \
  --memory-reservation="2g" \
  --health-cmd="curl -f http://localhost:4000/health || exit 1" \
  --health-interval=30s \
  --health-timeout=10s \
  --health-retries=3 \
  --health-start-period=10s \
  ${IMAGE_NAME}

echo "Cleaning up temporary files..."
rm docker-compose.temp.yml

echo "Deployment complete. Container is running in the background."
echo "To view logs: sudo docker logs -f climate-archive-api"
echo "To check container health: sudo docker inspect --format='{{.State.Health.Status}}' climate-archive-api"
echo "To see health check details: sudo docker inspect --format='{{json .State.Health}}' climate-archive-api | jq"
