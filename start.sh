#!/bin/bash

# pull down docker image
docker pull joshand/spark-operations-bot

# make sure docker image is not already running
docker-compose down

# start docker image
docker-compose up