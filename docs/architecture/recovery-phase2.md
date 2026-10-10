# Recuperación controlada de Paideia — Fase 2

## Resultado comprobado

- Los cambios de la Fase 1 permanecen en el checkout. No hubo push, merge ni modificación del padrón privado o de `.env`.
- `paideia-postgres` y `paideia-backend` siguen detenidos con salida 255. Ambos terminaron el 08/10/2026 a las 20:22:46 de Lima, con menos de un milisegundo de diferencia, sin OOM ni error de runtime registrado en `docker inspect`. El frontend sigue activo.
- Los logs no explican la terminación. Un error anterior sobre `course_assignments.teacher_name` fue seguido por arranque y peticiones correctas. Una interrupción del motor Docker/VM es una inferencia; no se confirmó su causa con los logs disponibles o los eventos de Windows consultados.
- Volumen original: `paideia_paideia_postgres_data`, local, PostgreSQL 17, aproximadamente 64 MiB. Su control indicaba `in production`: no había cierre limpio. No había enlaces simbólicos/tablespaces externos y ningún contenedor activo lo montaba para escribir.
- Se copió el volumen completo, incluido WAL, con montaje de solo lectura. Las huellas de todos sus archivos seguían iguales al finalizar; los servicios originales nunca se arrancaron.

## Respaldo privado verificado

Ubicación local fuera del repositorio y de OneDrive:

```text
%LOCALAPPDATA%\Paideia\backups\phase2-20261009-015922
```

La fecha del nombre usa UTC. El directorio tiene ACL restringida al usuario actual y SYSTEM. Contiene información institucional; no adjuntar sus archivos a Git, chats ni servicios públicos.

- `pgdata.tar`: copia física de 67 420 160 bytes; `SHA256SUMS`: huella verificada. Se compararon todas las huellas de archivos originales con la extracción antes de arrancar la copia.
- Restauración física: volumen independiente `paideia_phase2_restore`, contenedor `paideia-phase2-restored`, sin red ni puertos. PostgreSQL 17.11 completó recuperación WAL y quedó listo. El mensaje de fin de WAL fue seguido por recuperación completa, sin PANIC/FATAL.
- `paideia.dump`: respaldo lógico generado desde la copia recuperada. Se restauró sin errores en una segunda base dentro de ese contenedor aislado. Cantidades y huellas de todas las filas, por tabla, coincidieron con la copia recuperada. Su SHA-256 está en `paideia.dump.sha256`.
- `integrity-private.txt`, `database-inventory-private.json` y `source-files-before.sha256`: evidencia privada de integridad y estado; no incluyen filas nominales, pero se mantienen junto al respaldo.

El respaldo permite recuperar el estado encontrado. No demuestra que nunca se perdieran datos antes de esta fase. Hay una sola copia local en este equipo; falta una segunda copia cifrada fuera del equipo y una política de retención.

## Estado de la copia y migraciones

La copia recuperada está en `0011_evidence_types`, cabeza única del checkout. No hay revisiones pendientes en ese estado; la igualdad final de los archivos originales respalda que corresponde al volumen aún detenido.

Inventario agregado de la copia: 139 estudiantes, 37 cursos, 27 asistencias, cero calificaciones y cero seguimientos. No se consultaron ni mostraron nombres. El responsable aclaró que las notas actuales se registran en Excel externos: cero calificaciones en PostgreSQL puede ser completamente normal y no es por sí solo error ni evidencia de pérdida. Esta fase no importa esos archivos ni modifica notas.

No hubo restricciones no validadas ni referencias huérfanas en ninguna de las claves foráneas inspeccionadas. El esquema migrado y la copia presentan 19 diferencias de nulabilidad en `created_at`/`updated_at`: la base permite NULL donde los modelos no. No se corrigieron ni se creó una migración nueva. La comprobación no sustituye una auditoría académica completa ni una comprobación física exhaustiva de páginas, cuyos checksums estaban desactivados.

Riesgos del arranque normal:

1. El Dockerfile ejecuta `app.migrate` antes de Uvicorn. No usarlo para recuperación hasta revisar el esquema.
2. `app.migrate` aplica `upgrade head` y puede hacer `stamp 0002` ante tablas heredadas, sin validar todo ese esquema.
3. La revisión 0011 transforma valores de `evaluation_type`; no debe aplicarse inadvertidamente a una base distinta.
4. FastAPI aún agrega roles faltantes y, si se configuran las dos variables INITIAL_ADMIN, puede crear un administrador. No importa el padrón. Antes de iniciar, revisar estas condiciones; si implican altas no previstas, detenerse y decidirlas explícitamente.

## Validación sintética

