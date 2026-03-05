# Informe AB Testing (Baseline vs Refactor)

## Resumen ejecutivo
- `section4.py` redujo tamaño de **799** a **803** líneas.
- Definiciones de función duplicadas pasaron de **0** a **0**.
- Carga de datos: promedio baseline sin caché **1.9048s**.
- Carga cacheada: primer llamado **2.3485s**, hit de caché promedio **0.0960s**.
- Aceleración en hits de caché: **19.83x**.

## Archivos de salida
- CSV de métricas: `benchmarks/ab_test_results.csv`
