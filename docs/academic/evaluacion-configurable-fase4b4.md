# Fase 4B.4: evaluación configurable

**Actualización segunda laptop, 09/10/2026:** PostgreSQL real y migraciones 0012–0014
validados en el laboratorio único, con correcciones mínimas de 0014. Pasaron las tres
pruebas PostgreSQL pendientes y los casos de revisiones/API, permisos, restauración,
snapshots e integración XLSX. Angular compiló con Node 24 y lockfile. **Pendiente
recorrido visual** por memoria insuficiente y decisiones institucionales sobre cálculo
oficial. No declarar cierre integral. Véase
[evidencia y resultados actuales](validacion-segunda-laptop-fase4b.md).

Los estados de PostgreSQL/compilación pendientes del texto siguiente describen la
sesión anterior; esta actualización los sustituye sin borrar sus antecedentes.

Fecha de actualización: 09/10/2026. Rama: `dev/phase4b4-evaluation-offline`.
Docker permaneció pausado y no se utilizó la instalación institucional. Esta fase no
cierra [4B.3](importacion-institucional-fase4b3.md): continúa pendiente comprobar la
persistencia de sus diez notas después de reiniciar el laboratorio sintético.

La integración posterior del contexto manual, la identidad de criterios y el plan de
validación consolidado están en [Fase 4B.5](integracion-estabilizacion-fase4b5.md).

## Estado comprobable

| Componente | Implementación | Evidencia disponible |
| --- | --- | --- |
| Competencias | Clave estable, nombre, orden, estado y asociación opcional con criterios | Pruebas de dominio locales |
| Criterios | Alta, edición, orden por bloque, desactivación lógica, opcionalidad, peso, encabezado Excel y vínculo al componente legado | Pruebas de dominio locales |
| Ponderaciones | Rango 0–100 y cálculo relativo compatible con componentes actuales; denominador positivo por bloque | Pruebas de dominio locales; no se impuso suma 100 |
| Fórmulas | Intérprete decimal restringido para `+`, `-`, `*`, `/`, `SUM`, `MEAN`, `MIN`, `MAX` y `ROUND`; referencias, ciclos y complejidad validados | Pruebas de seguridad y aritmética |
| Plantilla institucional | Dos bloques de cuatro semanas, cinco criterios por bloque, promedios mensuales/final y literal existente | Pruebas con estructura anonimizada de 4B.3 |
| Versionado | Revisiones anexadas por curso/periodo con estado, versión anterior, autor, fecha, motivo, JSON y SHA-256 | SQLite aislado; PostgreSQL pendiente |
| Concurrencia | Versión base obligatoria y unicidad `(course_id, period_id, version)`; una carrera devuelve conflicto | Lógica y 409 probados localmente; carrera PostgreSQL preparada |
| Publicación | Guardar borrador, publicar y restablecer la plantilla generan revisiones inmutables; ninguna acción recalcula notas previas | API FastAPI con SQLite aislado |
| Permisos | Lectura para roles existentes; escritura para admin/coordinator y docente asignado; director solo lectura | Docente permitido/denegado y director denegado probados localmente |
| Historial de notas | Las notas nuevas pueden guardar la revisión publicada; el snapshot registra ID, versión y huella; el vínculo es inmutable | SQLite aislado; trigger PostgreSQL pendiente |
| Importación Excel | Si existe una publicación, el importador relaciona bloque y encabezado con esa versión; rechaza criterios sin correspondencia | Prueba sintética local; recorrido XLSX/PG pendiente |
| Interfaz | Editor dentro de Cursos para competencias, criterios, orden, estados, pesos, fórmulas, vista previa, borrador, publicación, historial y restauración | Código preparado; compilación y navegador pendientes |

Las migraciones 0012 y 0013 no se modificaron. La nueva migración
`0014_evaluation_configuration_revisions` es aditiva: crea el historial, añade a
`grade_records` una referencia nullable a la revisión y reemplaza el trigger de 0012
para incluir esa referencia en snapshots nuevos. El downgrade restaura la función de
0012 antes de retirar exclusivamente las estructuras de 0014. Se generó SQL offline de
upgrade y downgrade, pero la migración no se ejecutó en PostgreSQL.

## Contratos implementados

- `GET /courses/{course_id}/evaluation-template`: plantilla institucional para un periodo.
- `POST /courses/{course_id}/evaluation-preview`: validación y cálculo sin persistencia.
- `GET /courses/{course_id}/evaluation-configurations/current`: última revisión o plantilla
  predeterminada con versión cero.
- `GET /courses/{course_id}/evaluation-configurations/active`: última revisión publicada o
  plantilla predeterminada; los borradores no afectan el registro de notas.
