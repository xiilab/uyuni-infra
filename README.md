# Astrago 배포 및 관리 스크립트

이 스크립트는 Astrago 환경을 배포하고 관리하기 위한 유틸리티입니다. Astrago를 쉽게 배포하고 관리할 수 있도록 도와주는 툴입니다. 이 스크립트를 사용하여 Astrago 환경을 손쉽게 관리할 수 있습니다.
## 사전준비
1. yq 설치
```aidl
snap install yq
```
2. helm, helmfile 설치
```aidl
sh tools/install_helmfile.sh
```

## 사용법:

```bash
./deploy_astrago.sh [deploy|sync|destroy]
```

이 스크립트는 다섯 가지 주요 옵션을 지원합니다. 각각의 옵션은 특정 작업을 수행합니다.

- `deploy`: 새로운 환경을 만들고 astrago 전체 앱을 설치합니다. 사용자로부터 외부 접속 IP 주소, NFS 서버의 IP 주소, NFS의 base 경로를 입력받습니다." 
- `sync`: 이미 설정된 환경에 대해 astrago 전체 앱을 설치(업데이트)합니다.
- `destroy`: 이미 설정된 환경에 대해 astrago 전체 앱을 삭제합니다. 
- `sync <앱 이름>`: 특정 앱에 대해 설치(업데이트)합니다. 
- `destroy <앱 이름>`: 특정 앱에 대해 삭제합니다.

## 앱 종류:
- nfs-provisioner: NFS 프로비저너
- gpu-operator: GPU 오퍼레이터
- prometheus: Prometheus 모니터링 시스템
- event-exporter: 이벤트 익스포터
- keycloak: Keycloak 인증 및 인가 서비스
- astrago: Astrago 자체 앱

## 예시:
### 새로운 환경을 생성하고 astrago 앱 전체 설치:
```bash
./astrago.sh deploy
```
`deploy` 옵션을 사용하여 astrago 전체 환경을 배포합니다. 이 명령은 새로운 환경을 생성하고 설정된 astrago 전체 앱을 설치합니다.
```bash
외부 접속 IP 주소를 입력하시오: < 외부와 연결되어 있는 K8S 클러스터의 노드 IP > 입력
볼륨 타입을 입력하세요 (nfs 또는 local): 
# nfs 일 때 
NFS 서버의 IP 주소를 입력하시오: < NFS 서버 IP 입력 > e.g 10.61.3.2
NFS의 base 경로를 입력하시오: < base 경로를 입력 > e.g. /nfs-base/astrago
# local 일 때 
데이터를 저장할 K8S 노드 이름을 입력하시오: < K8S Node 이름 입력 > e.g. worker-1
데이터를 저장할 base 경로를 입력하시오: < base 경로 입력 > e.g. /local-base/astrago

```

### 이미 설정된 환경으로 astrago 앱 전체 설치:
```bash
./deploy_astrago.sh sync
```
`sync` 옵션을 사용하여 설정된 환경에 대해 전체 앱에 대하여 변경 사항을 동기화합니다. 

### 이미 설정된 환경으로 astrago 앱 전체 삭제:
```bash
./deploy_astrago.sh destroy
```
`destroy` 옵션을 사용하여 설정된 환경에 대해 astrago 전체 앱을 삭제합니다. 

### 특정 앱 설치(업데이트):
```bash
./deploy_astrago.sh sync prometheus
```
`sync <앱 이름>` 옵션을 사용하여 특정 앱에 대해 변경 사항을 배포합니다. 이 명령은 지정된 앱에 대해서만 helmfile sync를 실행합니다.

### 특정 앱 삭제:
```bash
./deploy_astrago.sh destroy prometheus
```
`destroy <앱 이름>` 옵션을 사용하여 특정 앱을 삭제합니다. 이 명령은 지정된 앱에 대해서만 helmfile sync를 실행합니다.
