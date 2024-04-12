# Kubespary Deploy
## 0. Dockerfile build
```
docker build -t kubespray .
docker run -itd --name kubespray kubespray:latest
# container 내부로 접속
docker exec -it kubespray bash
```

## 1. Inventory 파일 수정
```
inventory 파일 경로 : inventory/mycluster/astrago.yaml
```
### 예시
```
all:
  hosts:                            <- hosts에 클러스터 노드 정보 입력
    master-1:                        <- 노드의 이름
      ansible_host: 192.168.10.11    <- 노드의 IP주소
      ip: 192.168.10.11              <- 노드의 IP주소
      access_ip: 192.168.10.11       <- 노드의 IP주소
    master-2:
      ansible_host: 192.168.10.12
      ip: 192.168.10.12
      access_ip: 192.168.10.12
    master-3:
      ansible_host: 192.168.10.13
      ip: 192.168.10.13
      access_ip: 192.168.10.13
    worker-1:
      ansible_host: 192.168.10.111
      ip: 192.168.10.111
      access_ip: 192.168.10.111
    worker-2:
      ansible_host: 192.168.10.112
      ip: 192.168.10.112
      access_ip: 192.168.10.112
  children:
    kube-master:
      hosts:          <- 위 hosts의 노드 목록 중에 마스터로 사용할 노드의 이름 추가
        master-1:
        master-2:
        master-3:
    kube-node:
      hosts:          <- 위 hosts의 노드 목록 중에 워커로 사용할 노드의 이름 추가
        worker-1:
        worker-2:
    etcd:          
      hosts:          <- 위 hosts의 노드 목록 중에 etcd를 설치할 노드의 이름 추가
        master-1:
        master-2:
        master-3:
    k8s-cluster:
      children:
        kube-master:
        kube-node:
    calico-rr:
      hosts: {}

```

## 2. ssh-copy-id로 ssh publickey 전달
```
# ssh key 생성
ssh-keygen -t rsa
계속 엔터 실행

# inventory 파일에 등록된 모든 노드에 대해 public key 전달
ssh-copy-id root@<IP>
비밀번호 입력하여 전달.
```
## 3. ansible로 kubernetes 설치
```
ansible-playbook -i inventory/mycluster/astrago.yaml  --become --become-user=root cluster.yml
```