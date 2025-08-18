#!/bin/bash

docker compose -f devops/docker-compose/docker-compose.dev.yml down
docker compose -f devops/docker-compose/docker-compose.dev.yml up -d