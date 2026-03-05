# Despliegue en Kubernetes

## 1) Build y push de imagen

```bash
docker build -t ghcr.io/your-org/movilidad-social-mx:latest .
docker push ghcr.io/your-org/movilidad-social-mx:latest
```

## 2) Ajustes mínimos

- Cambia el `image` en `deployment.yaml` al registro real.
- Cambia el host `movilidad-social.example.com` en `ingress-nginx.yaml`.
- Crea el secreto real a partir de `secret.example.yaml`.

## 3) Aplicar manifiestos

```bash
kubectl apply -f deploy/k8s/namespace.yaml
kubectl apply -f deploy/k8s/secret.example.yaml
kubectl apply -f deploy/k8s/deployment.yaml
kubectl apply -f deploy/k8s/service.yaml
kubectl apply -f deploy/k8s/ingress-nginx.yaml
kubectl apply -f deploy/k8s/hpa.yaml
```

## 4) Notas de arquitectura

- **Múltiples réplicas**: `Deployment` con `replicas: 3`.
- **Balanceo**: Ingress NGINX reparte tráfico entre pods por el `Service`.
- **Afinidad de sesión**: deshabilitada (`sessionAffinity: None` y `affinity: none`) para favorecer stateless.
- **Autoscaling**: HPA por CPU, memoria y latencia p95 (`http_request_duration_seconds_p95`).

> Para la métrica p95 necesitas exponer métricas Prometheus y mapearlas como custom metric en el cluster (por ejemplo, `prometheus-adapter`).

## 5) Redis obligatorio en producción/horizontal

- Este despliegue **requiere Redis** para estado compartido cuando `ENV=production` o `REDIS_REQUIRED=true`.
- `deployment.yaml` define `REDIS_URL`, `REDIS_REQUIRED=true` y `ENV=production` para forzar fail-fast si Redis no responde.
- Si Redis no está disponible, los probes de `startup`/`readiness` fallarán y el pod no aceptará tráfico.
- **No despliegues en horizontal (replicas > 1) sin Redis**: perderías consistencia de estado entre pods.