- Las 11 migraciones se aplicaron a una base PostgreSQL vacía e independiente. Cada prueba adicional usó un esquema nuevo migrado, sin `create_all`, DROP ni limpieza de filas.
- 16 pruebas de persistencia pasaron en PostgreSQL y 16 en SQLite. Incluyen arranque sin padrón, importación repetida sin duplicados, ausencias y estados manuales preservados, identidades estables, historial relacionado y rollback de un fallo de integridad referencial.
- FastAPI/Uvicorn arrancó con datos sintéticos omitiendo migraciones. Después de reiniciar exclusivamente ese backend de prueba, `/health` y `/health/db` devolvieron HTTP 200 y coincidieron cantidades, huellas de filas, huellas de columnas y revisión.
- Se corrigió un fallo comprobado de Alembic al configurar URLs con `%` codificado: `migrations/env.py` escapa los porcentajes para ConfigParser. No altera migraciones ni datos.
- Ruff pasó en los archivos de esta fase. Los avisos de deprecación de FastAPI/TestClient/Alembic quedan pendientes.

Entorno reproducible, desde la raíz, sin usar el Compose habitual:

```powershell
docker compose -p paideia-phase2-isolated -f docker-compose.phase2-tests.yml up -d testdb
docker compose -p paideia-phase2-isolated -f docker-compose.phase2-tests.yml run tests
```

La imagen `paideia-backend:latest` debe existir con sus dependencias; el código de pruebas se monta en solo lectura. El archivo no carga `.env`, no monta datos institucionales ni publica puertos. La autenticación trust se limita a esa red interna sintética. PostgreSQL usa tmpfs: su contenido de prueba es temporal.

La validación realizada usó `paideia-phase2-testdb` y la red interna `paideia_phase2_testnet`. Ese contenedor sintético quedó activo. El API de prueba y la copia institucional restaurada quedaron detenidos; no se eliminó ningún contenedor o volumen.

## Procedimiento propuesto — NO ejecutado sobre servicios actuales

Requiere autorización para arrancar/recrear los servicios originales y permitir la recuperación WAL en el volumen actual. Trabajar desde la raíz de Paideia, con los usuarios temporalmente fuera de la aplicación. No usar `up` general, `down -v`, `prune`, reset ni restaurar encima del volumen original.

1. **Verificar respaldo y estado.** Comprobar las huellas guardadas, el volumen asociado al contenedor y que el checkout conserva la Fase 1. Si el volumen cambió desde esta copia, obtener y validar otro respaldo antes de continuar. Revisar las variables INITIAL_ADMIN sin mostrar sus valores y la presencia de los seis roles; no permitir aprovisionamiento imprevisto.

2. **Arrancar únicamente PostgreSQL existente.** Esto escribirá recuperación WAL sobre el volumen original; esa operación aún no está autorizada ni ejecutada:

   ```powershell
   docker start paideia-postgres
   docker exec paideia-postgres pg_isready -U paideia_user -d paideia
   ```

   Los nombres de usuario/base son los comprobados en esta instalación. Si hay FATAL/PANIC o no alcanza disponibilidad, detenerse; no resetear WAL ni borrar `postmaster.pid`.

3. **Reconstruir solo backend e inspeccionar sin arrancar FastAPI ni Alembic.** El override conserva conexiones, puertos y montajes legítimos y reemplaza únicamente el comando de arranque:

   ```powershell
   docker compose -f docker-compose.yml -f docker-compose.recovery.yml build backend
   $recoveryPath = Join-Path $env:LOCALAPPDATA 'Paideia\backups\phase2-20261009-015922'
   docker compose -f docker-compose.yml -f docker-compose.recovery.yml run --no-deps -T --entrypoint python backend -m app.inspect_database | Set-Content -Encoding UTF8 (Join-Path $recoveryPath 'current-before.json')
   ```

   Comprobar que el comando terminó con código 0 y JSON válido. `app.inspect_database` usa una transacción REPEATABLE READ, READ ONLY y no importa `app.main`. Comprobar revisión 0011, ausencia de huérfanos y conservación de cantidades/huellas frente a la evidencia privada. Si hay otra revisión, tablas faltantes o diferencias inesperadas, no ejecutar `app.migrate`: detenerse y revisar.

4. **Iniciar solo el backend actualizado, sin migraciones.** Después de confirmar que el aprovisionamiento de roles/admin no agregará registros inesperados:

   ```powershell
   docker compose -f docker-compose.yml -f docker-compose.recovery.yml up -d --no-deps backend
   Invoke-RestMethod http://localhost:8000/api/v1/health
   Invoke-RestMethod http://localhost:8000/api/v1/health/db
   ```

   No importar el padrón durante la recuperación. Repetir la inspección de solo lectura y comparar con `current-before.json`; las tablas académicas deben permanecer iguales.

