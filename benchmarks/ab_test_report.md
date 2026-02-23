# Informe AB Testing (Baseline vs Refactor)

## Resumen ejecutivo
- `section4.py` redujo tamaño de **782** a **348** líneas.
- Definiciones de función duplicadas pasaron de **5** a **0**.
- Carga de datos: promedio baseline sin caché **2.1086s**.
- Carga cacheada: primer llamado **2.2078s**, hit de caché promedio **0.0658s**.
- Aceleración en hits de caché: **32.04x**.

## Archivos de salida
- CSV de métricas: `benchmarks/ab_test_results.csv`
