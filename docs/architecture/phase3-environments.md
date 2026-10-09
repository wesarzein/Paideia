# Fase 3: instalación reproducible, colaboración y despliegue

## Separación de entornos

La instalación institucional recuperada usa `docker-compose.yml` y su override de recuperación. Su `.env`, volumen `paideia_paideia_postgres_data`, contenedores e imágenes existentes se conservan. **No aplicar la configuración nueva sobre esa instalación durante esta fase.**

Los nuevos entornos usan exclusivamente `docker-compose.environment.yml`, un archivo privado elegido explícitamente y un nombre de proyecto propio. No hay `container_name` fijo. Cada proyecto obtiene sus propias imágenes, redes, volumen PostgreSQL, credenciales y puerto de frontend. PostgreSQL y backend no publican puertos; Nginx publica el frontend en loopback y reenvía `/api/` al backend mediante la red interna.

| Entorno | Código y configuración | Datos |
| --- | --- | --- |
| Desarrollo individual | Checkout/rama por desarrollador; archivo privado propio | Base independiente y catálogo sintético reproducible |
| Integración compartida | Versión revisada por PR; secretos del operador | Una API y una base común, preferiblemente sintética o anonimizada y autorizada |
| Producción | Versión aprobada; secretos y operación institucional | Base privada persistente con respaldos verificados |

Git comparte código, contratos, dependencias y migraciones. No replica registros de PostgreSQL. Dos bases de desarrollo divergen deliberadamente; para probar colaboración entre usuarios se necesita un entorno de integración común. No compartir un dump institucional como procedimiento normal de alta de desarrolladores.

## Alta desde cero

Requisitos: Git, Docker/Compose y Python 3.12 para el generador, sin instalar dependencias de la aplicación en el host. Clonar el repositorio y situarse en su raíz. Usar un alias propio y un puerto libre; estos ejemplos no corresponden a la instalación institucional:

```text
python scripts/setup_dev.py dev1 --port 14200
docker compose --env-file config/local/dev1.env -f docker-compose.environment.yml build
docker compose --env-file config/local/dev1.env -f docker-compose.environment.yml run -T migrate
docker compose --env-file config/local/dev1.env -f docker-compose.environment.yml run -T seed
docker compose --env-file config/local/dev1.env -f docker-compose.environment.yml up -d backend frontend
```

`migrate` inicia su PostgreSQL vacío y aplica Alembic explícitamente. `seed` es opcional: agrega tres estudiantes ficticios y dos cursos, sin notas reales, y puede repetirse sin duplicaciones. Rechaza bases que no sean `paideia_dev_*`, otro usuario de base, ausencia de opt-in o un entorno distinto de desarrollo. Ninguno de esos procesos se ejecuta al arrancar el backend.

Abrir `http://localhost:14200`. La API está en `http://localhost:14200/api/v1`, y su documentación en `/docs` solo por acceso interno al backend; no se publica su puerto. Las credenciales administrativas sintéticas están en `config/local/dev1.env`, que no se imprime ni se versiona. No usar esa cuenta ni datos sintéticos en producción.

Para otro checkout o desarrollador en el mismo equipo:

```text
python scripts/setup_dev.py dev2 --port 14201
```

Repetir los comandos anteriores sustituyendo `dev1` por `dev2`. En equipos diferentes pueden usar el mismo puerto. El generador se niega a sobrescribir configuraciones existentes y valida alias/ruta/puerto; no lee ni cambia `.env`. En Unix establece permisos 0600; en Windows conservar el archivo dentro del perfil privado del usuario y aplicar ACL del equipo si se requiere. No guardar secretos productivos en carpetas sincronizadas.

Si no se instala Python en el host, el generador puede ejecutarse con la imagen Python fijada, montando únicamente este checkout. Ejemplo PowerShell:

```powershell
docker run --network none --mount "type=bind,src=$($PWD.Path),dst=/workspace" -w /workspace python:3.12.7-slim@sha256:60d9996b6a8a3689d36db740b49f4327be3be09a21122bd02fb8895abb38b50d python scripts/setup_dev.py dev1 --port 14200
```

La imagen debe estar disponible localmente o descargarse antes de ejecutar ese comando sin red. No montar un directorio personal más amplio.

## Operación y cambios de código

Usar siempre el mismo `--env-file` y `-f` para el proyecto elegido:

```text
docker compose --env-file config/local/dev1.env -f docker-compose.environment.yml ps
docker compose --env-file config/local/dev1.env -f docker-compose.environment.yml logs --tail 50 backend
docker compose --env-file config/local/dev1.env -f docker-compose.environment.yml build backend frontend
docker compose --env-file config/local/dev1.env -f docker-compose.environment.yml up -d backend frontend
```

Los contenedores ejecutan el código compilado/copiado en la imagen, sin hot reload. Recompilar tras cambios; no basta con editar archivos en el host. Las migraciones se revisan y aplican por separado, nunca como efecto de reiniciar la API. Revisar respaldos y revisiones pendientes antes de ejecutar `migrate` sobre una base que ya tenga información importante.

