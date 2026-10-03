## Guía de Inicio Rápido con Docker

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
  El padrón real se entrega por separado para proteger los datos personales de los alumnos. Guárdalo como `database/local/roster.json`; la carpeta está excluida de Git. El archivo debe contener `school_year` y secciones con `level`, `grade`, `section`, `students` (formato `APELLIDOS, NOMBRES`) y `courses` (`name` y `teacher` opcional). Al sincronizar, los códigos se generan con el orden de esta lista: primaria `{grado}P{orden}` (por ejemplo, `5P001`) y secundaria `{grado}S{sección}{orden}` (por ejemplo, `1SB001`).

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

  Compose monta el archivo como solo lectura. Al iniciar, el backend sincroniza ese padrón, desactiva alumnos/cursos que ya no correspondan y conserva sus notas, asistencias e historial. Si el archivo no existe, la aplicación no inventa alumnos.

### Incorporar a otro desarrollador y sincronizar datos

GitHub sincroniza el código y las migraciones de Alembic; no sincroniza el volumen local de PostgreSQL, el archivo `.env` ni `database/local/roster.json`.

- Para que en una instalación nueva aparezcan los alumnos y cursos base: el compañero clona los cambios, configura su propio `.env`, recibe el padrón 2026 por un canal privado y lo coloca en `database/local/roster.json`. Luego ejecuta `docker compose up --build -d`. El backend aplica las migraciones y concilia el padrón al iniciar. No hace falta copiar la base de datos solo para obtener ese catálogo.
- Para conservar también las calificaciones, asistencias, usuarios y seguimientos ya registrados, sincronizar el padrón no basta: esos datos están en tu PostgreSQL. Hay que compartir una copia de respaldo de la base por un canal privado y restaurarla en la instancia del compañero antes de iniciar el backend. El respaldo contiene información personal y académica de menores: nunca lo subas a GitHub. Coordinen una copia consistente y no trabajen escribiendo en las dos bases por separado, porque no se replican entre sí.
- Cada desarrollador debe usar su propia configuración local y cuenta administrativa. Las contraseñas, `.env`, respaldos y el padrón privado no se incorporan al repositorio.
- Las migraciones que sí estén subidas al repositorio se aplican automáticamente al iniciar el backend; el contenedor conserva su volumen PostgreSQL entre reinicios. No uses `docker compose down -v` salvo que quieras borrar intencionalmente la base local.

4. **Construye y levanta los contenedores**
  Ejecuta el siguiente comando desde la raíz del proyecto para construir las imágenes y arrancar los servicios en segundo plano:
   ```bash
   docker compose up --build -d
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

Alembic es la única fuente de cambios del esquema. No uses `Base.metadata.create_all()` ni agregues `CREATE TABLE`/`ALTER TABLE` al arranque de FastAPI o a scripts de inicialización de PostgreSQL. Los scripts de `database/init` se reservan para extensiones requeridas antes de que arranque la API. El padrón institucional se carga desde `database/local/roster.json` después de aplicar migraciones; no se deben sembrar alumnos ni cursos demo en la base compartida.

Cuando cambies modelos SQLAlchemy, desde `backend` crea una revisión y revísala antes de subirla:

```powershell
alembic revision --autogenerate -m "describe_schema_change"
alembic upgrade head
```

El contenedor ejecuta `python -m app.migrate` antes de iniciar FastAPI. Este paso actualiza bases versionadas y reconcilia instalaciones heredadas sin borrar sus datos.

### Registro de calificaciones

Las calificaciones se registran por mes; dos meses consecutivos conforman un bimestre. El catálogo de evidencias admitido es: Actitud ante el área, Cuaderno, Módulo, Exposición-Trabajos y Evaluación. Las plantillas de importación pueden usar encabezados mensuales; el sistema normaliza aliases previos y valida notas antes de guardarlas. Los códigos de cursos nuevos y del padrón se generan automáticamente y son estables para cada nombre de curso.

- **Apagar los contenedores:**
  ```bash
  docker compose down
  ```

- **Ver los contenedores activos:**
  ```bash
  docker compose ps
  ```

- **Revisar los registros (logs) en tiempo real:**
  ```bash
  docker compose logs -f
  ```