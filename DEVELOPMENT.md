## Desarrollo y operaciones

El alta de integrantes usa exclusivamente `docker-compose.environment.yml` y un archivo privado por desarrollador. GitHub comparte codigo y migraciones, nunca bases, secretos o padrones reales. La instalacion anterior y su volumen permanecen independientes.

Con Git, Python 3 y Docker Desktop disponibles, desde un clon de `main`:

```powershell
python scripts/setup_dev.py dev1 --port 14200
docker compose --env-file config/local/dev1.env -f docker-compose.environment.yml build backend
docker compose --env-file config/local/dev1.env -f docker-compose.environment.yml build frontend
python scripts/dev_environment.py config/local/dev1.env initialize
```

Construir las imagenes por separado con RAM suficiente. Node 24, Angular 20.3.33 y TypeScript 5.8.3 proceden del lockfile y Docker. `initialize` comprueba proyecto, volumen y destino efectivo, migra hasta head y carga solo el seed sintetico en un catalogo vacio. Acceso: `http://localhost:14200`; credenciales propias en `config/local/dev1.env`, fuera de Git.

Uso cotidiano: `python scripts/dev_environment.py config/local/dev1.env start`, `status` o `stop`. Para actualizar: `git pull --ff-only`, construir backend y frontend por separado y ejecutar `python scripts/dev_environment.py config/local/dev1.env update`. El arranque no migra, importa padrones ni borra datos. `update` verifica el destino antes de aplicar migraciones. No repetir `initialize` sobre un catalogo poblado.

En esta laptop sigue autorizado solo `config/local/phase4b3ui.env`, proyecto `paideia-dev-phase4b3ui`: sustituir el alias de los ejemplos sin crear otro laboratorio. Aislamiento: [Fase 3](docs/architecture/phase3-environments.md).

### Restablecer la contraseña de administrador

La contraseña existente no se puede recuperar en texto plano. Para cambiarla, desde la raíz del proyecto ejecuta en una terminal interactiva:

```powershell
docker compose --env-file config/local/dev1.env -f docker-compose.environment.yml exec backend python -m app.reset_admin_password
```

El comando solicita el correo de la cuenta administradora y pide dos veces la nueva contraseña sin mostrarla ni incluirla en el historial de comandos. Requiere un mínimo de 12 caracteres y solo actualiza una cuenta cuyo rol sea administrador. No expongas la contraseña en el chat, en comandos ni en archivos del repositorio.

### Versiones del entorno Docker

| Servicio | Imagen o base | Acceso local |
| --- | --- | --- |
| Backend | Python `3.12-slim` + `build-essential` | `http://localhost:8000` |
| Base de datos | `postgres:17-alpine` | `localhost:5432` |
| Frontend | `node:24-alpine` | `http://localhost:4200` |

---

### Comandos útiles para el día a día

### Esquema y migraciones de base de datos

Alembic es la única fuente de cambios del esquema. No uses `Base.metadata.create_all()` ni agregues `CREATE TABLE`/`ALTER TABLE` al arranque de FastAPI o a scripts de inicialización de PostgreSQL. Los scripts de `database/init` se reservan para extensiones requeridas antes de que arranque la API. La importación explícita del padrón requiere un esquema previamente provisionado y no ejecuta migraciones.

Cuando cambies modelos SQLAlchemy, desde `backend` crea una revisión y revísala antes de subirla:

```powershell
alembic revision --autogenerate -m "describe_schema_change"
alembic upgrade head
```

El Dockerfile nuevo inicia Uvicorn sin Alembic. Las imágenes anteriores a Fase 3 pueden conservar el comando que migraba automáticamente; la instalación recuperada sigue protegida por su override. Aplicar migraciones como operación explícita y revisada, con respaldo si hay datos importantes. El servicio `migrate` del entorno nuevo no ejecuta el stamp heurístico para bases heredadas.

### Importación explícita y conservadora del padrón

Este comando se reserva al operador autorizado con acceso administrativo al backend; no es un endpoint público. Utiliza la configuración de conexión del backend. Para una ejecución nativa, trabaja desde `backend` y proporciona `--path` con la ruta privada del archivo.

Con un backend que ya ejecute el código actualizado y un esquema revisado, obtiene primero una vista previa (transacción revertida, sin guardar):

