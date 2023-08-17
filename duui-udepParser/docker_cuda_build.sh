export TEXTIMAGER_DIAPARSER_BATCH_SIZE=8192
export TEXTIMAGER_UDEPPARSER_ANNOTATOR_NAME=udepparser_cuda_$TEXTIMAGER_DIAPARSER_BATCH_SIZE
export TEXTIMAGER_UDEPPARSER_ANNOTATOR_VERSION=0.0.1
export TEXTIMAGER_UDEPPARSER_LOG_LEVEL=INFO
export TEXTIMAGER_UDEPPARSER_PARSER_MODEL_NAME=de_hdt.dbmdz-bert-base

docker build \
  --build-arg TEXTIMAGER_UDEPPARSER_ANNOTATOR_NAME \
  --build-arg TEXTIMAGER_UDEPPARSER_ANNOTATOR_VERSION \
  --build-arg TEXTIMAGER_UDEPPARSER_LOG_LEVEL \
  --build-arg TEXTIMAGER_UDEPPARSER_BATCH_SIZE \
  -t ${TEXTIMAGER_UDEPPARSER_ANNOTATOR_NAME}:${TEXTIMAGER_UDEPPARSER_ANNOTATOR_VERSION} \
  -f src/main/docker/Dockerfile_cuda \
  .