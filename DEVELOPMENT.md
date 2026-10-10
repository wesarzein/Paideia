## Desarrollo y operación

Para instalar desde cero o incorporar un desarrollador, seguir la [guía de Fase 3](docs/architecture/phase3-environments.md): configuración privada por checkout, base independiente y datos sintéticos. No requiere el padrón institucional ni una copia de la base actual. El [requisito de evaluación configurable](docs/academic/evaluacion-configurable-y-auditoria.md) permanece reservado para auditoría funcional posterior.

### Instalación histórica ya provisionada

Las instrucciones siguientes documentan la instalación local anterior. No utilizarlas como bootstrap de un clon nuevo; no cambiar su `.env` ni su volumen durante el alta de otro desarrollador.

Sigue estos pasos para clonar y levantar el proyecto en tu entorno local sin instalar Node.js, Python ni las dependencias de forma manual. Docker Compose utiliza Python `3.12-slim` con `build-essential` para el backend, PostgreSQL `17-alpine` para la base de datos y Node.js `24-alpine` para el frontend. El frontend usa Angular `20.3.0` con TypeScript `5.8.3`.

### Prerrequisitos
- Tener instalado [Git](https://git-scm.com/).
- Tener instalado y abierto [Docker Desktop](https://www.docker.com/), con Docker Compose disponible.

### Pasos de instalación

1. **Clona el repositorio**
   ```bash
   git clone https://github.com/wesarzein/Paideia.git
   cd Paideia
   ```

2. **Configura las variables de entorno**
  Crea el archivo local `.env` a partir de `.env.example`. No compartas ni subas `.env` al repositorio:
   - En Windows (PowerShell):
     ```powershell
     Copy-Item .env.example .env
     ```
  Para una base nueva, define `INITIAL_ADMIN_EMAIL` y `INITIAL_ADMIN_PASSWORD` en `.env` con una cuenta institucional y contraseña única de al menos 12 caracteres. El backend crea esa cuenta solo si aún no existe; ya no hay credenciales de administrador demo codificadas. Si la base ya tiene administradores, conserva esas cuentas.
   - En Linux / macOS / Git Bash:
     ```bash
     cp .env.example .env
     ```

3. **Coloca el padrón escolar privado**
  El padrón real se entrega por separado para proteger los datos personales de los alumnos. Guárdalo como `database/local/roster.json`; la carpeta está excluida de Git. El archivo debe contener `school_year` y secciones con `level`, `grade`, `section`, `students` (formato `APELLIDOS, NOMBRES`) y `courses` (`name` y `teacher` opcional). El backend **no lee ni sincroniza el padrón al arrancar**. Los códigos existentes se conservan; los nuevos usan el siguiente sufijo disponible del grupo, no la posición en la lista.

  Ejemplo sin datos personales:
  ```json
  {
    "school_year": 2026,
    "sections": [{
      "level": "Primaria",
      "grade": "4°",
      "section": "A",
      "students": ["APELLIDOS, NOMBRES"],
      "courses": [{"name": "Curso", "teacher": "Docente"}]
    }]
  }
  ```

  Compose monta el archivo como solo lectura. El backend no lo importa al iniciar: su conciliación requiere el comando explícito descrito abajo. Los registros ausentes nunca se eliminan ni desactivan por ese archivo.

### Incorporar a otro desarrollador y sincronizar datos

GitHub sincroniza el código y las migraciones de Alembic; no sincroniza el volumen local de PostgreSQL, el archivo `.env` ni `database/local/roster.json`.

- Para que en una instalación nueva aparezcan los alumnos y cursos base: el compañero clona los cambios, configura su propio `.env`, recibe el padrón por un canal privado y lo coloca en `database/local/roster.json`. Después de provisionar el esquema, un operador autorizado importa explícitamente el padrón con el procedimiento de abajo. Reiniciar el backend no importa ni concilia el archivo.
- Cada base local tiene registros independientes. Para desarrollo normal usar catálogos sintéticos; para probar información común editable, usar una API de integración compartida y autorizada. Copiar un respaldo no establece replicación continua y no es el procedimiento habitual de alta de compañeros.
- Cada desarrollador debe usar su propia configuración local y cuenta administrativa. Las contraseñas, `.env`, respaldos y el padrón privado no se incorporan al repositorio.
- Las migraciones se aplican explícitamente, con revisión previa. El backend nuevo ya no las ejecuta al arrancar y conserva el volumen entre reinicios. No usar `docker compose down -v` sobre instalaciones con datos que deban conservarse.

4. **Construye y levanta los contenedores**
  Ejecuta el siguiente comando desde la raíz del proyecto para construir las imágenes y arrancar los servicios en segundo plano:
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.recovery.yml up -d --no-deps backend
   ```

5. **Accede a la aplicación**
   Una vez que los contenedores estén activos, puedes ingresar desde tu navegador:
   - **Frontend (Interfaz web):** `http://localhost:4200`
  - **Backend (documentación de la API):** `http://localhost:8000/docs`
  - **Base de datos PostgreSQL:** `localhost:5432`

  El Dashboard muestra indicadores con filtros por grado, sección, curso, periodo y mes. Estudiantes, cursos, calificaciones, asistencia, seguimiento y reportes consumen datos persistidos en PostgreSQL. Analítica e IA mantienen por ahora una interfaz informativa, sin cálculos ni predicciones.

### Restablecer la contraseña de administrador

La contraseña existente no se puede recuperar en texto plano. Para cambiarla, desde la raíz del proyecto ejecuta en una terminal interactiva:

```powershell
docker compose exec backend python -m app.reset_admin_password
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
docker compose exec backend python -m app.import_roster
```

El resultado muestra cantidades de altas/cambios y una huella `sha256`, sin nombres. Revisa el archivo privado y el resumen; para confirmar exactamente ese archivo:

```powershell
docker compose exec backend python -m app.import_roster --apply --sha256 HUELLA_DE_LA_VISTA_PREVIA
```

- El archivo agrega estudiantes, cursos, secciones, asignaciones y asociaciones académicas faltantes. Ausencia no significa baja. Un padrón parcial o una lista vacía de alumnos/cursos nunca elimina ni desactiva registros.
- Se conservan UUID, códigos existentes, estados, fechas de periodos, docentes asignados, criterios/pesos y registros históricos. No se reactivan matrículas ni alumnos/cursos inactivos.
- Para corregir nombres o cambiar grupo de un estudiante existente, usa un objeto con `id` (UUID) o `student_code`, más `first_name` y `last_name`, y agrega `--update-existing` tanto a la vista previa como a la aplicación. El código y UUID se mantienen. Si hay homónimos, usa identidad explícita; un identificador desconocido o contradictorio rechaza el lote.
- Cambiar nombres de cursos, docentes o estados se realiza mediante las funciones existentes de la aplicación, no por reemplazo desde el padrón.
- Un error revierte todo el lote. La vista previa no reserva códigos y el comando vuelve a validar al aplicar. Coordina la importación sin ediciones simultáneas; un conflicto de unicidad rechaza la transacción completa.
- Este cambio no recupera bajas o eliminaciones que se hubieran producido antes. No ejecuta migraciones, reseteos ni limpieza de datos demo.

### Pruebas focalizadas de persistencia

La [guía de recuperación de Fase 2](docs/architecture/recovery-phase2.md) registra el respaldo verificado, las pruebas PostgreSQL aisladas y los pasos propuestos para recuperar servicios sin ejecutar migraciones automáticas.

La recuperación ya se ejecutó y verificó sin cambios de registros, incluido un reinicio controlado. Para recrear el backend manteniendo el arranque sin migraciones automáticas, usa `docker compose -f docker-compose.yml -f docker-compose.recovery.yml up -d --no-deps backend`. Los healthchecks y las 16 pruebas PostgreSQL de la imagen reconstruida pasaron; la auditoría funcional del flujo Excel se realizará después.

`tests/unit/test_roster_persistence.py` utiliza SQLite en memoria por defecto, datos sintéticos y sesiones aisladas. También admite el PostgreSQL desechable definido en `docker-compose.phase2-tests.yml`; valida explícitamente el host, usuario y nombre de base antes de provisionar un esquema de prueba. Sustituye la sesión de arranque y la del comando; nunca usa la base actual. Para ejecutar SQLite desde `backend`, configura `DATABASE_URL=sqlite://` y una `JWT_SECRET_KEY` ficticia de al menos 32 caracteres en el proceso de pruebas, y ejecuta:

```text
python -m pytest tests/unit/test_roster_persistence.py -q -p no:cacheprovider
```

No ejecutes toda la suite contra una base institucional: algunos tests anteriores escriben y eliminan registros. En Fase 3 se verificó la suite completa con una imagen recién construida en PostgreSQL sintético independiente. Las ediciones simultáneas de datos académicos y los flujos visuales completos siguen pendientes.

### Registro de calificaciones

La documentación anterior describía calificaciones mensuales y un catálogo de evidencias existente. Eso no acredita su correspondencia con el Excel institucional ni el funcionamiento completo de la importación. La organización confirmada es de exámenes cada cuatro semanas y bimestres de ocho semanas; criterios, fórmulas y estructura deben verificarse con el Excel real en la [auditoría académica](docs/academic/evaluacion-configurable-y-auditoria.md). Esta fase no modifica esas funciones ni importa notas reales.

- **Apagar los contenedores:**
  ```bash
  docker compose stop
  ```

- **Ver los contenedores activos:**
  ```bash
  docker compose ps
  ```

- **Revisar los registros (logs) en tiempo real:**
  ```bash
  docker compose logs -f
  ```
