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


## 5) Evaluación: cola externa (Celery/RQ + Redis)

Recomendación para producción con picos altos o jobs largos:

- **Cuándo mover**: si el porcentaje de `busy` crece, hay timeouts frecuentes o el HPA escala pods web sin reducir cola local.
- **Beneficio principal**: desacoplar cómputo pesado del proceso web, permitiendo escalar workers por separado.
- **Opción 1 (Celery + Redis)**: mejor para enrutamiento avanzado, reintentos complejos y observabilidad madura (Flower/Prometheus).
- **Opción 2 (RQ + Redis)**: integración más simple y menor complejidad operativa para cargas moderadas.
- **Plan sugerido**: mantener API de `enqueue/poll` y cambiar la implementación interna para publicar/consultar jobs en Redis, con workers dedicados en otro `Deployment`.
