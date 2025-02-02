#!/bin/bash
set -e

# Get version from pyproject.toml
VERSION=$(grep '^version = ' pyproject.toml | cut -d'"' -f2 | tr -d '\n')
IMAGE_NAME="qredenceai/agenticfleet"  # Updated Docker Hub username
BRANCH=$(git rev-parse --abbrev-ref HEAD)

echo "Building AgenticFleet Docker image"
echo "Version: ${VERSION}"
echo "Branch: ${BRANCH}"
echo "Image: ${IMAGE_NAME}"

# Set tags based on branch
if [ "$BRANCH" = "main" ]; then
    TAGS="-t ${IMAGE_NAME}:${VERSION} -t ${IMAGE_NAME}:latest"
else
    TAGS="-t ${IMAGE_NAME}:${VERSION}-dev -t ${IMAGE_NAME}:dev"
fi

# Build the Docker image
docker build \
    -f .devcontainer/Dockerfile \
    --build-arg VERSION="${VERSION}" \
    --build-arg BUILDKIT_INLINE_CACHE=1 \
    ${TAGS} \
    .

# If --push flag is provided, push the images to Docker Hub
if [ "$1" = "--push" ]; then
    echo "Pushing images to Docker Hub..."
    if [ "$BRANCH" = "main" ]; then
        docker push "${IMAGE_NAME}:${VERSION}"
        docker push "${IMAGE_NAME}:latest"
    else
        docker push "${IMAGE_NAME}:${VERSION}-dev"
        docker push "${IMAGE_NAME}:dev"
    fi
fi

echo "Build complete!"