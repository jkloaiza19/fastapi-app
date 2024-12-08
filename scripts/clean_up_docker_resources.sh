#!/bin/bash
echo 'List all Docker images to identify unused ones:'
docker images -a

echo 'Remove dangling images (untagged images left over from builds):'
docker image prune -f

echo 'Remove all unused images:'
docker image prune -a -f

echo 'List all containers:'
docker ps -a

echo 'Removed stopped containers:'
docker container prune -f

echo 'List all volumes:'
docker volume ls

echo 'Remove all unused volumes:'
docker volume prune -f

echo 'Clear unused build cache:'
docker builder prune --all -f

echo 'Clean up unused Docker resources:'
docker system prune -a -f --volumes


