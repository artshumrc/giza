#!/bin/bash

# This script is used to redeploy the docker container
echo "Updating Giza app"

DOCKER_REGISTRY="407196791491.dkr.ecr.us-east-1.amazonaws.com"
aws ecr get-login-password | docker login --username AWS --password-stdin $DOCKER_REGISTRY

docker pull $DOCKER_REGISTRY/giza/django:latest
docker pull $DOCKER_REGISTRY/giza/ingest:latest

git pull

docker compose -f docker-compose.yml -f docker-compose-production.yml run --rm django python3 manage.py migrate 
docker compose -f docker-compose.yml -f docker-compose-production.yml up -d