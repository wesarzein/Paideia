## Guía de Inicio Rápido con Docker

Sigue estos pasos para clonar y levantar el proyecto en tu entorno local sin necesidad de instalar Node.js, Python o dependencias de forma manual.

### Prerrequisitos
- Tener instalado [Git](https://git-scm.com/).
- Tener instalado y abierto [Docker Desktop](https://www.docker.com/).

### Pasos de instalación

1. **Clona el repositorio**
   ```bash
   git clone https://github.com/wesarzein/Paideia.git
   cd Paideia
   ```

2. **Configura las variables de entorno**
   Duplica el archivo de ejemplo `.env.example` y renómbralo a `.env`:
   - En Windows (PowerShell):
     ```powershell
     Copy-Item .env.example .env
     ```
   - En Linux / macOS / Git Bash:
     ```bash
     cp .env.example .env
     ```

3. **Construye y levanta los contenedores**
   Ejecuta el siguiente comando para compilar las imágenes y arrancar los servicios en segundo plano:
   ```bash
   docker compose up --build -d
   ```

4. **Accede a la aplicación**
   Una vez que los contenedores estén activos, puedes ingresar desde tu navegador:
   - **Frontend (Interfaz web):** `http://localhost:4200`
   - **Backend (Documentación de la API / Docs):** `http://localhost:8000/docs`

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