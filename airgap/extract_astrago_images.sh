#!/bin/bash

CURRENT_DIR=$(dirname "$(realpath "$0")")
ADDITIONAL_IMAGE_ORIGINAL_FILE=$CURRENT_DIR/kubespray-offline/imagelists/images.txt.original
ADDITIONAL_IMAGE_FILE=$CURRENT_DIR/kubespray-offline/imagelists/images.txt

# Function to add images from helm charts to the images list
add_helm_images() {
  local chart_path=$1
  helm template $chart_path | yq -r '..|.image? | select(.)' | sort | uniq | sed '1d' >> $ADDITIONAL_IMAGE_FILE
}

gpuoperator_extract_images() {
  local chart_path=$1
  helm template $chart_path | yq eval '
    .. | select(has("repository") and has("image") and has("version")) | 
    .repository + "/" + .image + ":" + .version
  ' >> "$ADDITIONAL_IMAGE_FILE"
}

# Function to process Helm charts and prepare the images list
prepare_images_list() {
  echo "Start Extract Image List"
  cp $ADDITIONAL_IMAGE_ORIGINAL_FILE $ADDITIONAL_IMAGE_FILE
  # List of helm chart paths
  local helm_charts=(
    "$CURRENT_DIR/../applications/csi-driver-nfs/csi-driver-nfs"
    "$CURRENT_DIR/../applications/prometheus/kube-prometheus-stack"
    "$CURRENT_DIR/../applications/keycloak/keycloak"
    "$CURRENT_DIR/../applications/astrago/astrago"
  )

  # Loop through the helm charts and add images to the list
  for chart in "${helm_charts[@]}"; do
    add_helm_images "$chart"
  done
  gpuoperator_extract_images "$CURRENT_DIR/../applications/gpu-operator/custom-gpu-operator"
  echo "Finished Extract Image List"
}

prepare_images_list
