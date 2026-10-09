# Fase 4B.2: importación académica sin duplicados

Corrección autorizada del guardado de calificaciones. Se conserva [Fase 4B.1](integridad-historica-fase4b1.md), respaldada en el commit local `885c4f9`, y se trabaja en `dev/phase4b2-idempotent-imports`. Referencias: [auditoría 4A](auditoria-fase4a.md), [matriz EX-D/EV-I](auditoria-fase4a-matriz.md) y [requisitos configurables](evaluacion-configurable-y-auditoria.md).

No se modifica el parser institucional, la organización de exámenes/bimestres, IA/BI ni la base institucional. El XLSX institucional sigue pendiente de Fase 4B.3: esta corrección del guardado no demuestra que ese archivo pueda interpretarse de extremo a extremo.

## Defecto reproducido

El endpoint `POST /imports/grades/commit` preparaba un `GradeRecord` por fila y ejecutaba `add_all`, sin consultar coincidencias. La única unicidad era el UUID generado para cada registro. En un PostgreSQL desechable con migraciones hasta 0012, la prueba nueva importó diez notas, repitió el conjunto y falló con **20 registros en vez de 10**. La imagen `paideia-phase4b2-baseline-backend` conserva esa reproducción anterior a la corrección.

## Identidad y compatibilidad

Una nota se identifica por la combinación de:

1. UUID del alumno, curso y periodo.
2. UUID del componente/criterio, o ausencia explícita de componente.
3. Nombre de evaluación y tipo de evidencia normalizados por las validaciones existentes.
4. Fecha de evaluación.

El puntaje, observación, usuario que importa, nombre/hash del archivo y pesos **no** forman parte de la identidad. Dos notas de igual valor con distinta evaluación, fecha o criterio siguen siendo diferentes. Los nombres conservan mayúsculas/acentos; no hay coincidencia aproximada. Se eliminan espacios externos como en los endpoints existentes. La representación PostgreSQL es un arreglo JSON completo convertido a texto, sin usar un hash para decidir igualdad.

El sistema actual no tiene una entidad `Evaluation` ni un ID de intento. Dos actividades con exactamente los mismos metadatos anteriores no pueden distinguirse: hay que precisar su nombre, fecha o criterio antes de importarlas. Los valores predeterminados existentes se conservan; no inventan una identidad académica adicional.

Si una fila omite el componente, se buscan primero notas con el resto de dimensiones. Una sola coincidencia permite conservar su asociación; varias coincidencias se declaran ambiguas. Para una nota nueva, un componente del curso cuyo nombre coincide exactamente con el tipo de evidencia puede aportar su UUID; un componente inactivo impide el alta. No se infieren competencias ni reglas del Excel. Un `component_id` explícito debe pertenecer al curso; `null` explícito representa una nota sin componente, mientras una celda vacía se considera sin identificación del criterio.

La revisión devuelve el componente resuelto y la interfaz lo incluye al confirmar. Así se relacionan importaciones con notas manuales identificables, sin cambiar su configuración histórica ni confundir varios criterios. Las notas manuales siguen usando los endpoints actuales; PostgreSQL rechaza altas o reasignaciones que ocupen una identidad ya reservada, y la API devuelve 409 con rollback.

## Flujo de revisión y confirmación

Se reutilizan la carga por selección/arrastre, vista previa editable, filtros y pantalla existentes:

1. `/imports/grades/preview` mantiene la lectura actual del archivo.
2. El botón **Revisar registros existentes** llama a `/imports/grades/review` con las filas corregidas, curso y periodo. Comparte validación con el guardado; no escribe datos.
3. Cada fila se clasifica como nueva, idéntica, diferente, ambigua o repetida dentro del archivo. Se muestran puntaje/observación guardados y propuestos.
4. Las diferencias requieren **Conservar nota existente** o **Confirmar actualización**. Sin decisión, el servidor responde 409 y revierte el lote. Las nuevas se insertan y las idénticas se omiten.
5. Actualizar requiere una confirmación HMAC ligada al actor, identidad, propuesta y estado de la nota revisada. Cambios posteriores en la nota/propuesta invalidan la confirmación; deben revisarse otra vez. La decisión de conservar nunca sustituye datos.
6. Editar una celda o cambiar curso/periodo invalida la revisión en la interfaz. El servidor vuelve a validar identidad, permisos y estado al confirmar; no confía en el estado mostrado por el navegador.
7. El resultado informa `processed`, `imported`, `updated`, `skipped`, `rejected`. Una repetición idéntica devuelve cero altas y omite los registros existentes sin cambiar sus timestamps.

