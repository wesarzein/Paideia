# Paideia

Plataforma inteligente para el seguimiento y prevencion del riesgo academico de estudiantes de la IE Paideia Newton, Trujillo, La Libertad, Peru.

## Problema

La institucion gestiona informacion academica en hojas Excel dispersas. La consolidacion, analisis y seguimiento requieren trabajo manual.

## Objetivo

Centralizar los datos académicos y apoyar el seguimiento institucional con módulos transaccionales y un dashboard.

## Alcance

Incluye autenticación, usuarios, estudiantes, cursos, calificaciones, asistencia, seguimiento, dashboard, reportes e importación Excel/CSV. Analítica e IA tienen por ahora una interfaz informativa; sus cálculos y predicciones no están habilitados.

El [contexto técnico y plan de auditoría de evaluación configurable](docs/academic/evaluacion-configurable-y-auditoria.md) registra el requisito de competencias, criterios, ponderaciones y fórmulas personalizables por curso y periodo, con importación Excel, versionado y protección de historiales. Está documentado para una auditoría futura; no se declara implementado.

La [auditoría académica de Fase 4A](docs/academic/auditoria-fase4a.md) registra los recorridos ejecutados con PostgreSQL sintético y navegador, la matriz de cumplimiento, las brechas del Excel institucional y la implementación parcial de configuración. No se han aplicado todavía sus correcciones funcionales.

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

Git y Docker/Compose. Python 3.12 permite generar la configuración privada sin instalar dependencias de la aplicación; también puede ejecutarse mediante Docker según la guía. Node.js solo es necesario para desarrollo Angular nativo.

## Inicio rapido con Docker

Clona el repositorio y entra en su directorio:

```bash
git clone https://github.com/wesarzein/Paideia.git
cd Paideia
```

Genera un entorno propio con secretos nuevos, sin cambiar el `.env` de otra instalación:

```bash
python scripts/setup_dev.py dev1 --port 14200
```

El archivo privado queda en `config/local/dev1.env`, excluido de Git. El generador no sobrescribe archivos existentes.

El alta de desarrollo usa datos sintéticos y no requiere el padrón ni respaldos institucionales. El padrón real conserva su proceso explícito y privado; el arranque nunca lo importa.

Construye las imágenes y levanta los servicios en segundo plano:

```bash
docker compose --env-file config/local/dev1.env -f docker-compose.environment.yml build
docker compose --env-file config/local/dev1.env -f docker-compose.environment.yml run -T migrate
docker compose --env-file config/local/dev1.env -f docker-compose.environment.yml run -T seed
docker compose --env-file config/local/dev1.env -f docker-compose.environment.yml up -d backend frontend
```

## Versiones y accesos

- Backend: Python `3.12-slim` con `build-essential`
- Base de datos: PostgreSQL 17 en red interna, sin puerto publicado en el entorno nuevo
- Frontend: Node.js `24-alpine`
- Entorno nuevo: http://localhost:14200, con API bajo `/api/v1` mediante Nginx
- La instalación histórica conserva sus accesos 4200/8000 y su override de recuperación.

La [guía de Fase 3](docs/architecture/phase3-environments.md) explica alta del segundo desarrollador, migraciones explícitas, secretos, pruebas aisladas y requisitos pendientes de despliegue. No combinar el Compose nuevo con el histórico ni aplicarlo sobre el volumen institucional.

## Testing

```bash
python -m unittest discover -s scripts -p "test_*.py"
docker compose --env-file .env.test.example -p paideia-ci-local -f docker-compose.tests.yml build
docker compose --env-file .env.test.example -p paideia-ci-local -f docker-compose.tests.yml run -T migrate
docker compose --env-file .env.test.example -p paideia-ci-local -f docker-compose.tests.yml run -T tests
```

No ejecutar pruebas de escritura contra la base institucional. Para pruebas frontend nativas usar `npm ci --legacy-peer-deps` y `npm test -- --run` dentro de `frontend`.

## Scrum

El desarrollo se ejecutara por sprints, tomando el backlog documentado como punto de partida para refinamiento.

## Seguridad

No incluir datos reales, documentos, backups, Excel/CSV reales, contrasenas, JWT ni secretos.
