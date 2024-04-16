#!/bin/bash
export LANG=en_US.UTF-8

# 환경 이름을 고정
environment_name="astrago"

# 사용법 출력 함수
print_usage() {
    echo "사용법: $0 [deploy|sync|destroy|sync_only|destroy_only]"
    echo ""
    echo "deploy        : 새로운 환경을 만들고 astrago 전체 앱을 설치합니다. 사용자로부터 외부 접속 IP 주소, NFS 서버의 IP 주소, NFS의 base 경로를 입력받습니다."
    echo "sync          : 이미 설정된 환경에 대해 astrago 전체 앱을 설치(업데이트)합니다."
    echo "destroy       : 이미 설정된 환경에 대해 astrago 전체 앱을 삭제합니다."
    echo "sync <app이름>     : 특정 앱에 대해 설치(업데이트)합니다."
    echo "                사용법: $0 sync <앱 이름>"
    echo "destroy <app이름>  : 특정 앱에 대해 삭제합니다."
    echo "                사용법: $0 destroy <앱 이름>"
    echo ""
    echo "앱 종류:"
    echo "nfs-provisioner"
    echo "gpu-operator"
    echo "prometheus"
    echo "event-exporter"
    echo "keycloak"
    echo "astrago"
    exit 0
}

# 환경 디렉토리 생성 함수
create_environment_directory() {
    if [ ! -d "environments/$environment_name" ]; then
        echo "환경 디렉토리가 존재하지 않습니다. 생성 중..."
        mkdir "environments/$environment_name"
        echo "환경 디렉토리가 생성되었습니다."
    else
        echo "환경 디렉토리가 이미 존재합니다."
    fi
    cp -r environments/default/* "environments/$environment_name/"
    # 생성된 환경 파일 경로 출력
    echo "환경 파일이 생성된 경로: $(realpath "environments/$environment_name")"
}

# 사용자로부터 IP 주소 입력 받는 함수
get_ip_address() {
    local ip_variable=$1
    local message=$2
    while true; do
        echo -n "$message: "
        read -r ip
        if [[ $ip =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]; then
            eval "$ip_variable=$ip"
            break
        else
            echo "유효하지 않은 IP 주소입니다. 다시 입력하세요."
        fi
    done
}

# 사용자로부터 볼륨 타입 입력 받는 함수
get_volume_type() {
    local volume_type_variable=$1
    while true; do
        echo -n "볼륨 타입을 입력하세요 (nfs 또는 local): "
        read -r volume_type
        if [ "$volume_type" == "nfs" ] || [ "$volume_type" == "local" ]; then
            eval "$volume_type_variable=$volume_type"
            break
        else
            echo "유효하지 않은 볼륨 타입입니다. 다시 입력하세요."
        fi
    done
}

# 사용자로부터 폴더 생성을 위한 basePath 입력 받는 함수
get_base_path() {
    local base_path_variable=$1
    local message=$2
    echo -n "$message: "
    read -r base_path
    eval "$base_path_variable=$base_path"
}

# main 함수
main() {
    case "$1" in
        "--help")
            print_usage
            ;;
        "deploy")
            create_environment_directory

            # 사용자로부터 외부 접속 IP 주소를 입력 받음
            get_ip_address external_ip "외부 접속 IP 주소를 입력하시오"

            # 사용자로부터 볼륨 타입을 입력 받음
            get_volume_type volume_type

            if [ "$volume_type" == "nfs" ]; then
                # 사용자로부터 NFS 서버의 IP 주소를 입력 받음
                get_ip_address nfs_server_ip "NFS 서버의 IP 주소를 입력하시오"

                # 사용자로부터 NFS의 base 경로를 입력 받음
                get_base_path nfs_base_path "NFS의 base 경로를 입력하시오"

                values_file="environments/$environment_name/values.yaml"

                # externalIP 수정
                yq -i ".externalIP = \"$external_ip\"" "$values_file"

                # nfs 서버 IP 주소와 base 경로 수정
                yq -i ".nfs.enabled = true" "$values_file"
                yq -i ".nfs.server = \"$nfs_server_ip\"" "$values_file"
                yq -i ".nfs.basePath = \"$nfs_base_path\"" "$values_file"
            elif [ "$volume_type" == "local" ]; then
                # 사용자로부터 노드 이름을 입력 받음
                echo -n "데이터를 저장할 K8S 노드 이름을 입력하시오: "
                read -r node_name

                # 사용자로부터 base 경로를 입력 받음
                echo -n "데이터를 저장할 base 경로를 입력하시오: "
                read -r local_base_path

                values_file="environments/$environment_name/values.yaml"

                # externalIP 수정
                yq -i ".externalIP = \"$external_ip\"" "$values_file"

                # node 이름과 base 경로 수정
                yq -i ".local.enabled = true" "$values_file"
                yq -i ".local.nodeName = \"$node_name\"" "$values_file"
                yq -i ".local.basePath = \"$local_base_path\"" "$values_file"
            fi

            echo "values.yaml 파일이 수정되었습니다."

            # helmfile로 환경을 sync합니다.
            echo "helmfile -e $environment_name sync를 실행합니다."
            helmfile -e "$environment_name" sync
            ;;
        "sync" | "destroy")
            if [ ! -d "environments/$environment_name" ]; then
                echo "환경이 설정되어 있지 않습니다. deploy를 먼저 실행하세요."
            elif [ -n "$2" ]; then
                echo "helmfile -e $environment_name -l app=$2 $1를 실행합니다."
                helmfile -e "$environment_name" -l "app=$2" "$1"
            else
                echo "helmfile -e $environment_name $1를 실행합니다."
                helmfile -e "$environment_name" "$1"
            fi
            ;;
        *)
            print_usage
            ;;
    esac
}

# 스크립트 실행
main "$@"

