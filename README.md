# GitOps CI/CD Pipeline with ArgoCD & AI Health Monitoring

A production-style GitOps pipeline where Jenkins handles CI and ArgoCD handles CD on a self-managed Kubernetes cluster hosted on GCP. Features an AI-powered post-deployment health monitor that automatically rolls back unhealthy deployments.

---

## What it does

A single `git push` triggers the entire pipeline:

1. **Jenkins CI** — builds a Docker image, pushes it to DockerHub, updates the Kubernetes manifest with the new image tag, and commits it back to GitHub
2. **ArgoCD CD** — detects the new manifest in GitHub, syncs the Kubernetes cluster to match, and performs a rolling update
3. **AI Health Monitor** — waits for pods to stabilize, hits the live app URL, sends the HTTP status and pod logs to Groq AI (Llama 3.1), and decides if the deployment is healthy
4. **Auto Rollback** — if the AI returns UNHEALTHY, Jenkins runs `git revert` and pushes it; ArgoCD detects the revert and restores the previous image automatically

---

## Tech Stack

| Layer | Technology |
|---|---|
| Application | Python · Streamlit |
| Containerization | Docker · DockerHub |
| CI | Jenkins (Poll SCM) · Groovy Pipeline |
| CD | ArgoCD (GitOps) |
| Orchestration | Kubernetes (self-managed) |
| Infrastructure | GCP VM (k8s-master-01) |
| AI | Groq API · Llama 3.1 8B Instant |
| Source Control | GitHub |

---

## Architecture

```
Developer → GitHub → Jenkins CI → DockerHub
                         ↓
                  Update k8s manifest → GitHub
                                           ↓
                                       ArgoCD → Kubernetes Cluster → Live App
                                                      ↓
                                             AI Health Check (Groq)
                                            /                    \
                                        HEALTHY              UNHEALTHY
                                           ↓                      ↓
                                    Pipeline SUCCESS         git revert → ArgoCD rollback
```

---

## Project Structure

```
gitops_argocd/
├── app/
│   └── app.py               # Streamlit application
├── k8s/
│   ├── deployment.yaml      # Kubernetes Deployment (2 replicas)
│   └── service.yaml         # NodePort Service (port 30095)
├── argocd/
│   └── application.yaml     # ArgoCD Application manifest
├── scripts/
│   └── health_check.py      # AI post-deployment health monitor
├── Dockerfile               # Container image definition
└── Jenkinsfile              # 6-stage CI/CD pipeline
```

---

## Key Features

- **GitOps model** — Git is the single source of truth. No manual `kubectl apply`. Every change is versioned and auditable.
- **ArgoCD self-healing** — if someone manually changes the cluster (e.g. `kubectl scale`), ArgoCD detects the drift and reverts it within 30 seconds
- **ArgoCD pruning** — resources removed from Git are automatically deleted from the cluster
- **AI-powered health check** — uses Groq's Llama 3.1 to assess deployment health beyond a simple HTTP 200 check, enabling reasoning over multiple signals
- **Automatic rollback** — unhealthy deployments are reverted without any manual intervention via `git revert` + ArgoCD sync
- **Secure secrets** — Groq API key and GitHub token stored in Jenkins credentials, never in code

---

## Pipeline Stages

| Stage | What it does |
|---|---|
| 1. Checkout | Clone the repo into Jenkins workspace |
| 2. Build Docker Image | `docker build` from `app/` |
| 3. Push to DockerHub | Push image with build number as tag |
| 4. Update k8s Manifest | `sed` the image tag in `deployment.yaml` |
| 5. Commit & Push to GitHub | Jenkins commits the updated manifest back to master |
| 6. AI Health Check | Wait 125s → HTTP check → Groq AI decision → pass or rollback |

---

## ArgoCD Configuration

- **Sync policy:** Automated with `prune: true` and `selfHeal: true`
- **Reconciliation interval:** 30 seconds
- **Watches:** `k8s/` folder on `master` branch
- **Namespace:** `streamlit-app`
