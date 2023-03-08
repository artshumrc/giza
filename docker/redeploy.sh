#!/bin/bash

# This script is used to redeploy the docker container
# It is called by the webhook server; see webhooks/readme.md for more info on the deploy strategy

# This gets logged in /var/log/webhook/giza-deploy/giza-deploy.sh to mark the start of the script
# timestamps already provided by webhook
echo "################ Redeploying giza app ################"
echo $payload
echo ${entire-payload}

DOCKER_REGISTRY="407196791491.dkr.ecr.us-east-1.amazonaws.com"
DEPLOY_ENV="Dockerized Giza Dev"
DEPLOY_STATUS="Success"
REPO_PATH="/home/giza/giza-dockerized/giza/"
# COMMIT_SHA= TODO get the commit sha from the webhook payload

echo "Pulling latest docker images"
AWS_PROFILE=fasrc_cd aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $DOCKER_REGISTRY

docker pull $DOCKER_REGISTRY/giza/django:latest
docker pull $DOCKER_REGISTRY/giza/ingest:latest

echo  "Pulling latest code from git"
git pull

echo "Stopping old containers and running new ones"
docker compose -f docker-compose.yml -f docker-compose-production.yml run --rm django python3 manage.py migrate
docker compose stop
docker compose -f docker-compose.yml -f docker-compose-production.yml up -d

DOCKER_STATUS=$(docker ps -a)

echo "Sending confirmation to Slack"
# TODO pull status based on DOCKER_STATUS
# TODO bash try/catch, run regardless of whether the rest of this script succeeds
# --webhook is relying on SLACK_WEBHOOK being set in .env
python3 slack_status.py --deploy_status "$DEPLOY_STATUS" --deploy_env "$DEPLOY_ENV" \
    --docker_status "$DOCKER_STATUS" --repo_path "$REPO_PATH"

echo "################ Finished redeploying giza app ################"