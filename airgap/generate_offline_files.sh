#!/bin/sh

# Define variables
CURRENT_DIR=$(dirname "$(realpath "$0")")
K8S_OFFLINE_PATH=$(realpath "$CURRENT_DIR/../kubespray/contrib/offline")
IMAGE_LIST_FILE_NAME="images.list"
export IMAGES_FROM_FILE="$K8S_OFFLINE_PATH/temp/$IMAGE_LIST_FILE_NAME"

# Check if HTTP server is needed
NO_HTTP_SERVER=no

# Execute the generate_list.sh script
sh "$K8S_OFFLINE_PATH/generate_list.sh"

# Function to add images from helm charts to the images list
add_helm_images() {
  local chart_path=$1
  echo "Processing images from chart: $chart_path"
  helm images get "$chart_path" >> "$IMAGES_FROM_FILE"
}

# List of helm chart paths
HELM_CHARTS=(
  "$CURRENT_DIR/../applications/csi-driver-nfs/csi-driver-nfs"
  "$CURRENT_DIR/../applications/gpu-operator/custom-gpu-operator"
  "$CURRENT_DIR/../applications/prometheus/kube-prometheus-stack"
  "$CURRENT_DIR/../applications/keycloak/keycloak"
  "$CURRENT_DIR/../applications/astrago/astrago"
)

# Loop through the helm charts and add images to the list
for chart in "${HELM_CHARTS[@]}"; do
  add_helm_images "$chart"
done

# Move to the offline directory
cd "$K8S_OFFLINE_PATH" || exit

# Generate Kubernetes images list
sh manage-offline-container-images.sh create

# Generate offline files
sh manage-offline-files.sh

# Clean up temporary files
rm -rf offline-files temp

# Move generated files to current directory
mv offline-files.tar.gz container-images.tar.gz "$CURRENT_DIR"

