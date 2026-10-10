# Paideia: continuidad de desarrollo

- Antes de trabajar: comprobar rama, commit y Git; leer `docs/development/roadmap.md`
  y la evidencia de la tarea siguiente. Conservar cambios ajenos y funciones existentes.
- Arquitectura: Angular standalone, FastAPI, SQLAlchemy 2, PostgreSQL 17 y Alembic.
  Mantener la arquitectura y reutilizar servicios/componentes. Python 3.12, Node 24,
  Angular/TypeScript del lockfile; las dependencias nativas de esta laptop son ajenas.
- Único laboratorio autorizado: `paideia-dev-phase4b3ui`, configuración
  `config/local/phase4b3ui.env`, Compose `docker-compose.environment.yml`, frontend
  `127.0.0.1:14211`. Verificar etiquetas, volumen y conexión efectiva antes de escribir.
  Conservar las 32 notas actuales (incluidas las 21 iniciales) y sus snapshots. Usar esquemas UUID para pruebas
  de migración o fixtures destructivas; nunca downgrade de public con datos conservables.
- No tocar instalación `paideia`, `.env` raíz, volumen institucional, padrones, secretos
  o respaldos. No prune, down -v, reset --hard ni despliegue público.
  La solicitud integral IA/BI autoriza fetch, push normal, PR y squash condicionado
  a aceptación funcional, auditoría de todos los commits salientes y CI aprobado.
  Conservar referencia de respaldo; nunca force push ni integrar fallos críticos.
- Comprobar RAM antes de navegador/build/tests exigentes; una operación exigente a la vez.
  Reutilizar cachés e imágenes, límites de memoria y un trabajador en compilaciones.
- Pruebas focalizadas positivas/negativas para permisos, relaciones, transacciones y
  persistencia. No repetir auditorías/suites aprobadas sin un cambio que las afecte.
  Código encontrado o compilación no equivalen a recorrido de interfaz comprobado.
- No inventar reglas institucionales de opcionales/fórmulas/ponderaciones; mantener
  cálculos ambiguos fuera de resultados oficiales. Prioridad actual: BI PostgreSQL/Angular
  e IA local experimental demostrativa; modelos sintéticos jamás generan alertas reales.
  No servicios, costos ni claves externas. IA institucional requiere datos, política,
  validación y aprobación explícitas. Conservar módulos existentes, sin ampliar ERP.
- Alcance congelado del MVP (10/10/2026): cerrar únicamente la estabilización existente,
  auditoría 0017, recuperación IA 0018, BI, instalación y regresiones esenciales.
  No ampliar módulos, algoritmos, ERP ni documentación universitaria. Conservar el trabajo
  interrumpido. Consolidar por rama temporal y PR squash solo con CI aprobado y respaldo.
  Al verificar el MVP y su integración en main, detener el desarrollo; registrar limitaciones
  no críticas para otra versión. Ante un bloqueo, conservar cambios y punto de reanudación.
