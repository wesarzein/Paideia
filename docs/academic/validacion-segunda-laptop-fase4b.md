# Validación académica en la segunda laptop

Fecha: 09/10/2026 (America/Lima). Rama: `dev/phase4b5-academic-stabilization`.
Punto de partida: `3c3a87b`. Este informe actualiza los pendientes de 4B.3–4B.5;
las evidencias de la laptop anterior se conservan como antecedentes.
Correcciones, pruebas y verificador: commit local `b156d12`.

## Resultado y alcance

| Fase | Estado comprobado | Límite pendiente |
| --- | --- | --- |
| 4B.3 | Cierre técnico de persistencia/importación en el laboratorio nuevo: diez notas, corrección explícita, IDs y snapshots estables, reinicio PostgreSQL e idempotencia | No acredita el volumen de la laptop anterior; este recorrido fue HTTP/API, no una nueva prueba de navegador |
| 4B.4 | PostgreSQL real, publicación/versionado, carrera concurrente, permisos, restauración, snapshots y compilación Angular verificados | Editor sin recorrido visual nuevo; política institucional de opcionales y precedencia pendiente |
| 4B.5 | Contexto manual explícito, configuración publicada, identidad de criterios, compatibilidad Excel e historia estable verificados en PostgreSQL/API | Matriz manual y editor sin recorrido visual nuevo; no declarar cierre integral |

## Laboratorio y protección

Se comprobaron antes de escribir las etiquetas Compose, el archivo de configuración,
el volumen montado, la conexión efectiva y `current_database()/current_user`:

- proyecto único: `paideia-dev-phase4b3ui`;
- configuración: `config/local/phase4b3ui.env`;
- Compose: exclusivamente `docker-compose.environment.yml`;
- destino: `postgres / paideia_dev_phase4b3ui / paideia_dev`;
- volumen: `paideia-dev-phase4b3ui_postgres_data`;
- PostgreSQL 17: **cero tablas en public** antes del primer intento;
- frontend: `127.0.0.1:14211`; API/PostgreSQL sin puertos publicados.

La instalación `paideia`, sus contenedores, `.env` y volumen anterior no se iniciaron
ni utilizaron. No hubo push, merge, prune, limpieza de volúmenes ni uso de datos reales.
Los contenedores de operaciones y esquemas UUID se conservaron para inspección.

## Migraciones y correcciones mínimas

La primera ejecución desde cero falló en 0014 y PostgreSQL revirtió la transacción
completa: su identificador de 39 caracteres excedía `alembic_version.version_num(32)`.
0014 ahora amplía esa columna a 64 sin renombrar su revisión. El downgrade conserva
la amplitud, porque Alembic actualiza el identificador después de ejecutar la función
de downgrade. No se modificaron 0012/0013.

Las tres pruebas PostgreSQL iniciales pasaron, pero las regresiones de notas legadas
detectaron un segundo defecto: el trigger de 0014 consultaba un `record` sin estructura
cuando no había revisión publicada. Ahora asigna la estructura mediante SELECT incluso
cuando la referencia es NULL. También se rechaza explícitamente un bloque NULL en notas
configurables, incluido el acceso SQL directo.

El esquema público ya había recibido 0014 antes de detectar ese trigger. Se verificó
que aún tenía **cero calificaciones** y se reemplazó únicamente la función corregida,
en una transacción del laboratorio. No se hizo downgrade de public ni se alteraron notas.
La imagen backend final contiene la migración corregida para futuras instalaciones.

Se corrigió una prueba histórica que seleccionaba columnas del modelo 0014 mientras
su esquema todavía estaba en 0012: compara las columnas realmente existentes antes
del upgrade. La fixture de revisiones/API ahora reutiliza la salvaguarda PostgreSQL y
permite ejecutar esos casos en esquemas UUID, manteniendo SQLite como opción predeterminada.

## Pruebas reales

**34 casos PostgreSQL distintos aprobados** (las repeticiones por corrección no se
cuentan como casos adicionales):

- 26 casos entre `test_evaluation_configuration_postgresql.py`,
  `test_grade_assessment_history.py` y `test_grade_import_identity.py`.
  Tras el arreglo del trigger hubo 25 aprobados y un error de importación `text`
  en la prueba histórica corregida; ese caso pasó en la ejecución siguiente.
- 7 casos de `test_evaluation_revision_persistence.py` sobre PostgreSQL.
- 1 caso XLSX completo de 160 entradas:
  `test_complete_template_160_inputs_persist_reimport_and_snapshots`.

La última ejecución de las tres pruebas PostgreSQL pendientes y el caso XLSX completo
pasó **4/4 en 14,01 s**, incluida la nueva comprobación SQL de bloque NULL. La ejecución
de la prueba histórica corregida y siete casos de revisiones pasó **8/8 en 23,13 s**.
Las 92 pruebas anteriores no se repitieron.

Se comprobaron instalación limpia hasta head; preservación de datos previos al aplicar
0012 y 0013; ciclo **0014 → 0013 → 0014** con nota legada en un esquema UUID; una sola
publicación ganadora; protección append-only e identidad distinta por criterio.
Todos los downgrades de pruebas ocurrieron en esquemas UUID, nunca en public.

Además, **7/7 pruebas de revisiones/API en SQLite** pasaron en 1,55 s para verificar
la compatibilidad de la fixture modificada. Ruff focalizado y `git diff --check` pasaron.
Las advertencias de Alembic/Starlette observadas no se corrigieron en esta tarea.