Las actualizaciones autorizadas cambian exclusivamente puntaje/observación y conservan ID, asociaciones y los dos snapshots de 0012. Se registra `grade_import_update` en `audit_logs`, con actor, ID, puntaje anterior/nuevo y señal de cambio de observación, en la misma transacción. Esto no implementa el historial completo de todas las ediciones/borrados manuales; tampoco conserva el texto anterior completo de observaciones en ese historial.

Los permisos existentes permanecen: importación por admin/docente/coordinador en API, y verificación de asignación del docente por cada alumno/curso. La ruta UI mantiene los roles previos admin/docente; no se amplía acceso al coordinador. Un usuario no autorizado no puede utilizar una confirmación ajena ni omitir la comprobación de asignaciones.

## Garantías PostgreSQL: migración 0013

`0013_grade_import_identity` depende de `0012_grade_assessment_snapshot`; **no modifica 0012**.

- Añade `grade_record_identities`, cuya clave primaria reserva la combinación académica completa. Un FK diferido referencia la nota y permite reservar su identidad dentro de la misma transacción de INSERT.
- Un trigger de `grade_records` reserva identidades para todos los escritores, incluidas altas manuales, SQL directo e importaciones. La unicidad de PostgreSQL impide dos altas simultáneas con la misma identidad.
- El importador adquiere locks transaccionales por identidad base en orden estable y bloquea las notas encontradas antes de comprobar diferencias. Dos confirmaciones idénticas terminan con diez altas totales; dos actualizaciones diferentes revisadas contra el mismo estado producen una ganadora y un 409 para la propuesta obsoleta.
- Si un escritor manual gana después de revisar un alta, la restricción rechaza el lote importado y lo revierte. No se reintenta una sustitución automáticamente: debe repetirse la revisión.
- Cambiar metadatos de una nota a una identidad libre conserva las acciones existentes y libera su reserva anterior cuando corresponde a ese registro. Borrar una nota mediante una acción existente elimina su reserva individual por FK; esta fase no ejecuta borrados ni cambia esas funcionalidades.
- Un error valida/revierte el lote completo. Las reservas y los registros de auditoría también pertenecen a esa transacción.

La creación inicial toma un lock `SHARE ROW EXCLUSIVE` sobre `grade_records` hasta completar el backfill y activar el trigger en la misma transacción. Así una escritura concurrente no puede quedar entre el inventario inicial y la protección nueva. Utiliza datos existentes sin UPDATE/DELETE de notas. Las identidades únicas quedan asociadas a su nota; las repetidas se reservan con `grade_id=NULL`, sin escoger un ganador. Se verificó la migración desde 0012 con dos notas diferentes del mismo grupo: IDs, valores, relaciones, timestamps y snapshots quedaron exactamente iguales.

El downgrade se rechaza porque quitar las reservas deshabilitaría la protección. Revisar el plan de reversión y el respaldo antes de cualquier despliegue; una restauración puede perder escrituras posteriores y no está autorizada en esta fase.

## Duplicados históricos: estrategia pendiente de autorización

No se elimina ni consolida automáticamente ningún grupo preexistente. El importador bloquea los grupos ambiguos, incluso si sus puntajes coinciden.

Para una futura revisión autorizada:

1. Respaldar y verificar la restauración antes de considerar cambios institucionales.
2. Inventariar reservas con `grade_id IS NULL` y sus registros asociados, en acceso restringido. Conservar IDs, relaciones, snapshots y evidencia de origen; no exportar datos personales a documentación pública.
3. Determinar con el docente si son actividades distintas mal identificadas o repeticiones reales. No decidir por igualdad de puntajes.
4. Preparar una previsualización de la resolución y su efecto en promedios. Las actividades distintas requieren metadatos diferenciadores confirmados; una repetición real requiere una política de conservación/versionado y trazabilidad antes de excluirla del cálculo.
5. Autorizar y registrar la resolución por grupo, sin borrados automáticos. Las reservas ambiguas son deliberadamente conservadoras y no se liberan por sí solas: si los registros se reidentifican, hay que revisar también la reserva anterior mediante un procedimiento autorizado.

