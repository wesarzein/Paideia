# Reproducción segura de Fase 4A

Estos comandos son para entornos **sintéticos independientes**. No usar `.env` institucional, `docker-compose.yml`, `docker-compose.recovery.yml`, el padrón real ni volúmenes conocidos de producción. No ejecutar los scripts de auditoría sobre la instalación actual.

Los scripts tienen guards de proyecto, usuario/base y puertos. Una ejecución exitosa del harness puede contener discrepancias: revisar `status` de cada comprobación, no solo el exit code. Los resultados de esta sesión están versionados; XLSX/PDF, contexto y credenciales permanecen privados.

## 1. Recorridos API y navegador

En PowerShell desde la raíz, sobre un proyecto de auditoría sin datos:

```powershell
python scripts/setup_dev.py phase4a --port 14204
docker compose --env-file config/local/phase4a.env -f docker-compose.environment.yml -f docker-compose.audit.yml build backend frontend
docker compose --env-file config/local/phase4a.env -f docker-compose.environment.yml -f docker-compose.audit.yml run -T migrate
docker compose --env-file config/local/phase4a.env -f docker-compose.environment.yml -f docker-compose.audit.yml run -T seed
docker compose --env-file config/local/phase4a.env -f docker-compose.environment.yml -f docker-compose.audit.yml up -d --wait backend frontend
```

El archivo privado no se sobrescribe. Si ya existe una configuración generada para este proyecto, conservarla y verificar que corresponde a este entorno antes de omitir el primer comando. El override usa tmpfs, sin volumen ni inicializadores institucionales. No omitirlo para estos recorridos. Arrancar un tmpfs detenido crea una base vacía y obliga a migrar/cargar de nuevo; no confundir esto con persistencia productiva ni usar el patrón sobre datos importantes.

Preparar las réplicas a partir del archivo proporcionado, montado **solo lectura**. No modificar el original ni publicar sus nombres. El generador admite únicamente la estructura inspeccionada y valida igualdad de fórmulas, encabezados y rangos combinados:

```powershell
$auditDir = Join-Path $env:LOCALAPPDATA 'Paideia/audit-phase4a'
New-Item -ItemType Directory -Force -Path $auditDir | Out-Null
docker run --network none --mount 'type=bind,src=C:\Users\sanch\Downloads\REGISTRO DE NOTA 1EROA SEC.xlsx,dst=/private/source.xlsx,readonly' --mount "type=bind,src=$($PWD.Path)\scripts\audit_phase4a,dst=/audit,readonly" --mount "type=bind,src=$auditDir,dst=/results" --entrypoint python paideia-dev-phase4a-backend /audit/prepare_excel.py /private/source.xlsx /results
docker compose --env-file config/local/phase4a.env -f docker-compose.environment.yml -f docker-compose.audit.yml run -T --env PYTHONPATH=/app --entrypoint python --volume "$($PWD.Path)\scripts\audit_phase4a:/audit:ro" --volume "${auditDir}:/results" backend /audit/api_audit.py
```

El script API crea identidades/cursos/notas ficticios. Probar un formato plano cuando el parser institucional falla es un ensayo **separado**, no una sustitución del requisito. Ejecutar el API audit una vez por base fresca; no se incluyen comandos de borrado/reset para repetirlo.

Instalar Playwright en un venv nuevo dentro del directorio privado. No instalar globalmente ni usar el perfil personal del navegador. En esta sesión se usó Edge headless; su ejecutable debe existir. En otro equipo ajustar únicamente la ruta a un navegador disponible compatible y validar nuevamente:

```powershell
python -m venv "$auditDir/venv"
& "$auditDir/venv/Scripts/python.exe" -m pip install playwright==1.55.0
$auditBrowser = 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
& "$auditDir/venv/Scripts/python.exe" scripts/audit_phase4a/browser_audit.py --private $auditDir --config config/local/phase4a.env --browser $auditBrowser
& "$auditDir/venv/Scripts/python.exe" scripts/audit_phase4a/browser_extra_audit.py --private $auditDir --browser $auditBrowser
docker compose --env-file config/local/phase4a.env -f docker-compose.environment.yml -f docker-compose.audit.yml run -T --env PYTHONPATH=/app --entrypoint python --volume "$($PWD.Path)\scripts\audit_phase4a:/audit:ro" --volume "${auditDir}:/results" backend /audit/supplemental_audit.py
```

El navegador solo permite solicitudes a `localhost:14204`, usa un contexto nuevo y guarda exportaciones sintéticas privadas. Los scripts extra/suplementario dependen del API audit y deben ejecutarse una vez, en ese orden. Las capturas públicas de resultados no incluyen contraseñas, tokens ni filas de estudiantes.

## 2. Persistencia después de reiniciar PostgreSQL

Usar **otro proyecto vacío**, con volumen nuevo desechable y exclusivamente sintético; tmpfs no permite validar esa conservación. Estos nombres están fijados por el guard. Si ya existe el volumen de la prueba anterior, **no borrarlo ni repetir la carga sobre él**: para otra ejecución elegir un proyecto/alias nuevo y adaptar el guard del harness de pruebas de manera explícita, o usar un Docker de laboratorio independiente. No reutilizar un volumen cuyo origen no se conoce.

```powershell
python scripts/setup_dev.py phase4apersist --port 14205
docker compose --env-file config/local/phase4apersist.env -f docker-compose.environment.yml build backend frontend
docker compose --env-file config/local/phase4apersist.env -f docker-compose.environment.yml run -T migrate
docker compose --env-file config/local/phase4apersist.env -f docker-compose.environment.yml run -T seed
docker compose --env-file config/local/phase4apersist.env -f docker-compose.environment.yml up -d --wait backend frontend
python scripts/audit_phase4a/persistence_audit.py --private $auditDir
```

La prueba agrega dos notas (una importada y un cero manual), asistencia, seguimiento y un componente; obtiene inventario read-only; reinicia **solo** PostgreSQL/backend/frontend de `paideia-dev-phase4apersist`; exige igualdad completa del inventario y verifica lectura de los registros. No migra al reiniciar.

## 3. Regresión y evidencia

La regresión anterior usa exclusivamente PostgreSQL sintético y un archivo de entorno explícito sin secretos:

```powershell
$env:PAIDEIA_TEST_IMAGE = 'paideia-dev-phase4a-backend'
docker compose --env-file .env.test.example -p paideia-phase4a-regression -f docker-compose.tests.yml run -T migrate
docker compose --env-file .env.test.example -p paideia-phase4a-regression -f docker-compose.tests.yml run -T tests
```

El inventario de rutas puede obtenerse por `GET /openapi.json` **dentro del backend sintético** y guardarse como `route-inventory.json` en el directorio privado; no confundirlo con un recorrido de UI. La colección pública exige los archivos enumerados de esta sesión, el inventario de rutas y la estructura Excel. Nunca recoge `browser-context.json`, `.env`, XLSX, PDF o dumps:

```powershell
python scripts/audit_phase4a/collect_results.py --private $auditDir
```

`collect_results.py` conserva el commit de referencia y el resultado de regresión de esta sesión; para documentar una nueva versión, actualizar explícitamente esa metadata y las comprobaciones de protección de base, no copiar afirmaciones sin haberlas ejecutado.

Al terminar, detener únicamente esos proyectos mediante `stop` con sus archivos de entorno/Compose explícitos. No usar `down -v`, `prune`, reset, borrados o restauraciones sobre bases existentes. Se conservan archivos privados y el volumen sintético de persistencia; los resultados temporales de tmpfs son desechables.