5. **Verificar el frontend existente.** Abrir `http://localhost:4200`, iniciar sesión con una cuenta existente y comprobar peticiones a `http://localhost:8000/api/v1` y filtros en modo consulta. No crear ni editar datos reales durante esta verificación. La integración visual real queda pendiente; no se afirma validada por los healthchecks.

6. **Reinicio controlado, solo con autorización.** Guardar otro inventario privado antes. Con usuarios fuera del sistema:

   ```powershell
   docker stop paideia-backend
   docker restart paideia-postgres
   docker exec paideia-postgres pg_isready -U paideia_user -d paideia
   docker start paideia-backend
   Invoke-RestMethod http://localhost:8000/api/v1/health/db
   ```

   Esperar disponibilidad de PostgreSQL antes de iniciar backend. El backend debe haber sido recreado con el override del paso 4; verificar su comando, que debe ser Uvicorn sin `app.migrate`. Repetir inventario y comparar cantidades y huellas; consultar desde otro usuario autorizado. Si no coinciden, no restaurar ni revertir automáticamente: detenerse y conservar evidencias.

No se considera la recuperación actual completada hasta efectuar estos pasos autorizados. La restauración aislada y el reinicio sintético reducen el riesgo, pero no reemplazan esa validación.

## Recuperación ejecutada tras la autorización del responsable

El responsable autorizó continuar la recuperación y aclaró que no se debe investigar la ausencia de calificaciones como pérdida. El procedimiento anterior queda como registro de los pasos preparados; su ejecución técnica se completó con estos resultados:

- Se verificaron nuevamente las huellas SHA-256 de ambos respaldos y las huellas de todos los archivos del volumen detenido antes de arrancarlo. Coincidían con la copia verificada.
- Se inició el contenedor PostgreSQL existente sobre el mismo volumen. Completó recuperación WAL, sin FATAL/PANIC. No se restauró encima del volumen original.
- Se reconstruyó la imagen del backend con los cambios del checkout y se inspeccionó la base real en modo READ ONLY, sin FastAPI ni Alembic. Coincidieron cantidades, huellas de todas las filas y huellas de columnas con el respaldo. La revisión seguía en `0011_evidence_types`.
- Los seis roles necesarios ya existían y no estaban configuradas las variables de alta inicial del administrador. Se inició el backend con `docker-compose.recovery.yml`; su comando contiene solo Uvicorn, sin `app.migrate`.
- El inventario completo coincidió antes y después del arranque: no hubo altas, bajas ni cambios de registros.
- La imagen recién construida, sin montar código desde el host, pasó las 16 pruebas focalizadas contra PostgreSQL sintético independiente. No se ejecutaron pruebas de escritura sobre la base real.
- Se detuvo el backend, se reinició PostgreSQL y se volvió a iniciar el backend existente. Coincidieron cantidades, huellas de todas las filas, estructura y revisión antes y después de ese reinicio controlado.
- PostgreSQL, backend y frontend quedaron activos y saludables. `/api/v1/health`, `/api/v1/health/db` y `http://localhost:4200` respondieron HTTP 200. Una petición de health con el origen del frontend también respondió correctamente. La sesión autenticada y los flujos visuales completos siguen pendientes; estas comprobaciones no los certifican.
- Evidencias privadas adicionales: `current-before.json`, `current-after-start.json`, `current-before-restart.json`, `current-after-restart.json` y `recovery-validation.json`, en la carpeta del respaldo.

Para posteriores recreaciones del backend durante esta recuperación, utilizar ambos archivos Compose:

```powershell
docker compose -f docker-compose.yml -f docker-compose.recovery.yml up -d --no-deps backend
```

Un `docker compose up` que recree el backend usando únicamente el archivo habitual volvería a seleccionar el comando que aplica migraciones. La configuración local `.env` y el Compose habitual se conservaron.

## Prioridad posterior: importación Excel

La futura auditoría académica debe incorporar el [requisito de evaluación configurable por curso y periodo](../academic/evaluacion-configurable-y-auditoria.md), incluidas competencias, criterios, ponderaciones, fórmulas seguras, versiones y preservación histórica. Ese documento contiene el contexto técnico y las tareas de auditoría; la fase actual solo lo documenta y mantiene la prioridad del entorno colaborativo y despliegue.

Las calificaciones institucionales actuales están en archivos Excel externos. La auditoría funcional posterior debe verificar el archivo real de referencia, incluidas hojas, fórmulas, encabezados y estructura; arrastrar y soltar; interpretación de los criterios de cada curso; revisión y corrección por el docente; confirmación previa a cualquier persistencia; y almacenamiento permanente en PostgreSQL. Debe respetar evaluaciones cada cuatro semanas y bimestres de ocho semanas, conservando funcionalidades adicionales existentes. Esta recuperación no auditó ese flujo de extremo a extremo ni importó archivos académicos reales.