## Pruebas ejecutadas

**75 pruebas backend aprobadas** en PostgreSQL 17 aislado: 59 anteriores más 16 casos nuevos, con 48 advertencias preexistentes de deprecación. Además, **16 pruebas del padrón aprobadas en SQLite en memoria**, sin usarlo como sustituto de las garantías PostgreSQL. Migraciones desde base vacía hasta 0013 aprobadas. Nuevos casos:

| Caso | Resultado comprobado |
| --- | --- |
| Primera importación/repetición de diez notas | 10 altas, luego 0; permanecen 10 registros idénticos |
| Nuevas + existentes + repetidas dentro del archivo | 1 alta y 11 omisiones; valores contradictorios de la misma identidad rechazan el lote |
| Nota corregida por docente | Se muestra diferencia; sin decisión devuelve 409; conservar mantiene la corrección |
| Actualización confirmada | Cambia solo lo solicitado; conserva snapshots; genera auditoría |
| Estado/propuesta/confirmación/actor alterados | Cuatro casos rechazados con 409 |
| Compatibilidad manual e identidades diferentes | Coincidencia manual detectada; evaluaciones, fechas, tipos y componentes diferentes se conservan separados; ambigüedad requiere criterio |
| Errores de validación y diferencias sin resolver | Sin altas parciales ni sustituciones |
| Dos confirmaciones idénticas concurrentes | Ambas 200; altas totales 10 |
| Dos propuestas de actualización concurrentes | Una 200, otra 409; una sola auditoría |
| Escritura SQL duplicada y rollback | Restricción rechaza el alta y revierte un cambio anterior de puntaje en la transacción |
| Escritor manual posterior a la revisión | Importación 409 y rollback de todo el lote; permanece únicamente la nota rival |
| Docente asignado/no asignado y rol no permitido | Docente asignado importa y actualiza tras revisar; no autorizado rechazado |
| Duplicados previos a 0013 | Migración no cambia notas; reserva ambigua y guardado bloqueado |
| Timestamp histórico nulo permitido por el esquema anterior | Revisión y actualización autorizada funcionan sin sustituir snapshots ni alterar el esquema previo |

La prueba de reasignación de 4B.1 se adaptó para usar un criterio libre, manteniendo todas sus comprobaciones de snapshot. Su variante anterior apuntaba a un criterio ya ocupado por otra nota de la misma evaluación, que ahora debe producir un conflicto de identidad. No se suprimieron las pruebas históricas.

**Seis comprobaciones reales en Edge headless**, con login UI/JWT, frontend Nginx, FastAPI y PostgreSQL en volumen sintético independiente `paideia-dev-phase4b2final_postgres_data`:

1. Selección CSV sintético, vista previa/revisión y primera importación de diez notas.
2. Reimportación por UI: cero altas, diez omisiones y mismos registros.
3. Corrección guardada conservada mediante decisión explícita.
4. Edición de propuesta invalida revisión; nueva revisión y actualización confirmada conserva snapshot.
5. Reinicio real de PostgreSQL, backend y frontend sintéticos: inventario completo, esquema y contenido iguales antes/después.
6. Reimportación después del reinicio: diez registros, sin recapturar pesos aunque el peso vigente cambió de 2 a 7.

La suite de integración usa dependencias de autenticación sustituidas para los casos de rol, manteniendo permisos/asignaciones reales de la base sintética; el recorrido navegador usa autenticación real de admin. No se afirma que se haya probado el navegador con todos los roles ni el Excel institucional.

Los primeros ensayos de navegador fallaron por selectores del harness y por exigir ausencia de diferencias de modelo que ya eran conocidas. Se corrigieron las pruebas y se utilizó un proyecto nuevo, conservando las bases anteriores. La ejecución final completó las seis comprobaciones. El inspector mantiene 19 discrepancias de nulabilidad en timestamps, iguales a la referencia previa de recuperación; no se corrigen fuera de alcance. La tabla nueva no tiene discrepancias y no hay constraints inválidas.

