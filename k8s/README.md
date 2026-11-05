# Kubernetes deployment — namespace `hw5gai`

All four docker-compose services (networkchange, postgres, searxng, ntfy)
as k8s manifests with a NodePort Service per workload. Qdrant and MinIO
stay external (already running on another cluster).

| Service       | NodePort | In-cluster DNS                                           |
|---------------|----------|----------------------------------------------------------|
| networkchange | 30070    | `networkchange.hw5gai.svc.cluster.local:7000`            |
| postgres      | 31432    | `postgres.hw5gai.svc.cluster.local:5432`                 |
| searxng       | 30080    | `searxng.hw5gai.svc.cluster.local:8080`                  |
| ntfy          | 30091    | `ntfy.hw5gai.svc.cluster.local:80`                       |
| qdrant        | external | `http://172.20.1.109:30633` (env: `QDRANT_URL`)          |
| minio         | external | `minio-hl.hwcna.svc.cluster.local:9000` (env: `MINIO_ENDPOINT`) |

## Prerequisites

### 1. Build and push the networkchange image

```sh
docker build -t 172.20.1.22/5g-ai/nc-v7-monolith:latest .
docker push 172.20.1.22/5g-ai/nc-v7-monolith:latest
```

Repeat on every code change; `imagePullPolicy: Always` will pull the new
`:latest` tag whenever the pod restarts.

### 2. Create the Harbor pull secret

```sh
# Namespace hw5gai is assumed to already exist.
kubectl -n hw5gai create secret docker-registry harbor-pull \
  --docker-server=172.20.1.22 \
  --docker-username=<robot-account> \
  --docker-password=<robot-password> \
  --docker-email=<email>
```

This is referenced by every Deployment/StatefulSet via `imagePullSecrets` and
is deliberately absent from source control and `kustomization.yaml`.

### 3. Create the app environment secret

Copy `.env.example` to `.env.k8s`, edit every `CHANGE_ME` value, then:

```sh
cp .env.example .env.k8s
# Edit .env.k8s — set real DATABASE_URL, POSTGRES_PASSWORD,
# ODYSSEUS_ADMIN_PASSWORD, MINIO_SECRET_KEY, allow-list origins, etc.
kubectl -n hw5gai create secret generic app-env --from-env-file=.env.k8s \
  --dry-run=client -o yaml | kubectl apply -f -
```

The real Secret is deliberately absent from source control and from
`kustomization.yaml`. If you need to rotate a value later, update `.env.k8s`,
repeat the command above, and restart the affected pod.

### 4. Adjust the embedding model host path

`k8s/networkchange-deployment.yaml` mounts `/home/ai/networkchange/bge-small-en-v1.5`
as a `hostPath`. On any cluster node that will schedule the networkchange pod,
that directory must exist and be readable. For multi-node clusters,
either:

- prestage the model on every worker node, OR
- bake it into a custom sidecar image, OR
- replace the `hostPath` volume with a pre-bound PVC.

## Apply

```sh
kubectl apply -k k8s/
```

Create the two required Secrets first, then apply the ConfigMaps, stateful
services, and app through `kustomization.yaml`.

## Verify

```sh
# All four workloads reach Ready
kubectl -n hw5gai get pods -w

# Find a node IP
NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')

# App responds on /api/ready (returns 200 when Postgres+Qdrant+MinIO all healthy)
curl -fsS "http://$NODE_IP:30070/api/ready" | jq .

# Postgres reachable from the host
psql -h "$NODE_IP" -p 31432 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\dt'

# SearXNG responding
curl -fsS "http://$NODE_IP:30080/" -o /dev/null -w '%{http_code}\n'

# ntfy health
curl -fsS "http://$NODE_IP:30091/v1/health"
```

On first boot, networkchange runs `alembic upgrade head` under a Postgres
advisory lock to build schema (`core/database.py:1847`). Watch the logs:

```sh
kubectl -n hw5gai logs deploy/networkchange -f
```

## Rollback

```sh
# Delete workloads + services; PVCs survive for data preservation
kubectl delete -k k8s/

# Nuclear — also drop persisted data
kubectl -n hw5gai delete pvc --all
```

## Operational notes

- **Single replica only.** Durable state is in Postgres/MinIO/Qdrant, but MCP
  connections, detached agent-run SSE replay, and scheduler/poller coordination
  are process-local. Externalize those coordinators before scaling horizontally.
- **PV data survives pod deletion.** `postgres-data`,
  `networkchange-data`, and `ntfy-cache` PVCs persist across
  `kubectl delete deploy/sts`. Use `kubectl -n hw5gai delete pvc --all`
  only if you want to lose data.
- **Node port range.** 30000–32767 (k8s default). All four NodePorts sit
  comfortably inside.
- **SearXNG init container.** The compose file's entrypoint wrapper
  (lines 124-136) becomes a k8s initContainer that renders
  `/etc/searxng/settings.yml` from the ConfigMap template before the
  SearXNG container starts. If `SEARXNG_SECRET` is empty, the
  initContainer generates a random one — the same behavior as compose.
- **Alembic migrations are automatic.** First-boot `init_db()` runs
  `alembic upgrade head` under a `pg_advisory_lock`. No manual migration
  step needed.
- **Ingress not included.** NodePort-only per user request. To add an
  Ingress later: `kustomize edit add resource ingress.yaml` (non-breaking).

## Files

```
k8s/
├── kustomization.yaml            # top-level apply entry; resource order
├── configmap-searxng.yaml        # inline of config/searxng/settings.yml
├── postgres-statefulset.yaml     # Service(31432)+StatefulSet+PVC
├── searxng-deployment.yaml       # Service(30080)+Deployment+initContainer+ConfigMap
├── ntfy-deployment.yaml          # Service(30091)+Deployment+PVC
└── networkchange-deployment.yaml # Service(30070)+Deployment(initContainer+probes)+PVC+hostPath embeddings
```
