## Guía de Inicio Rápido con Docker

Sigue estos pasos para clonar y levantar el proyecto en tu entorno local sin instalar Node.js, Python ni las dependencias de forma manual. Docker Compose utiliza Python `3.12-slim` con `build-essential` para el backend, PostgreSQL `17-alpine` para la base de datos y Node.js `24-alpine` para el frontend.

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
   - En Linux / macOS / Git Bash:
     ```bash
     cp .env.example .env
     ```

3. **Construye y levanta los contenedores**
  Ejecuta el siguiente comando desde la raíz del proyecto para construir las imágenes y arrancar los servicios en segundo plano:
   ```bash
   docker compose up --build -d
   ```

4. **Accede a la aplicación**
   Una vez que los contenedores estén activos, puedes ingresar desde tu navegador:
   - **Frontend (Interfaz web):** `http://localhost:4200`
  - **Backend (documentación de la API):** `http://localhost:8000/docs`
  - **Base de datos PostgreSQL:** `localhost:5432`

### Versiones del entorno Docker

| Servicio | Imagen o base | Acceso local |
| --- | --- | --- |
| Backend | Python `3.12-slim` + `build-essential` | `http://localhost:8000` |
| Base de datos | `postgres:17-alpine` | `localhost:5432` |
| Frontend | `node:24-alpine` | `http://localhost:4200` |

---

### Comandos útiles para el día a día

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