- `GET /courses/{course_id}/evaluation-configurations/versions`: historial completo del ámbito.
- `POST /courses/{course_id}/evaluation-configurations/drafts`: nueva revisión de borrador.
- `POST /courses/{course_id}/evaluation-configurations/publish`: publicación explícita.
- `POST /courses/{course_id}/evaluation-configurations/restore-institutional`: nueva
  publicación basada en la plantilla, sin eliminar el historial.

Cada escritura exige `expected_version` y un motivo. El documento se valida otra vez en
backend. Las revisiones no se actualizan ni eliminan: ORM y migración PostgreSQL las
protegen. La restricción única resuelve el caso en que dos solicitudes observan la misma
versión; una debe recargar antes de reintentar.

## Reglas que se mantienen

- Vacío es `None`; cero explícito es una nota válida. Un criterio obligatorio ausente
  deja incompleto el resultado de la previsualización.
- Los pesos siguen siendo relativos. Cambiar un peso no reescribe automáticamente una
  fórmula; la interfaz muestra ambos resultados para revisión.
- `ROUND` admite de cero a cuatro decimales con redondeo decimal de mitad hacia arriba.
  No se ejecutan fórmulas Excel, macros, `eval`, atributos, índices ni código arbitrario.
- Los documentos admiten hasta 64 criterios, 32 competencias y 32 fórmulas. Las
  expresiones admiten hasta 512 caracteres, 128 nodos y profundidad 20.
- Los criterios usan claves estables; cambiar la posición no cambia su identidad.
- No se asignan fechas ni bimestres desde la fecha de importación. El importador usa el
  bloque y el contexto académico que el docente confirmó en 4B.3.
- Los snapshots anteriores permanecen sin referencia de revisión (`NULL`) y conservan
  exactamente la evidencia capturada por 0012. No se intenta reconstruir historia desconocida.

## Validación realizada sin Docker

Se aprobaron **32 pruebas locales** en 1,60 segundos en la ejecución final: 26 del motor/documento y seis de
persistencia/API con SQLite aislado. Cubren seguridad de fórmulas, ceros y vacíos,
competencias, criterios, orden, desactivación, pesos, serialización, revisiones, edición
obsoleta, permisos, publicación/restauración, conservación del snapshot y mapeo del
Excel contra la publicación vigente.

También se comprobó:

- compilación bytecode del backend;
- generación OpenAPI de las ocho rutas de plantilla, vista previa y
  configuración/versionado;
- cadena Alembic con 0014 como `head`;
- generación offline del SQL PostgreSQL de upgrade y downgrade de 0014;
- Ruff para los módulos puros, la migración y las pruebas nuevas;
- codificación UTF-8 y balance básico de las plantillas TypeScript;
- `git diff --check`.

No se repitieron las 92 pruebas anteriores. No se ejecutaron PostgreSQL, Docker,
navegador ni compilación Angular. Node y las dependencias frontend no están instalados
en el entorno local disponible.

## Ejecución PostgreSQL preparada

`backend/tests/unit/test_evaluation_configuration_postgresql.py` queda omitido salvo que
exista `PAIDEIA_TEST_POSTGRES_URL`. Reutiliza una salvaguarda que admite el laboratorio
phase2 o, con selección explícita adicional, esquemas aislados de `phase4b3ui`. En una
única ejecución posterior comprobará:

1. upgrade y downgrade real de 0014 en un esquema sintético;
2. una sola ganadora entre dos publicaciones concurrentes;
3. trigger append-only del historial;
4. captura e inmutabilidad de la revisión en el snapshot de una nota nueva.

En esa misma ejecución deben correrse las regresiones PostgreSQL de 0012, 0013 y el
importador institucional, seguidas por compilación frontend y un recorrido de navegador.

## Límites pendientes

- La persistencia y los triggers no están validados en PostgreSQL real.
- La interfaz no está compilada ni probada en navegador; sus contratos HTTP sí aparecen
  en OpenAPI, pero eso no acredita el recorrido visual.
- La integración 4B.5 ya añadió bimestre y bloque institucional explícitos al registro
  manual, selecciona criterios de la publicación activa y captura su peso en el snapshot.
  Esta ruta todavía requiere compilación Angular y ejecución integrada con PostgreSQL;
  no se infirió el contexto académico desde la fecha ni desde el mes calendario.
- El Excel sí aporta bloque explícito y ya valida su correspondencia con la configuración
  publicada. Falta ejecutar el XLSX completo con PostgreSQL para acreditar guardado,
  idempotencia y consulta con 0014.
- La política institucional para opcionales incompletos y la relación normativa entre
  pesos y fórmulas sigue pendiente de confirmación antes de convertir la previsualización
  en cálculo oficial de resultados.

El código está preparado para la validación integrada, pero 4B.4 continúa **implementada
parcialmente y no validada de extremo a extremo**.
