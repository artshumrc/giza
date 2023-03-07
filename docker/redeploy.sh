#!/bin/bash

# This script is used to redeploy the docker container
# It is called by the webhook server; see webhooks/readme.md for more info on the deploy strategy

# This gets logged in /var/log/webhook/giza-deploy/giza-deploy.sh to mark the start of the script
# timestamps already provided by webhook
echo "################ Redeploying giza app ################"

# See entire payload so we can differentiate between different events, e.g. push vs Github Actions
echo $payload

echo "Pulling latest docker images"
DOCKER_REGISTRY="407196791491.dkr.ecr.us-east-1.amazonaws.com"
AWS_PROFILE=fasrc_cd aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $DOCKER_REGISTRY

docker pull $DOCKER_REGISTRY/giza/django:latest
docker pull $DOCKER_REGISTRY/giza/ingest:latest

echo  "Pulling latest code from git"
git pull

echo "Stopping old containers and running new ones"
docker compose -f docker-compose.yml -f docker-compose-production.yml run --rm django python3 manage.py migrate
docker compose stop
docker compose -f docker-compose.yml -f docker-compose-production.yml up -d

echo "################ Finished redeploying giza app ################"