## Diez notas reproducidas y reinicio

`scripts/verify_academic_lab_api.py` ejecuta el flujo HTTP real contra Uvicorn desde
el contenedor backend, sin navegador ni puertos adicionales. Antes de escribir valida
el destino; en el host verifica proyecto, Compose y volumen. El inicio rechaza notas
preexistentes y nunca resetea el laboratorio.

Se utilizó `institutional_fixture.workbook_bytes`: diez entradas, 150 vacíos y 64
referencias derivadas. Se comprobaron rechazo de nota 25/código externo, correspondencia
explícita, corrección a cero, revisión y confirmación. Se guardaron exactamente diez
notas con valores `0,12,14,16,18,20,20,20,20,20`; luego se editó la primera a 17,
se comprobó conservación y se confirmó expresamente su actualización a **5**, manteniendo
ID y snapshot. Reimportar omitió las diez sin cambios.

El reinicio final afectó **exclusivamente PostgreSQL**. Se compararon las diez notas,
todas las filas API del laboratorio y el inventario público completo, incluidas reservas
de identidad, conteos y huellas de filas/columnas. Resultado: `passed: true`.

- SHA-256 de las diez notas: `062b5c8a74c0a6ce1dd400e2e875406382d658809fdf92c450cc372fba52f308`.
- SHA-256 del inventario: `acfeed872bd6c2b3899b4b02d7009ce894b6ef52689919f196ae12778462d7f7`.

Un primer intento de comparación quedó invalidado por escrituras simultáneas del
recorrido de configuración; no se usa como evidencia. Se repitió sin escrituras
concurrentes y pasó. Las salidas JSON se conservan en `config/local`, fuera de Git.
La propuesta XLSX corregida también se conserva allí, para sobrevivir a recreaciones
del backend. La reimportación se verificó nuevamente con la imagen backend final.

## Integración configurable

En el segundo curso sintético se comprobó mediante HTTP:

1. Borrador v1 sin configuración activa ni cambio de notas; publicación obsoleta devuelve 409.
2. Publicación v2 con peso 3; borrador v3 con peso 9 sin alterar la configuración activa.
3. XLSX: diez notas nuevas vinculadas a v2 y peso publicado 3, no al borrador.
4. Nota manual sin contexto rechazada; guardado con bimestre, bloque, criterio,
   evaluación y fecha explícitos vinculado a v2.
5. Publicación posterior v4 y restauración v5 sin cambios de IDs, notas ni snapshots;
   reimportación del XLSX omite diez sin duplicación.

El laboratorio conserva **21 notas**: las diez originales y once del curso configurable.
Las reglas institucionales pendientes permanecen sin resolver y las fórmulas siguen
siendo previsualización, sin convertirse en cálculo oficial.

## Angular y recursos

Se descartaron para el build las dependencias locales Angular 22/TypeScript 6.
El contenedor de compilación usó el digest Node 24 del Dockerfile, Node **24.21.0**,
`npm ci --legacy-peer-deps --no-audit --no-fund`, heap 512 MiB, máximo de un trabajador,
un CPU y límite total/swap de **768 MiB**. Instaló 965 paquetes desde el lockfile y
`npm run build` pasó en **29,441 s**, sin cambios frontend necesarios.

Se preservó el contenedor y su caché. El artefacto compilado se copió a un directorio
privado y se empaquetó con el Nginx fijado por digest; no se ejecutó un segundo build
Angular. Backend y frontend no se construyeron simultáneamente. La imagen backend
reutilizó las dependencias existentes, verificadas contra todo `requirements.lock`,
añadiendo únicamente `xlrd==2.0.2` y copiando el código actual. Su CMD inicia Uvicorn
sin migraciones automáticas.

Los tres servicios sintéticos quedaron saludables; `/api/v1/health/db` responde `ok`
por el proxy en el puerto 14211. Eso **no acredita la interfaz**.
Se preparó Playwright 1.55.0 en `config/local/browser-venv`, sin perfil personal ni
instalación global. Con aproximadamente **0,93 GiB libres** después del build no se
inició Edge: editor, matriz, consulta visual y recorrido XLSX visual siguen pendientes.

## Continuación ejecutable

Sobre el laboratorio conservado, sin reconstruir ni reinicializar:

```powershell
python -B scripts/verify_academic_lab_api.py --stage reimport
```

`--stage import` y `--stage configuration` son etapas iniciales y deliberadamente
rechazan repetir el escenario poblado. `--stage persistence` permite repetir el
reinicio protegido cuando un cambio relevante lo justifique; ejecutarlo sin otras
escrituras ni pruebas concurrentes.

El siguiente trabajo es el recorrido esencial de navegador con memoria suficiente:
competencias/criterios/orden/estado → pesos/fórmulas/vista previa → borrador → publicación
→ matriz con bimestre/bloque/fecha → consulta → versión posterior → historia estable.
Comprobar además la consulta y reimportación visual del XLSX existente, sin borrar datos.

Después del cierre visual, el siguiente bloque definido por la matriz de 4A es el
**ámbito y los permisos de consultas/resúmenes/reportes** (REQ-04 y REQ-33, P0), con
pruebas focalizadas por rol y curso. No iniciar módulos nuevos, IA o BI. La política
de opcionales incompletos y precedencia entre fórmulas/ponderaciones requiere confirmación
institucional antes de habilitar resultados oficiales; las migraciones institucionales
siguen fuera de esta autorización.
