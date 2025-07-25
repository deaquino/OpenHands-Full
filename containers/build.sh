#!/usr/bin/env bash
set -eo pipefail


# Initialize variables with default values
image_name=""
dockerhub_user=""
push=0
load=0
tag_suffix=""
dry_run=0

# Function to display usage information
usage() {
    echo "Usage: $0 -i <image_name> [-u <dockerhub_user>] [--push] [--load] [-t <tag_suffix>] [--dry]"
    echo "  -i: Image name (required)"
    echo "  -u: Docker Hub username (required for push)"
    echo "  --push: Push the image to Docker Hub"
    echo "  --load: Load the image locally"
    echo "  -t: Tag suffix"
    echo "  --dry: Don't build, only create build-args.json"
    exit 1
}

# Parse command-line options
# Parse command-line options
while [[ $# -gt 0 ]]; do
    case $1 in
        -i) image_name="$2"; shift 2 ;;
        -u) dockerhub_user="$2"; shift 2 ;;
        --push) push=1; shift ;;
        --load) load=1; shift ;;
        -t) tag_suffix="$2"; shift 2 ;;
        --dry) dry_run=1; shift ;;
        *) usage ;;
    esac
done

# Check if required arguments are provided
if [[ -z "$image_name" ]]; then
    echo "Error: Image name is required."
    usage
fi

# If push is requested, dockerhub_user is required
if [[ $push -eq 1 && -z "$dockerhub_user" ]]; then
    echo "Error: Docker Hub username is required when pushing."
    usage
fi


echo "Building: $image_name"
tags=()

OPENHANDS_BUILD_VERSION="dev"

cache_tag_base="buildcache"
cache_tag="$cache_tag_base"


if [[ -n $RELEVANT_SHA ]]; then
  git_hash=$(git rev-parse --short "$RELEVANT_SHA")
  tags+=("$git_hash")
  tags+=("$RELEVANT_SHA")
fi

# Ensure at least one tag is generated before pushing
if [[ $push -eq 1 && ${#tags[@]} -eq 0 ]]; then
  echo "No tags generated from git or ref info. Using default tag: latest"
  tags+=("latest")
fi

if [[ -n $GITHUB_REF_NAME ]]; then
  # check if ref name is a version number
  if [[ $GITHUB_REF_NAME =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    major_version=$(echo "$GITHUB_REF_NAME" | cut -d. -f1)
    minor_version=$(echo "$GITHUB_REF_NAME" | cut -d. -f1,2)
    tags+=("$major_version" "$minor_version")
    tags+=("latest")
  fi
  sanitized_ref_name=$(echo "$GITHUB_REF_NAME" | sed 's/[^a-zA-Z0-9.-]\+/-/g')
  OPENHANDS_BUILD_VERSION=$sanitized_ref_name
  sanitized_ref_name=$(echo "$sanitized_ref_name" | tr '[:upper:]' '[:lower:]') # lower case is required in tagging
  tags+=("$sanitized_ref_name")
  cache_tag+="-${sanitized_ref_name}"
fi

if [[ -n $tag_suffix ]]; then
  cache_tag+="-${tag_suffix}"
  for i in "${!tags[@]}"; do
    tags[$i]="${tags[$i]}-$tag_suffix"
  done
fi

echo "Tags: ${tags[@]}"

if [[ "$image_name" == "openhands" ]]; then
  dir="./containers/app"
elif [[ "$image_name" == "runtime" ]]; then
  dir="./containers/runtime"
else
  dir="./containers/$image_name"
fi

if [[ (! -f "$dir/Dockerfile") && "$image_name" != "runtime" ]]; then
  # Allow runtime to be built without a Dockerfile
  echo "No Dockerfile found"
  exit 1
fi
if [[ ! -f "$dir/config.sh" ]]; then
  echo "No config.sh found for Dockerfile"
  exit 1
fi

source "$dir/config.sh"


# Set Docker Hub as the default registry
DOCKER_REGISTRY="docker.io"
if [[ -n "$dockerhub_user" ]]; then
  DOCKER_ORG="$dockerhub_user"
fi

# If $DOCKER_IMAGE_SOURCE_TAG is set, add it to the tags
if [[ -n "$DOCKER_IMAGE_SOURCE_TAG" ]]; then
  tags+=("$DOCKER_IMAGE_SOURCE_TAG")
fi
# If $DOCKER_IMAGE_TAG is set, add it to the tags
if [[ -n "$DOCKER_IMAGE_TAG" ]]; then
  tags+=("$DOCKER_IMAGE_TAG")
fi


# Compose Docker Hub repository path
DOCKER_REPOSITORY="$DOCKER_REGISTRY/$DOCKER_ORG/$DOCKER_IMAGE"
DOCKER_REPOSITORY=${DOCKER_REPOSITORY,,} # lowercase
echo "Repo: $DOCKER_REPOSITORY"
echo "Base dir: $DOCKER_BASE_DIR"

args=""
full_tags=()
for tag in "${tags[@]}"; do
  args+=" -t $DOCKER_REPOSITORY:$tag"
  full_tags+=("$DOCKER_REPOSITORY:$tag")
done


if [[ $push -eq 1 ]]; then
  args+=" --push"
  args+=" --cache-to=type=registry,ref=$DOCKER_REPOSITORY:$cache_tag,mode=max"
fi

if [[ $load -eq 1 ]]; then
  args+=" --load"
fi

echo "Args: $args"

# Modify the platform selection based on --load flag
if [[ $load -eq 1 ]]; then
  # When loading, build only for the current platform
  platform=$(docker version -f '{{.Server.Os}}/{{.Server.Arch}}')
else
  # For push or without load, build for multiple platforms
  platform="linux/amd64,linux/arm64"
fi
if [[ $dry_run -eq 1 ]]; then
  echo "Dry Run is enabled. Writing build config to docker-build-dry.json"
  jq -n \
    --argjson tags "$(printf '%s\n' "${full_tags[@]}" | jq -R . | jq -s .)" \
    --arg platform "$platform" \
    --arg openhands_build_version "$OPENHANDS_BUILD_VERSION" \
    --arg dockerfile "$dir/Dockerfile" \
    '{
      tags: $tags,
      platform: $platform,
      build_args: [
        "OPENHANDS_BUILD_VERSION=" + $openhands_build_version
      ],
      dockerfile: $dockerfile
    }' > docker-build-dry.json

    exit 0
fi



echo "Building for platform(s): $platform"

docker buildx build \
  $args \
  --build-arg OPENHANDS_BUILD_VERSION="$OPENHANDS_BUILD_VERSION" \
  --cache-from=type=registry,ref=$DOCKER_REPOSITORY:$cache_tag \
  --cache-from=type=registry,ref=$DOCKER_REPOSITORY:$cache_tag_base-main \
  --platform $platform \
  --provenance=false \
  -f "$dir/Dockerfile" \
  "$DOCKER_BASE_DIR"

# If load was requested, print the loaded images
if [[ $load -eq 1 ]]; then
  echo "Local images built:"
  docker images "$DOCKER_REPOSITORY" --format "{{.Repository}}:{{.Tag}}"
fi
