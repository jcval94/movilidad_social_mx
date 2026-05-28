# Despliegue en Cloud Run

## Prerrequisitos

- Proyecto de Google Cloud con facturación activa.
- APIs habilitadas: Cloud Run, Artifact Registry, Cloud Build e IAM.
- Imagen Docker publicada en Artifact Registry.
- Artefacto de modelo incluido en la imagen o montado por otro mecanismo aprobado.

## Build de imagen

Desde la raíz del repositorio:

```bash
gcloud builds submit --tag REGION-docker.pkg.dev/PROJECT_ID/REPOSITORY/movilidad-social-api:TAG -f GCP/Dockerfile .
```

## Despliegue directo

```bash
gcloud run deploy movilidad-social-api \
  --image REGION-docker.pkg.dev/PROJECT_ID/REPOSITORY/movilidad-social-api:TAG \
  --region REGION \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars MSMX_API_ENVIRONMENT=prod
```

## Despliegue declarativo

Actualiza `GCP/deploy/cloudrun.service.yaml` con proyecto, región e imagen; después aplica:

```bash
gcloud run services replace GCP/deploy/cloudrun.service.yaml --region REGION
```

## Despliegue con Terraform

```bash
cd GCP/deploy/terraform
terraform init
terraform plan -var='project_id=PROJECT_ID' -var='region=REGION' -var='image=IMAGE_URI'
terraform apply -var='project_id=PROJECT_ID' -var='region=REGION' -var='image=IMAGE_URI'
```

## Verificación posterior

```bash
curl https://SERVICE_URL/healthz
curl https://SERVICE_URL/readyz
curl -X POST https://SERVICE_URL/v1/predict \
  -H 'Content-Type: application/json' \
  --data @GCP/examples/request.predict.json
```