Si se usa Make, indicar siempre `ENV_FILE=config/local/dev1.env`: por ejemplo, `make build ENV_FILE=config/local/dev1.env`. Los targets `migrate` y `seed` son explícitos; `stop` conserva el volumen. `backend-test` usa exclusivamente el Compose sintético. No existe un target de borrado.

Para apagar un entorno individual sin borrar su volumen, usar `stop` con sus dos argumentos de configuración. No usar `down -v`, resets, prune ni restauraciones sobre una base compartida. El padrón institucional sigue siendo una importación explícita y privada; no participa en el bootstrap de desarrollo.

Para desarrollo Angular nativo, `npm start` usa `proxy.conf.json` y reenvía `/api` a `localhost:8000`; provisionar antes un backend de desarrollo independiente. La SPA usa rutas API relativas y no necesita recompilarse para cambiar el dominio del despliegue.

## Dependencias, migraciones y CI

- Las bases Python, Node, Nginx y PostgreSQL del entorno nuevo están fijadas por digest. Actualizarlas deliberadamente, con revisión y pruebas; los paquetes de sistema instalados mediante apt aún dependen de la disponibilidad del repositorio, por lo que no se afirma reproducibilidad binaria bit a bit.
- `backend/requirements.txt` conserva las dependencias directas. `requirements.lock` fija también las transitivas, capturadas del runtime Linux/Python 3.12 que ya pasó las pruebas. Docker y CI usan ese lock; para Windows nativo se mantiene `requirements.txt` porque hay paquetes específicos de Linux en el lock.
- El frontend usa `npm ci --legacy-peer-deps` y `package-lock.json`, sin resolver versiones nuevas en cada build. Node de CI y Docker está alineado en la serie 24, y Python en 3.12.
- Angular se actualizó de 20.3.0 a 20.3.33 dentro de la misma serie, tras detectar avisos de seguridad, incluido el [aviso oficial GHSA-hh8m-fm6v-7cvg](https://github.com/angular/angular/security/advisories/GHSA-hh8m-fm6v-7cvg). Compilación y runner se verificaron; queda pendiente la regresión funcional visual. `npm audit --omit=dev` reportó cero vulnerabilidades en esta comprobación; el audit completo todavía reporta 18 (3 moderadas, 10 altas y 5 críticas) en herramientas/transitivas de desarrollo. Evaluar actualizaciones de CLI/build y Vitest con pruebas separadas antes de declarar cerrada la revisión de dependencias. No se ejecutó `audit fix --force` ni se migró de versión mayor.
- Alembic sigue siendo la fuente del esquema. No se agregaron revisiones ni se corrigieron las 19 diferencias de nulabilidad detectadas previamente.
- El CI del backend valida scripts de configuración, lint de los archivos de infraestructura/persistencia y la suite completa en PostgreSQL desechable. El lint global de módulos anteriores queda pendiente: no se hicieron refactorizaciones masivas para cambiar formato de otros módulos.
- Los workflows se prepararon y se validaron localmente mediante sus comandos. Su ejecución remota y protecciones de ramas requieren publicar/revisar cambios en una fase autorizada; no se realizó push ni merge.

Ejecutar pruebas aisladas desde la raíz:

```text
python -m unittest discover -s scripts -p "test_*.py"
docker compose --env-file .env.test.example -p paideia-ci-local -f docker-compose.tests.yml build
docker compose --env-file .env.test.example -p paideia-ci-local -f docker-compose.tests.yml run -T migrate
docker compose --env-file .env.test.example -p paideia-ci-local -f docker-compose.tests.yml run -T tests
```

Esos comandos usan un archivo de entorno vacío versionado y un nombre de proyecto explícito para impedir la lectura implícita de `.env` y la herencia del nombre institucional. No omitir `--env-file` ni `-p`. El Compose no publica puertos ni monta datos privados. PostgreSQL usa tmpfs y autenticación trust únicamente en su red sintética interna. La suite anterior contiene limpieza de registros de prueba; nunca ejecutarla contra la base institucional. El nombre de proyecto de pruebas debe ser distinto del de desarrollo/institución.

## Trabajo paralelo del equipo

1. Mantener checkouts o worktrees separados y ramas de alcance pequeño. Nunca editar simultáneamente el mismo directorio compartido.
2. Cada desarrollador genera su archivo privado y usa su base propia; no versionar `.env`, `config/local`, padrones, respaldos o credenciales.
3. Revisar cambios de contrato frontend/API y lockfiles juntos. No resolver conflictos de lock con una edición manual de números de versión: regenerar deliberadamente y ejecutar build/pruebas.
4. Antes de crear una migración, consultar las heads y el trabajo paralelo. No renombrar o editar una revisión aplicada para resolver un conflicto. Si dos ramas generan heads, revisar un merge Alembic y validar ambos caminos en una base sintética antes de integrar; no aplicar a producción durante esa resolución.
5. Compartir información editable mediante la misma API de integración, no copiando bases entre PCs como si se replicaran continuamente. No usar producción como base de experimentos.

## Preparación de integración/producción

`.env.production.example` es una plantilla, no un archivo listo para desplegar. El operador debe elegir un proyecto/volumen nuevos, generar secretos propios, configurar la URL PostgreSQL coherente con usuario/base/contraseña y los dominios HTTPS reales, y almacenar el archivo fuera de Git. Los valores de ejemplo hacen fallar la validación del backend en `production`/`staging`. No activar `ALLOW_SYNTHETIC_SEED`.

Usar `docker-compose.environment.yml` con ese archivo y aplicar migraciones como operación revisada antes de arrancar servicios. Solo el frontend publica loopback; instalar un proxy TLS en el servidor para el dominio institucional y reenviar al puerto del frontend. PostgreSQL y API se mantienen en red interna. Esta fase no contrató infraestructura, cambió DNS, obtuvo certificados ni publicó el sistema.

La URL de la base duplica parámetros de PostgreSQL por compatibilidad; si se cambia una credencial, actualizar ambos valores coherentemente. No rotar contraseñas cambiando solo un archivo y esperando que un volumen PostgreSQL existente se reprovisione.

Faltan para declarar producción preparada operativamente: servidor/dominio/TLS; responsable de secretos, monitoreo y backups; copia cifrada fuera del equipo y retención; restauración programada y rollback probado en el destino; auditoría funcional y de permisos completa. El entorno no sustituye esas verificaciones.

En el destino validar también cabeceras y redirecciones HTTPS a través del proxy TLS, límites de importación y resolución del backend tras recrearlo. Los healthchecks y el login local no acreditan esa cadena de despliegue.

## Evidencias y pendientes de esta fase

- Se instalaron proyectos independientes `paideia-dev-phase3a` y `paideia-dev-phase3b` con bases y secretos propios, sin padrón real, usando puertos 14200/14201.
- El procedimiento final corregido se ejecutó también en `paideia-dev-phase3c`, puerto 14202, con un volumen nuevo: configuración generada, build, once migraciones y seed sintético.
- En C se verificaron login, tres alumnos ficticios, redirección que conserva el puerto y healthchecks. Después de reiniciar exclusivamente sus tres servicios, el inventario completo de PostgreSQL coincidió exactamente con el anterior. El proxy resuelve el backend mediante DNS de Docker y conserva `Host` con su puerto.
- Las once migraciones se aplicaron desde cero y la carga sintética repetida no produjo altas ni modificaciones adicionales.
- La suite completa pasó 52 pruebas en PostgreSQL y el generador pasó cuatro pruebas de protección de configuración e independencia. Se verificaron login y consulta de alumnos mediante el proxy en ambos entornos; un curso creado en A no apareció en B y el JWT de A fue rechazado en B.
- La compilación del frontend y su prueba existente pasaron. Esa prueba solo comprueba el runner y no acredita los flujos visuales completos.
- La verificación HTTP detectó y corrigió la separación de redes necesaria para publicar el frontend en Docker Desktop, el dominio válido de la cuenta sintética y la carga de modelos requerida por el importador independiente. Las correcciones solo se aplicaron a código/entornos sintéticos.
- Una inspección de solo lectura comparó las 15 tablas institucionales con el inventario posterior a la recuperación: ningún conteo, huella de filas ni huella de columnas cambió; revisión `0011_evidence_types`. Los servicios institucionales no se reiniciaron ni reconstruyeron en Fase 3.
- Al finalizar se detuvieron solo los proyectos sintéticos A/B/C y los PostgreSQL de CI creados en esta fase para liberar recursos. Los volúmenes de desarrollo, configuraciones e imágenes se conservaron; el PostgreSQL de pruebas usa tmpfs y debe volver a migrarse al iniciar una instancia nueva. La instalación institucional sigue saludable. No se ejecutó borrado de volúmenes, push ni merge.
- Las opciones de evaluación flexible y la importación Excel quedan para la [auditoría académica posterior](../academic/evaluacion-configurable-y-auditoria.md), con el Excel real como referencia privada. No se implementaron IA ni BI.

## Archivos de Fase 3

Configuración: `docker-compose.environment.yml`, `docker-compose.tests.yml`, `.env.production.example`, `.env.test.example`, `.env.example`, `.gitignore`, `Makefile`, `scripts/setup_dev.py`, `scripts/test_setup_dev.py`, `database/seeds/roster.synthetic.json`.

Backend: `Dockerfile`, `.dockerignore`, `requirements.lock`, `app/core/config.py`, `app/main.py` (CORS), `app/seed_dev.py`, `tests/unit/test_environment_config.py`, y la importación del registro completo de modelos en `app/services/school_roster.py`. El resto de la protección del padrón, el importador, el inspector y las migraciones preservan los cambios de Fase 1/2; no son implementaciones nuevas de Fase 3.

Frontend: `Dockerfile`, `.dockerignore`, `package.json`, `package-lock.json`, `nginx.conf`, `proxy.conf.json`, `src/environments/environment.ts`. Integración/documentación: ambos workflows CI, `README.md`, `DEVELOPMENT.md`, `CONTRIBUTING.md`, `ARCHITECTURE.md` y esta guía. El documento académico se conserva como alcance de auditoría futura.
