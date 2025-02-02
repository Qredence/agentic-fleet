#!/bin/bash
set -e

# Get version from pyproject.toml (more precise extraction)
VERSION=$(grep '^version = ' pyproject.toml | cut -d'"' -f2 | tr -d '\n')
IMAGE_NAME="qredence/agenticfleet"

echo "Building AgenticFleet Docker image"
echo "Version: ${VERSION}"
echo "Image: ${IMAGE_NAME}"

# Build the Docker image
docker build \
    -f .devcontainer/Dockerfile \
    --build-arg VERSION="${VERSION}" \
    --build-arg BUILDKIT_INLINE_CACHE=1 \
    -t "${IMAGE_NAME}:${VERSION}" \
    -t "${IMAGE_NAME}:latest" \
    .

# If --push flag is provided, push the images to Docker Hub
if [ "$1" = "--push" ]; then
    echo "Pushing images to Docker Hub..."
    docker push "${IMAGE_NAME}:${VERSION}"
    docker push "${IMAGE_NAME}:latest"
fi

echo "Build complete!"