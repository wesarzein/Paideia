# Fase 4B.3: implementada, cierre pendiente

Implementación conservada en `81c8b89`, rama `dev/phase4b3-institutional-excel`.
**No declarar cerrada esta fase:** falta evidencia concluyente de persistencia después
del reinicio del laboratorio `paideia-dev-phase4b3ui`.

Evidencias de ejecución anterior registradas en la conversación, no repetidas en esta
continuación: 92 pruebas aprobadas en PostgreSQL aislado (17 casos de esta fase),
lectura de plantilla completa con 160 entradas, vacíos frente a ceros, fórmulas,
corrección, correspondencias, confirmación, guardado, consulta con filtros del aula,
reimportación sin duplicados y actualización expresamente confirmada. No se presenta
la existencia de pruebas en el repositorio como sustituto de su ejecución.

La plantilla sintética reproduce encabezados, nueve combinaciones y 64 fórmulas de
la copia anonimizada inspeccionada. Promedios/cachés/literales son referencia, no
criterios persistidos; las fórmulas desconocidas no se ejecutan. Las fechas de los
dos bloques requieren confirmación, no se deducen de la fecha de importación.

`scripts/verify_institutional_import.py --resume-consultation` sigue utilizando
Playwright y reinicia servicios sintéticos. La ejecución final quedó sin resultado
recuperable. Una futura alternativa ligera API/PostgreSQL deberá comparar las diez
notas, sus identificadores, valores, snapshots y el inventario antes/después de un
reinicio autorizado, y distinguirla de una nueva prueba de navegador.

**Actualización 4B.5, 09/10/2026:** esa alternativa ligera ya está implementada en
`scripts/verify_phase4b3_persistence.py`, restringida a `paideia-dev-phase4b3ui` y sin
Playwright. No se ejecutó porque Docker estaba detenido y solo había 0,49 GiB de RAM
disponible. Por tanto, la fase continúa pendiente y no cerrada.

Docker permanece pausado intencionalmente por el responsable. No reactivarlo,
crear laboratorios ni usar la instalación institucional para completar esta prueba.
Las migraciones 0012/0013 no se ejecutaron en la base institucional en esta fase.
