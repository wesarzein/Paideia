# Entrega BI e IA experimental

09/10/2026, segunda laptop, rama `dev/phase4b5-academic-stabilization`.
Fuentes: alcance, matriz 4A, estrategia IA y solicitud integral REQ-24–32.
ERS originales no disponibles. No se declara entrega integral todavía.

## BI verificado

`GET /api/v1/kpis` consulta PostgreSQL con los predicados académicos existentes:
docentes por curso y sección, familias sin acceso al panel del personal. Filtros
por nivel/grado/sección/estudiante/curso/periodo/bimestre; asistencia por periodo
porque sus registros no tienen identidad de bimestre. Sin caché de resultados.

Promedios de referencia con pesos capturados; cero real distinto de null. No activa
fórmulas oficiales. Distribución numérica/literal, evolución mensual, comparación
de periodos, detalle autorizado por curso/alumno, ausencias/tardanzas y cobertura
de matrículas activas. La completitud de criterios obligatorios usa la revisión
histórica de los contextos registrados; opcionales ausentes por separado, sin
política inventada. No reconstruye evaluaciones sin registros ni calendario esperado.
Regla literal estricta de plantilla, no política universal.

- 7/7 PostgreSQL en 13,01 s, esquemas UUID: ACL cruzada, filtros, ceros, límites
  literales, ausencia de evidencia, revisión histórica y opcionales.
- 46/46 Vitest en 21,80 s (cuatro nuevos de BI); build 26,836 s.
- Navegador detectó desbordamiento del menú móvil compartido; `aside min-width:0`
  lo corrige. Build posterior 27,301 s; recorrido Playwright pasó gráficos,
  curso único, vacío/null, error/reintento y 390 px, cero errores JavaScript.
- Consulta KPI local observada: 0,051 s; muestra pequeña, no acredita carga productiva.
- 32 notas exactas conservadas; SHA-256
  `e7998edc2fb51a66ea381f2e15207f45e6e7502df0ac29664dbe66e96f92a1b5`.
  Evidencia privada: `config/local/business-ui.result.json`. Sin migración BI.

## IA y consolidación pendientes

Extractor temporal, dataset ficticio y regresión logística en desarrollo; no
predicciones institucionales. No push ni PR todavía: requieren auditoría del
historial saliente y aceptación integral. Backup local `backup/pre-bi-ai-a6495ce`.
