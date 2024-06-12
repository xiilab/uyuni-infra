#!/bin/bash

CURRENT_DIR=$(dirname "$(realpath "$0")")
sudo cp $CURRENT_DIR/ubuntu/* /usr/local/bin/
