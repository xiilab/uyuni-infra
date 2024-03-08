# Astrago Infra Deploy

[Helmfile](https://helmfile.readthedocs.io/en/latest/)을 이용하여 Astrago에 필요한 플랫폼을 설치
* gpu-operator
* keycloak 
* prometheus
* astrago

## 1. 디렉토리 구조
```
├── README.md
├── applications  -> 각 플랫폼별 helmfile이 저장되어 있는 폴더
│   ├── astrago
│   ├── csi-driver-nfs
│   ├── flux2
│   ├── gpu-operator
│   ├── keycloak
│   ├── prometheus
├── environments  -> 환경별로 다른 값을 적용할 수 있는 폴더
│   └──  install_helmfile.sh
├── tools  -> helm & helmfile 설치 스크립트 
│   ├── 
│   ├── dev
│   └── stage
└── helmfile.yaml  -> main helmfile 파일
```

## 2. 환경설정 변경 방법
1. environments > dev OR stage > values.yaml 변경 
2. dev(개발 클러스터 배포 환경), stage(스테이징 클러스터 배포 환경)
```
astrago:
  prometheus:
    host: http://10.61.3.12:30090
# astrago에서 연결할 keycloak 설정 정보    
  keycloak:
    host: http://10.61.3.8:30001
    realm: myrealm
    client: kubernetes-client
    clientSecret: 7bE2Oq2HyKrPsX49EXul0G48O4c4kkFv
    nextauthUrl: http://10.61.3.12:30080
# astrago mariadb 설정 정보    
  mariadb:
    rootPassword: root
    database: astrago
    username: astrago
    password: xiirocks
    volume:
      volumeName: astra-mariadb-volume
      volumeSize: 8Gi
      volumeType: nfs
      nfs:
        server: 10.61.3.2
        path: /kube_storage/astra-mariadb-volume
  core:
    repository: harbor.xiilab.com:32443/uyuni/server-core
    imageTag: "develop-f3d1c6a"
  batch:
    repository: harbor.xiilab.com:32443/uyuni/server-batch
    imageTag: "develop-f3d1c6a"
  monitor:
    repository: harbor.xiilab.com:32443/uyuni/server-monitor
    imageTag: "develop-f3d1c6a"
  frontend:
    repository: "harbor.xiilab.com:32443/uyuni/uyuni-frontend"
    imageTag: develop-27a78d1
    service:
      type: NodePort
      port: 3000
      nodePort: 30080
```

## 3. 명령어
### 3.1 인프라 설치(맨 상단의 위치에서(helmfile.yaml이 있는 곳에서) 실행)
#### helmfile을 이용하여 전체 인프라 설치 
```sh
helmfile --environment <env name> sync
ex) helmfile --environment dev sync (개발 클러스터 배포)
ex) helmfile --environment stage sync (스테이징 클러스터 배포)
```
#### helmfile을 이용하여 전체 인프라 제거
```sh
helmfile --environment <env name> destroy
ex) helmfile --environment dev destroy (개발 클러스터 제거)
ex) helmfile --environment stage destroy (스테이징 클러스터 제거)
```
#### helmfile을 이용하여 개별 인프라 설치
```sh
helmfile --environment <env name> -l app=<app name> sync
ex) helmfile --environment dev -l app=gpu-operator sync (gpu operator 배포)
ex) helmfile --environment dev -l app=prometheus sync (prometheus 배포)
ex) helmfile --environment dev -l app=keycloak sync (keycloak 배포)
ex) helmfile --environment dev -l app=astrago sync (astrago 배포)
```
#### helmfile을 이용하여 개별 인프라 제거
```sh
helmfile --environment <env name> -l app=<app name> destroy
ex) helmfile --environment dev -l app=gpu-operator destroy (gpu operator 제거)
ex) helmfile --environment dev -l app=prometheus destroy (prometheus 제거)
ex) helmfile --environment dev -l app=keycloak destroy (keycloak 제거)
ex) helmfile --environment dev -l app=astrago destroy (astrago 제거)
```