# Paideia

Plataforma inteligente para el seguimiento y prevencion del riesgo academico de estudiantes de la IE Paideia Newton, Trujillo, La Libertad, Peru.

## Problema

La institucion gestiona informacion academica en hojas Excel dispersas. La consolidacion, analisis y seguimiento requieren trabajo manual.

## Objetivo

Centralizar datos academicos y convertirlos en informacion util mediante un sistema transaccional, analitica, inteligencia de negocio e IA como alerta temprana.

## Alcance

Incluye base para gestion academica, notas, asistencia, seguimiento, analitica, IA, reportes e importacion Excel/CSV. No es un ERP escolar completo.

## Arquitectura

```mermaid
flowchart TD
  A[Angular SPA] -->|REST JSON| B[FastAPI]
  B --> C[Service Layer]
  C --> D[Repositories]
  D --> E[(PostgreSQL)]
  B --> F[AI Risk Prediction]
  E --> G[Analitica]
```

## Stack tecnologico

| Capa | Tecnologia |
| --- | --- |
| Frontend | Angular 20.3, TypeScript 5.8.3, Vitest |
| Backend | Python 3.12-slim, FastAPI 0.141, Pydantic 2, SQLAlchemy 2 |
| Datos | PostgreSQL 17-alpine, Alembic |
| IA | Pandas, NumPy, scikit-learn |
| Infraestructura | Docker, Docker Compose; frontend sobre Node.js 24-alpine |

## Modulos

Autenticacion, usuarios, estudiantes, gestion academica, calificaciones, asistencia, seguimiento, BI, IA, reportes e importacion.

## Estructura del repositorio

```text
backend/   FastAPI, SQLAlchemy, Alembic y tests
frontend/  Angular SPA y componentes base
database/  SQL inicial, seeds y backups excluidos
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
