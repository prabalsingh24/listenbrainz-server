#!/bin/bash

HOSTNAME=$(hostname -s)
CONTAINER_NAME=listenbrainz-rmq-snooper-beta
DEPLOY_ENV=beta
PRIVATE_SUBNET=10.2.2
PRIVATE_IP=$(ip -4 route get $PRIVATE_SUBNET|awk '{print $NF;exit}')

docker run \
    -it \
    --rm \
    --hostname $HOSTNAME \
    --env DEPLOY_ENV=$DEPLOY_ENV \
    --name $CONTAINER_NAME \
    --env CONTAINER_NAME=$CONTAINER_NAME \
    --env PRIVATE_IP="$PRIVATE_IP" \
    --dns $PRIVATE_IP \
    --env CONSUL_HOST=$PRIVATE_IP \
    metabrainz/listenbrainz:rmq_snooper
