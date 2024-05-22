#!/bin/sh

# Define variables
runtime=docker
CURRENT_DIR=$(dirname "$(realpath "$0")")
RETRY_COUNT=3

AIRGAP_FILES_DIR=$CURRENT_DIR/airgap-files

IMAGE_LIST_FILE_NAME="images.list"
TEMP_IMAGE_LIST="$CURRENT_DIR/temp/$IMAGE_LIST_FILE_NAME"
IMAGE_LIST="$AIRGAP_FILES_DIR/$IMAGE_LIST_FILE_NAME"
REGISTRY_PORT=25000
REGISTRY_NAME=ready-registry

OFFLINE_FILES_DIR_NAME="offline-files"
OFFLINE_FILES_DIR="$AIRGAP_FILES_DIR/${OFFLINE_FILES_DIR_NAME}"
FILES_LIST=${FILES_LIST:-"${CURRENT_DIR}/temp/files.list"}


mkdir "$AIRGAP_FILES_DIR"

# Function to add images from helm charts to the images list
add_helm_images() {
  local chart_path=$1
  echo "Processing images from chart: $chart_path"
  helm images get "$chart_path" >> "$IMAGE_LIST"
}

# Function to process Helm charts and prepare the images list
prepare_images_list() {
  cp $TEMP_IMAGE_LIST $IMAGE_LIST

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
  echo "========== Download Airgap Images =========="

  set +e
  sudo docker container inspect $REGISTRY_NAME >/dev/null 2>&1
  if [ $? -ne 0 ]; then
    sudo docker run --restart=always -d -p "${REGISTRY_PORT}:5000" -v "$CURRENT_DIR/airgap-files/registry:/var/lib/registry" --name $REGISTRY_NAME registry:latest
  fi
  set -e

  DESTINATION_REGISTRY="localhost:${REGISTRY_PORT}"

  while read -r image; do
    image_without_tag="${image%:*}"
    tag="${image##*:}"
    new_image="${DESTINATION_REGISTRY}/${image_without_tag#*/}:${tag}"
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
  done < "$IMAGE_LIST"

  sudo docker stop $REGISTRY_NAME && sudo docker rm $REGISTRY_NAME
  echo "Succeeded to register container images to local registry."
}

# Function to execute manage-offline-files.sh
execute_manage_offline_files() {
  echo "========== Download Airgap WebServer Files =========="
  rm -rf "${OFFLINE_FILES_DIR}"
  mkdir  "${OFFLINE_FILES_DIR}"

  wget -x -P "${OFFLINE_FILES_DIR}" -i "${FILES_LIST}"
  echo "Succeeded to download offline files"
}

# Prepare the images list
prepare_images_list

# Download and register images to local registry
download_images

# Execute manage-offline-files.sh
execute_manage_offline_files

