#!/bin/bash

# Helm 3 설치 스크립트 다운로드
curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3

# 스크립트에 실행 권한 부여
chmod 700 get_helm.sh

# Helm 3 설치 스크립트 실행
./get_helm.sh && rm get_helm.sh

# Helmfile 다운로드
wget https://github.com/helmfile/helmfile/releases/download/v0.162.0/helmfile_0.162.0_linux_amd64.tar.gz

# 압축 해제
tar -zxvf helmfile_0.162.0_linux_amd64.tar.gz

# 실행 권한 부여
chmod +x helmfile

# 실행 파일을 /usr/local/bin 으로 이동
mv helmfile /usr/local/bin

rm helmfile_0.162.0_linux_amd64.tar.gz  LICENSE README*
