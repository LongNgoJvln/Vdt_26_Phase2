# Internal server deployment

This document is a deployment handoff, not a record of a successful deployment.
The package was source-verified and tested, but the workstation used to prepare
it did not have Docker, so build and runtime health checks must run on the
internal server.

## 1. Unpack and verify

```sh
unzip nc_v7_monolith.zip
cd nc_v7_monolith
python3 scripts/verify_monolith_source.py
```

The verifier must report `PASS`. Confirm that `.env`, kubeconfig, database files,
logs, sessions, uploads, and `k8s/secret-*.yaml` are absent.

## 2. Configure environment

```sh
cp .env.example .env
chmod 600 .env
```

At minimum review:

- `DATABASE_URL` and `ODYSSEUS_MULTITENANT_POSTGRES`
- `QDRANT_URL`, `QDRANT_API_KEY`, and embedding configuration
- `ODYSSEUS_USE_MINIO` and all `MINIO_*` values
- authentication password, cookie mode, and allowed origins
- model endpoints/keys, either from environment or the Admin UI
- SearXNG and ntfy addresses if those features are used

Do not reuse the example `CHANGE_ME` values.

## 3A. Docker Compose

```sh
docker compose config
docker compose build odysseus
docker compose up -d
docker compose ps
docker compose logs --tail=200 odysseus
curl -fsS http://127.0.0.1:7000/api/health
curl -fsS http://127.0.0.1:7000/api/ready
```

For the internal multi-tenant deployment, set Postgres mode and a Postgres
`DATABASE_URL`; startup applies Alembic through revision
`0006_network_change_records`. Qdrant and MinIO can remain external.

## 3B. Kubernetes

The checked-in manifests currently assume:

- namespace `hw5gai`
- image `172.20.1.22/5g-ai/nc-v7-monolith:latest`
- a node label matching IP `10.55.110.122`
- NodePorts defined in `k8s/README.md`
- embedding weights at `/home/ai/networkchange/bge-small-en-v1.5`
- external Qdrant/MinIO values supplied through `app-env`

Review and change those site-specific values before applying.

Create Secrets out of band:

```sh
kubectl -n hw5gai create secret docker-registry harbor-pull \
  --docker-server=172.20.1.22 \
  --docker-username='<robot-user>' \
  --docker-password='<robot-password>' \
  --docker-email='<email>' \
  --dry-run=client -o yaml | kubectl apply -f -

cp .env.example .env.k8s
# Edit .env.k8s with real internal values.
kubectl -n hw5gai create secret generic app-env \
  --from-env-file=.env.k8s --dry-run=client -o yaml | kubectl apply -f -

docker build -t 172.20.1.22/5g-ai/nc-v7-monolith:latest .
docker push 172.20.1.22/5g-ai/nc-v7-monolith:latest
kubectl apply -k k8s/
kubectl -n hw5gai rollout status deploy/networkchange --timeout=5m
kubectl -n hw5gai logs deploy/networkchange --tail=200
```

## 4. Configure read-only MCP

Log in as an administrator and add the Kubernetes/network MCP server through the
existing MCP settings UI. Confirm that:

- the server connects and tools are discovered;
- only read/list/get/log/event/metric-style tools are exposed;
- write/apply/delete/patch/exec tools are absent or disabled;
- the MCP process/container receives the minimum read-only credentials;
- tool descriptions are indexed in Qdrant after connection.

The application does not ship a kubeconfig or Kubernetes MCP implementation.

## 5. Smoke-test the network workflow

Use agent mode and the configured model. Suggested prompts:

1. `Liệt kê các read-only MCP tools có thể dùng cho Kubernetes.`
2. `Thu thập network snapshot cho namespace <lab-namespace>; chỉ dùng read-only MCP.`
3. `Lập change proposal để scale deployment <name>, không thực thi thay đổi.`
4. `Validate manifest trong proposal và tạo report thành document.`
5. `Hiển thị network-change history của tôi.`

Verify in logs that MCP reads happen before `collect_network_snapshot`, the
proposal says `execution_allowed=false`, and no cluster mutation is attempted.

## 6. Rollback deployment

Application rollback is an image rollback; database migration `0006` only adds
two tables and is backward-compatible with the base application.

```sh
kubectl -n hw5gai rollout undo deploy/networkchange
```

Do not run the Alembic downgrade or delete the new tables unless the snapshot
and proposal data has been backed up and deletion is explicitly approved.

