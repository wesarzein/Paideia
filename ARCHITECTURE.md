# Arquitectura

Paideia usa una arquitectura modular simple orientada a mantener un producto escalable y mantenible.

```mermaid
flowchart LR
  UI[Angular 22 SPA] --> API[FastAPI REST API]
  API --> Auth[Auth/RBAC]
  API --> Services[Service Layer]
  Services --> Repos[Repositories]
  Repos --> DB[(PostgreSQL 17-alpine)]
  Services --> AI[Modulo IA]
  DB --> BI[Analitica]
```

## Frontend

SPA Angular con standalone components, Router, lazy loading, HttpClient, guards, interceptor JWT, componentes reutilizables y paginas placeholder.

## Backend

FastAPI expone `/api/v1`. La estructura separa endpoints, servicios, repositorios, schemas, modelos y modulos. La primera fase implementa solo health check y configuracion.

## Base de datos

PostgreSQL 17 mediante la imagen `postgres:17-alpine`, SQLAlchemy 2, Alembic, UUID donde corresponde, integridad referencial y timestamps timezone-aware. Modelo inicial: users, roles, students, academic_periods, grades, sections y courses.

## IA

La IA consumira servicios internos del backend. No accede desde frontend a la base de datos. La prediccion sera alerta temprana indicativa y requiere validacion pedagogica.

## BI / analitica

La capa de inteligencia de negocio o analitica consumira datos preparados desde PostgreSQL y vistas analiticas.

## Seguridad

JWT, RBAC, hashing Argon2 y dependencias FastAPI quedan preparados. No se almacenan contrasenas en texto plano.

## Docker

Compose define `postgres`, `backend` y `frontend`, red interna, healthchecks, volumen persistente y puertos configurables. El backend usa Python `3.12-slim` con `build-essential`, y el frontend usa Node.js `24-alpine`. Los accesos locales son `http://localhost:4200`, `http://localhost:8000/docs` y PostgreSQL en `localhost:5432`.

## Flujo de datos

```mermaid
sequenceDiagram
  participant U as Usuario
  participant F as Angular
  participant A as FastAPI
  participant P as PostgreSQL
  U->>F: Interaccion
  F->>A: REST/JSON
  A->>P: SQLAlchemy
  P-->>A: Datos
  A-->>F: Respuesta JSON
```

## Decisiones

- Se mantiene monolito modular, sin microservicios, Kubernetes, Redis ni colas.
- Node.js se limita al runtime/herramientas del frontend.
- Se documentan tablas futuras sin crearlas todas en la primera fase.
- El entorno Docker validado usa `postgres:17-alpine`, Python `3.12-slim` con `build-essential` y Node.js `24-alpine`.

## Fases posteriores

CRUD, autenticacion completa, importacion transaccional, reportes, dashboards e IA entrenada se implementaran mediante historias de usuario.
