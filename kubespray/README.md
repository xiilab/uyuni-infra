# Kubespary Deploy
## 0. Dockerfile build
```
docker build -t kubespray .
docker run -itd --name kubespray kubespray:latest
# container 내부로 접속
docker exec -it kubespray bash
```

## 1. Inventory 위치
```
개발 클러스터 : inventory/mycluster/develop.yaml
스테이징 클러스터 : inventory/mycluster/staging.yaml
```

## 2. ssh-copy-id로 ssh publickey 전달
```
# ssh key 생성
ssh-keygen -t rsa
# inventory에 등록된 모든 노드에 대해 public key 전달
ssh-copy-id root@<IP>
비밀번호 입력하여 전달.
```
## 3. ansible로 kubernetes 설치
```
ansible-playbook -i inventory/mycluster/develop.yaml  --become --become-user=root cluster.yml
ansible-playbook -i inventory/mycluster/staging.yaml  --become --become-user=root cluster.yml

```