Ruff de los archivos nuevos y `git diff --check` aprobados. El frontend compiló correctamente. La inspección institucional fue únicamente `REPEATABLE READ, READ ONLY`: 15 tablas con conteos, huellas y esquema iguales a la referencia privada, revisión **0011**, sin aplicar 0012 ni 0013.

## Reproducción segura

Backend, desde la raíz del repositorio, con un proyecto nuevo que no se reutilice con datos ajenos:

```powershell
$env:PAIDEIA_TEST_IMAGE = 'paideia-phase4b2-tests-backend'
docker compose --env-file .env.test.example -p paideia-phase4b2-tests -f docker-compose.tests.yml build tests
docker compose --env-file .env.test.example -p paideia-phase4b2-tests -f docker-compose.tests.yml run migrate
docker compose --env-file .env.test.example -p paideia-phase4b2-tests -f docker-compose.tests.yml run tests
```

Recorrido UI/reinicio: generar un alias **nuevo** `phase4b2...` y puerto libre 14206–14219. No reutilizar la base final para repetir la carga; el harness exige que no haya notas. La configuración local permanece ignorada y sus secretos no se muestran:

```powershell
python scripts/setup_dev.py phase4b2nueva --port 14210
docker compose --env-file config/local/phase4b2nueva.env -f docker-compose.environment.yml build backend frontend
docker compose --env-file config/local/phase4b2nueva.env -f docker-compose.environment.yml run migrate
docker compose --env-file config/local/phase4b2nueva.env -f docker-compose.environment.yml run seed
docker compose --env-file config/local/phase4b2nueva.env -f docker-compose.environment.yml up -d --wait backend frontend
& "$env:LOCALAPPDATA/Paideia/audit-phase4a/venv/Scripts/python.exe" scripts/verify_grade_import_identity.py --config config/local/phase4b2nueva.env --browser 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
```

El último comando requiere el venv privado de Playwright utilizado en 4A y Edge. En otro equipo preparar un venv privado equivalente siguiendo [reproducción 4A](reproduccion-fase4a.md). El script valida proyecto, base, usuario y puerto, crea su CSV en memoria y solo reinicia ese Compose sintético. No incluye borrados/reset ni montaje de datos institucionales.

## Archivos y siguientes tareas

- `backend/app/services/grade_import_identity.py`: comparación, confirmaciones y transacción.
- `backend/app/endpoints/imports.py`: revisión y guardado compartiendo validación.
- `backend/app/endpoints/grades.py`: 409/rollback para conflictos manuales.
- `backend/app/models/academic.py`: modelo de reservas; snapshots conservados.
- `backend/migrations/versions/0013_grade_import_identity.py`: garantía PostgreSQL y compatibilidad histórica.
- `backend/tests/unit/test_grade_import_identity.py`: nuevos casos focalizados.
- `backend/tests/unit/test_grade_assessment_history.py`: reasignación a criterio libre para conservar su propósito.
- `frontend/src/app/core/services/api.service.ts`: contratos de revisión/resultados.
- `frontend/src/app/features/imports/placeholder.page.ts`: comparación, decisiones e invalidación de revisión, conservando modos, filtros y carga editable.
- `scripts/verify_grade_import_identity.py`: prueba real de UI/API y reinicio sintético.
- `docs/academic/evaluacion-configurable-y-auditoria.md` y este documento: contexto y resultados.

Pendiente de autorización: despliegue coordinado de 0012/0013 con respaldo verificado y revisión de grupos históricos; no desplegar el backend nuevo sobre 0011/0012 sin 0013. La migración tiene operaciones DDL/bloqueo y reserva identidades existentes, por lo que necesita una ventana planificada. Garantías concurrentes requieren PostgreSQL; SQLite no reemplaza estas pruebas.

La siguiente tarea será **Fase 4B.3**, parser del Excel institucional, únicamente después de autorización. Debe generar identidades claras por evaluación/criterio/fecha, conservar la estructura real y utilizar esta misma revisión/confirmación, sin introducir otra importación ni saltar decisiones del docente.
