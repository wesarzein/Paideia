# Contribucion

## Ramas

- `main`: rama estable.
- `develop`: integracion de sprint.
- `feature/*`: nuevas capacidades.
- `fix/*`: correcciones.
- `docs/*`: documentacion.

## Commits

Usar prefijos: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`.

## Pull requests

Cada PR debe describir alcance, pruebas ejecutadas, riesgos y relacion con historias o requerimientos.

## Entornos independientes y migraciones paralelas

Cada desarrollador debe usar su propio checkout/worktree, rama, archivo privado y base sintética según la [guía de Fase 3](docs/architecture/phase3-environments.md). No compartir un directorio de trabajo mutable ni usar la base institucional para pruebas. La información compartida entre usuarios pertenece a una API de integración común, no a Git.

Consultar heads Alembic antes de crear revisiones y coordinar con el compañero. No editar una migración ya aplicada para resolver conflictos. Revisar los merges de heads y comprobar ambos caminos en bases sintéticas antes de integrar. Incluir lockfiles y cambios de contrato en la revisión; no ejecutar migraciones sobre una base compartida sin el procedimiento operativo autorizado.

## Definition of Done

- Codigo revisado.
- Tests relevantes ejecutados.
- Sin secretos ni datos reales.
- Documentacion actualizada cuando aplique.
- Cumple el alcance aprobado para el sprint.
