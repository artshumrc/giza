#!/bin/bash

# This script is used to redeploy the docker container
# It is called by the webhook server
### Usage steps
# 1. Install go and webhook server - https://github.com/adnanh/webhook. May get installed at ~/go/bin/webhook
# 2. Create or copy hooks file at ~/hooks.json
# 3. Make sure this file is executable
# 4. Run webhook server with the following command: `webhook -hooks ~/hooks.json -logfile /var/log/webhook/giza-deploy/giza-deploy.log -verbose`

now=$(date +"%Y-%m-%d_%H-%M-%S")
echo "Updating Giza app - $now"

DOCKER_REGISTRY="407196791491.dkr.ecr.us-east-1.amazonaws.com"
AWS_PROFILE=fasrc_cd aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $DOCKER_REGISTRY

docker pull $DOCKER_REGISTRY/giza/django:latest
docker pull $DOCKER_REGISTRY/giza/ingest:latest

git pull

docker compose -f docker-compose.yml -f docker-compose-production.yml run --rm django python3 manage.py migrate 
docker compose -f docker-compose.yml -f docker-compose-production.yml up -d