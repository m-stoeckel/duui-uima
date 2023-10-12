#!/usr/bin/env bash
set -euo pipefail

export DUUI_SENTENCIZER_TRANKIT_MODEL_NAME="xlm-roberta-base"
export DUUI_SENTENCIZER_TRANKIT_CUDA=1

export DUUI_SENTENCIZER_TRANKIT_ANNOTATOR_NAME=duui-sentencizer-trankit
export DUUI_SENTENCIZER_TRANKIT_ANNOTATOR_VERSION=0.2

export DOCKER_REGISTRY="docker.texttechnologylab.org/"

docker build \
  --build-arg DUUI_SENTENCIZER_TRANKIT_MODEL_NAME \
  --build-arg DUUI_SENTENCIZER_TRANKIT_CUDA \
  --build-arg DUUI_SENTENCIZER_TRANKIT_ANNOTATOR_NAME \
  --build-arg DUUI_SENTENCIZER_TRANKIT_ANNOTATOR_VERSION \
  -t ${DOCKER_REGISTRY}${DUUI_SENTENCIZER_TRANKIT_ANNOTATOR_NAME}-cuda${DUUI_SENTENCIZER_TRANKIT_CUDA}:${DUUI_SENTENCIZER_TRANKIT_ANNOTATOR_VERSION} \
  -f src/main/docker/Dockerfile \
  .

docker tag \
  ${DOCKER_REGISTRY}${DUUI_SENTENCIZER_TRANKIT_ANNOTATOR_NAME}-cuda${DUUI_SENTENCIZER_TRANKIT_CUDA}:${DUUI_SENTENCIZER_TRANKIT_ANNOTATOR_VERSION} \
  ${DOCKER_REGISTRY}${DUUI_SENTENCIZER_TRANKIT_ANNOTATOR_NAME}-cuda${DUUI_SENTENCIZER_TRANKIT_CUDA}:latest