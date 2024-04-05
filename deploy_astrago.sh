#!/bin/bash

environment_name="astrago"  # 환경 이름을 고정

# astrago 디렉토리가 없는 경우 생성합니다.
if [ ! -d "environments/$environment_name" ]; then
    echo "환경 디렉토리가 존재하지 않습니다. 생성 중..."
    mkdir "environments/$environment_name"
    cp -r environments/dev/* "environments/$environment_name"
    echo "환경 디렉토리가 생성되었습니다."
else
    echo "환경 디렉토리가 이미 존재합니다."
fi

# 사용자로부터 외부 접속 IP 주소를 입력 받음
while true; do
    echo -n "외부 접속 IP 주소를 입력하시오: "
    read -r external_ip

    # 입력받은 IP 주소가 유효한지 확인합니다.
    if [[ $external_ip =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]; then
        break
    else
        echo "유효하지 않은 IP 주소입니다. 다시 입력하세요."
    fi
done

# 사용자로부터 NFS 서버의 IP 주소를 입력 받음
while true; do
    echo -n "NFS 서버의 IP 주소를 입력하시오: "
    read -r nfs_server_ip

    # 입력받은 IP 주소가 유효한지 확인합니다.
    if [[ $nfs_server_ip =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]; then
        break
    else
        echo "유효하지 않은 IP 주소입니다. 다시 입력하세요."
    fi
done

# 사용자로부터 NFS의 base 경로를 입력 받음
echo -n "NFS의 base 경로를 입력하시오: "
read -r nfs_base_path

# nfs_base_path에서 슬래시를 이스케이프 처리
escaped_nfs_base_path=$(echo "$nfs_base_path" | sed 's/\//\\\//g')

# values.yaml 파일 경로
values_file="environments/$environment_name/values.yaml"

# externalIP 수정
sed -i '' "s/externalIP: .*/externalIP: $external_ip/" "$values_file"

# nfs 서버 IP 주소와 base 경로 수정
sed -i '' "s/server: .*/server: $nfs_server_ip/" "$values_file"
sed -i '' "s/basePath: .*/basePath: $escaped_nfs_base_path/" "$values_file"

