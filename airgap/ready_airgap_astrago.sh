#!/bin/sh

# Define variables
CURRENT_DIR=$(dirname "$(realpath "$0")")
IMAGE_LIST_FILE_NAME="images.list"
IMAGES_FROM_FILE="$CURRENT_DIR/temp/$IMAGE_LIST_FILE_NAME"
REGISTRY_PORT=25000
REGISTRY_NAME=ready-registry
runtime=docker
RETRY_COUNT=3


export NO_HTTP_SERVER=no

# Function to add images from helm charts to the images list
add_helm_images() {
  local chart_path=$1
  echo "Processing images from chart: $chart_path"
  helm images get "$chart_path" >> "$IMAGE_LIST_FILE_NAME"
}

# Function to process Helm charts and prepare the images list
prepare_images_list() {
  cp $IMAGES_FROM_FILE .

  # List of helm chart paths
  local helm_charts=(
    "$CURRENT_DIR/../applications/csi-driver-nfs/csi-driver-nfs"
    "$CURRENT_DIR/../applications/gpu-operator/custom-gpu-operator"
    "$CURRENT_DIR/../applications/prometheus/kube-prometheus-stack"
    "$CURRENT_DIR/../applications/keycloak/keycloak"
    "$CURRENT_DIR/../applications/astrago/astrago"
  )

  # Loop through the helm charts and add images to the list
  for chart in "${helm_charts[@]}"; do
    add_helm_images "$chart"
  done
}

# Function to download and register images to local registry
download_images() {
  echo "========== Download Images  =========="

  set +e
  sudo docker container inspect registry >/dev/null 2>&1
  if [ $? -ne 0 ]; then
      sudo docker run --restart=always -d -p "${REGISTRY_PORT}":"5000" -v $CURRENT_DIR/registry:/var/lib/registry --name $REGISTRY_NAME registry:latest
  fi
  set -e

  DESTINATION_REGISTRY="localhost:${REGISTRY_PORT}"

  while read -r image; do
    image_without_tag="${image%:*}"
    tag="${image##*:}"
    repository="${image_without_tag%/*}"
    new_repository="${DESTINATION_REGISTRY}/${image_without_tag#*/}"
    new_image="${new_repository}:${tag}"
    echo $new_image

    # Retry logic for pulling images
    for i in $(seq 1 $RETRY_COUNT); do
      sudo ${runtime} pull ${image} && break || {
        if [ $i -eq $RETRY_COUNT ]; then
          echo "Failed to pull image: ${image} after $RETRY_COUNT attempts."
          exit 1
        fi
        echo "Retrying pull for image: ${image} ($i/$RETRY_COUNT)"
        sleep 2
      }
    done

    sudo ${runtime} tag ${image} ${new_image}

    # Retry logic for pushing images
    for i in $(seq 1 $RETRY_COUNT); do
      sudo ${runtime} push ${new_image} && break || {
        if [ $i -eq $RETRY_COUNT ]; then
          echo "Failed to push image: ${new_image} after $RETRY_COUNT attempts."
          exit 1
        fi
        echo "Retrying push for image: ${new_image} ($i/$RETRY_COUNT)"
        sleep 2
      }
    done
  done <<< "$(cat ${IMAGES_FROM_FILE})"
  sudo docker stop $REGISTRY_NAME && sudo docker rm $REGISTRY_NAME
  echo "Succeeded to register container images to local registry."
}

# Function to execute manage-offline-files.sh
execute_manage_offline_files() {
  echo "========== Download WebServer File =========="
  # Generate offline files
  sh $CURRENT_DIR/manage-offline-files.sh

  # Clean up temporary files
  rm -rf $CURRENT_DIR/offline-files.tar.gz
}

# Prepare the images list
prepare_images_list

# Download and register images to local registry
download_images

# Execute manage-offline-files.sh
execute_manage_offline_files

echo "Finished ready to Offline"