```powershell
docker compose --env-file config/local/dev1.env -f docker-compose.environment.yml exec backend python -m app.import_roster
```

El resultado muestra cantidades de altas/cambios y una huella `sha256`, sin nombres. Revisa el archivo privado y el resumen; para confirmar exactamente ese archivo:

```powershell
docker compose --env-file config/local/dev1.env -f docker-compose.environment.yml exec backend python -m app.import_roster --apply --sha256 HUELLA_DE_LA_VISTA_PREVIA
```

- El archivo agrega estudiantes, cursos, secciones, asignaciones y asociaciones académicas faltantes. Ausencia no significa baja. Un padrón parcial o una lista vacía de alumnos/cursos nunca elimina ni desactiva registros.
- Se conservan UUID, códigos existentes, estados, fechas de periodos, docentes asignados, criterios/pesos y registros históricos. No se reactivan matrículas ni alumnos/cursos inactivos.
- Para corregir nombres o cambiar grupo de un estudiante existente, usa un objeto con `id` (UUID) o `student_code`, más `first_name` y `last_name`, y agrega `--update-existing` tanto a la vista previa como a la aplicación. El código y UUID se mantienen. Si hay homónimos, usa identidad explícita; un identificador desconocido o contradictorio rechaza el lote.
- Cambiar nombres de cursos, docentes o estados se realiza mediante las funciones existentes de la aplicación, no por reemplazo desde el padrón.
- Un error revierte todo el lote. La vista previa no reserva códigos y el comando vuelve a validar al aplicar. Coordina la importación sin ediciones simultáneas; un conflicto de unicidad rechaza la transacción completa.
- Este cambio no recupera bajas o eliminaciones que se hubieran producido antes. No ejecuta migraciones, reseteos ni limpieza de datos demo.

### Pruebas focalizadas de persistencia

La [guía de recuperación de Fase 2](docs/architecture/recovery-phase2.md) registra el respaldo verificado, las pruebas PostgreSQL aisladas y los pasos propuestos para recuperar servicios sin ejecutar migraciones automáticas.

La recuperación ya se ejecutó y verificó sin cambios de registros, incluido un reinicio controlado. Para recrear el backend manteniendo el arranque sin migraciones automáticas, usa el procedimiento de recuperacion historico autorizado, ajeno al alta de desarrolladores. Los healthchecks y las 16 pruebas PostgreSQL de la imagen reconstruida pasaron; la auditoría funcional del flujo Excel se realizará después.

`tests/unit/test_roster_persistence.py` utiliza SQLite en memoria por defecto, datos sintéticos y sesiones aisladas. También admite el PostgreSQL desechable definido en `docker-compose.phase2-tests.yml`; valida explícitamente el host, usuario y nombre de base antes de provisionar un esquema de prueba. Sustituye la sesión de arranque y la del comando; nunca usa la base actual. Para ejecutar SQLite desde `backend`, configura `DATABASE_URL=sqlite://` y una `JWT_SECRET_KEY` ficticia de al menos 32 caracteres en el proceso de pruebas, y ejecuta:

```text
python -m pytest tests/unit/test_roster_persistence.py -q -p no:cacheprovider
```

No ejecutes toda la suite contra una base institucional: algunos tests anteriores escriben y eliminan registros. En Fase 3 se verificó la suite completa con una imagen recién construida en PostgreSQL sintético independiente. Las ediciones simultáneas de datos académicos y los flujos visuales completos siguen pendientes.

### Registro de calificaciones

La documentación anterior describía calificaciones mensuales y un catálogo de evidencias existente. Eso no acredita su correspondencia con el Excel institucional ni el funcionamiento completo de la importación. La organización confirmada es de exámenes cada cuatro semanas y bimestres de ocho semanas; criterios, fórmulas y estructura deben verificarse con el Excel real en la [auditoría académica](docs/academic/evaluacion-configurable-y-auditoria.md). Esta fase no modifica esas funciones ni importa notas reales.

- **Apagar los contenedores:**
  ```bash
  python scripts/dev_environment.py config/local/dev1.env stop
  ```

- **Ver los contenedores activos:**
  ```bash
  python scripts/dev_environment.py config/local/dev1.env status
  ```

- **Revisar los registros (logs) en tiempo real:**
  ```bash
  docker compose --env-file config/local/dev1.env -f docker-compose.environment.yml logs -f
  ```
