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

Extractor temporal y regresión logística local implementados: dos pruebas de
features sin fuga futura, dos de entrenamiento/inferencia, once de registro/API
(incluye carrera y ciclo de migración). Todos aprobados sobre fixtures aisladas.
El dataset usa modelos académicos existentes, 80 alumnos ficticios, tres cursos
y cinco periodos; jamás inserta en public. Etiquetas experimentales por promedio
del periodo siguiente y corte configurable; no eficacia institucional acreditada.

0016 agrega registro, despliegue y auditoría de modelos. Ciclo 0016→0015→0016
en UUID aprobado; upgrade de public autorizado conserva las 16 tablas previas
exactas y las 32 notas. No downgrade de public. Resultado real del verificador:
`passed: true`, fingerprint PG de notas `fa9fbf0849e863ec22090e957e9054c7`.
Worker independiente bajo demanda, BLAS de un hilo y CPU máximo 180 s; backend
con memoria/swap 768 MiB y un CPU. Sin worker permanente ni servicios externos.
Dependencias fijadas: sklearn 1.7.2, scipy 1.16.2, joblib 1.5.2, threadpoolctl 3.6.0.
Artefactos numéricos JSON; no archivos pickle ni carga de modelos arbitrarios.

Panel Angular: cuatro casos nuevos, **50/50** componentes en 28,52 s, build
31,535 s. Tras recuperar RAM, Playwright pasó solicitud HTTP con worker auxiliar,
candidato persistido, aprobación, activación, inferencia, recarga, desactivación,
restauración y móvil; cero errores JavaScript y 32 notas exactas. Los intentos
anteriores por debajo de 1,5 GiB terminaron antes de solicitar trabajos.

Resultado experimental real (semilla 42): entrenamiento 342 ejemplos/57 alumnos;
evaluación temporal 48 ejemplos/16 alumnos, cero alumnos compartidos. Precisión
0,900; recall 0,750; F1 0,818; Brier 0,0866; matriz [[35,1],[3,9]]. Baseline
mayoritario F1 0; Brier 0,25; matriz [[36,0],[12,0]]. Etiquetas sintéticas por regla,
sin eficacia institucional acreditada. Inferencia: 240 casos ficticios, 0,636 s
observados incluyendo UI/HTTP; no acredita carga productiva. Parámetros/modelo
numéricos, métricas y fuente persistidos en PostgreSQL; prueba privada
`config/local/risk-ui.result.json`. Segundo candidato por API (semilla 43) aprobado:
precisión/recall/F1 0,9545; Brier 0,0343; matriz [[25,1],[1,21]]. Misma separación
342/48 ejemplos y 57/16 alumnos. El entrenamiento no cambió el modelo activo;
activación explícita y rollback al anterior conservaron íntegra su metadata y las
32 notas. Evidencia privada `risk-retraining.result.json`.

Integración BI: conteos, cobertura, versión y fecha demostrativos en sección
independiente; 50/50 componentes en 23,05 s y build 25,897 s. Recorrido
visual de esa sección **aprobado** con 240 casos ficticios separados de 32 notas,
cobertura/versionado/fecha, filtros, vacío, error/reintento y móvil; cero errores JS.
Consulta integrada observada 0,581 s. Entrenamiento API sin Edge reserva mínimo 1 GiB y comparte
el límite duro del backend 768 MiB; navegador/entrenamiento combinado mantiene
1,5 GiB. Empaquetado desde caché sin instalación usa cap 256 MiB, serializado.

Regresión focalizada posterior: 8/8 PG en 15,19 s (siete BI + nuevo caso de modo
institucional/umbrales invertidos/motivo vacío rechazados). Total de este bloque:
22 casos focalizados distintos (7 BI + 15 IA): 19 usan PostgreSQL y tres son
pruebas puras de features/suficiencia, aprobados por etapas; no es una ejecución
conjunta nueva. Cuatro unittest de infraestructura y Ruff scripts/BI/IA aprobaron.

Aceptación funcional local verificada. Auditoría preliminar de 37 commits/476
versiones de archivos: sin coincidencias de claves/JWT/rutas privadas; revisión
manual de datos JSON, configuración, SQL y logo completada (fixture ficticia,
resultados anonimizados, logo sin personas). Los filtros automáticos no sustituyen
esa revisión. No se publican archivos `config/local`, XLSX, datasets ni artefactos.
Auditoría final anterior al push: 39 commits/478 versiones, sin coincidencias;
los únicos cambios siguientes son esta referencia documental y el roadmap.
Backup local `backup/pre-bi-ai-a6495ce` y `backup/pre-main-bi-ai`.
Desarrollo publicado por push normal; [PR #2](https://github.com/wesarzein/Paideia/pull/2)
conserva el estado de CI e integración. Squash condicionado al CI remoto aprobado.

Inventario Docker final: solo tres servicios del laboratorio autorizados activos.
Se retiraron cuatro contenedores de build Angular creados en este bloque, detenidos,
sin volúmenes y con montaje fuente de solo lectura; artefactos y logs preservados
en `config/local`. Imágenes/cachés, respaldos, volumen sintético, volumen institucional
y recursos previos se conservaron. Backend actualizado desde caché sin reinstalar
dependencias ni repetir el build Angular.
