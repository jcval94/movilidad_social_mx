# Informe AB Testing (Baseline vs Refactor)

## Resumen ejecutivo
- `section4.py` redujo tamaño de **784** a **801** líneas.
- Definiciones de función duplicadas pasaron de **0** a **0**.
- Carga de datos: promedio baseline sin caché **2.1421s**.
- Carga cacheada: primer llamado **2.3086s**, hit de caché promedio **0.0746s**.
- Aceleración en hits de caché: **28.73x**.
- Delta promedio (before/after): **2.0675s** menos por llamada en cache hit.
- Hit ratio medido en experimento: **75%** (3 hits / 4 llamadas cacheadas).

## Archivos de salida
- CSV de métricas: `benchmarks/ab_test_results.csv`
