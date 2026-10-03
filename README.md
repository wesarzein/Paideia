# Paideia

Plataforma inteligente para el seguimiento y prevencion del riesgo academico de estudiantes de la IE Paideia Newton, Trujillo, La Libertad, Peru.

## Problema

La institucion gestiona informacion academica en hojas Excel dispersas. La consolidacion, analisis y seguimiento requieren trabajo manual.

## Objetivo

Centralizar los datos académicos y apoyar el seguimiento institucional con módulos transaccionales y un dashboard.

## Alcance

Incluye autenticación, usuarios, estudiantes, cursos, calificaciones, asistencia, seguimiento, dashboard, reportes e importación Excel/CSV. Analítica e IA tienen por ahora una interfaz informativa; sus cálculos y predicciones no están habilitados.

## Arquitectura

```mermaid
flowchart TD
  A[Angular SPA] -->|REST JSON| B[FastAPI]
  B --> C[Service Layer]
  C --> D[Repositories]
  D --> E[(PostgreSQL)]
  B --> F[Dashboard]
  F -. "planificado" .-> G[Analítica e IA]
```

## Stack tecnologico

| Capa | Tecnologia |
| --- | --- |
| Frontend | Angular 20.3, TypeScript 5.8.3, Vitest |
| Backend | Python 3.12-slim, FastAPI 0.141, Pydantic 2, SQLAlchemy 2 |
| Datos | PostgreSQL 17-alpine, Alembic |
| Analítica e IA | Interfaces previstas; procesamiento aún no habilitado |
| Infraestructura | Docker, Docker Compose; frontend sobre Node.js 24-alpine |

## Modulos

Autenticación, usuarios, estudiantes, cursos y asignaciones, calificaciones, asistencia, seguimiento, dashboard, reportes e importación. Analítica e IA están pendientes de implementación funcional.

## Estructura del repositorio

```text
backend/   FastAPI, SQLAlchemy, Alembic y tests
frontend/  Angular SPA y componentes base
database/  migraciones/configuracion, respaldos y padrón escolar local excluido de Git
ml/        estructura de IA sin modelos entrenados
bi/        SQL, datasets y KPIs de analitica de negocio
docs/      requisitos, arquitectura, Scrum, IA y analitica de negocio
```

## Requisitos previos

Git, Docker Desktop y VS Code. Node.js es opcional para desarrollo Angular local; el entorno Docker utiliza Node.js 24-alpine. Python solo es necesario si se ejecuta el backend fuera de Docker.

## Inicio rapido con Docker

Clona el repositorio y entra en su directorio:

```bash
git clone https://github.com/wesarzein/Paideia.git
cd Paideia
```

Crea el archivo local de variables de entorno a partir de la plantilla:

```bash
cp .env.example .env
```

En Windows PowerShell, usa `Copy-Item .env.example .env`. Revisa los valores locales y no subas `.env` al repositorio.

El padrón escolar se entrega por separado para proteger los datos personales de los alumnos. Guárdalo en `database/local/roster.json` antes de iniciar Compose. Su estructura está descrita en [DEVELOPMENT.md](./DEVELOPMENT.md); esa carpeta está excluida de Git y no incluye datos en clones nuevos.

Construye las imágenes y levanta los servicios en segundo plano:

```bash
docker compose up --build -d
```

## Versiones y accesos

- Backend: Python `3.12-slim` con `build-essential`
- Base de datos: `postgres:17-alpine`, puerto `5432`
- Frontend: Node.js `24-alpine`
- Frontend: http://localhost:4200
- Backend / documentación API: http://localhost:8000/docs

## Testing

```bash
cd backend && pytest
cd frontend && npm test -- --run
```

## Scrum

El desarrollo se ejecutara por sprints, tomando el backlog documentado como punto de partida para refinamiento.

## Seguridad

No incluir datos reales, documentos, backups, Excel/CSV reales, contrasenas, JWT ni secretos.
