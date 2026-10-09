# Paideia: continuidad de desarrollo

- Antes de trabajar: comprobar rama, commit y Git; leer `docs/development/roadmap.md`
  y la evidencia de la tarea siguiente. Conservar cambios ajenos y funciones existentes.
- Arquitectura: Angular standalone, FastAPI, SQLAlchemy 2, PostgreSQL 17 y Alembic.
  Mantener la arquitectura y reutilizar servicios/componentes. Python 3.12, Node 24,
  Angular/TypeScript del lockfile; las dependencias nativas de esta laptop son ajenas.
- Único laboratorio autorizado: `paideia-dev-phase4b3ui`, configuración
  `config/local/phase4b3ui.env`, Compose `docker-compose.environment.yml`, frontend
  `127.0.0.1:14211`. Verificar etiquetas, volumen y conexión efectiva antes de escribir.
  Conservar las 21 notas de referencia y sus snapshots. Usar esquemas UUID para pruebas
  de migración o fixtures destructivas; nunca downgrade de public con datos conservables.
- No tocar instalación `paideia`, `.env` raíz, volumen institucional, padrones, secretos
  o respaldos. No prune, down -v, reset --hard, push, merge, main ni despliegue público.
- Comprobar RAM antes de navegador/build/tests exigentes; una operación exigente a la vez.
  Reutilizar cachés e imágenes, límites de memoria y un trabajador en compilaciones.
- Pruebas focalizadas positivas/negativas para permisos, relaciones, transacciones y
  persistencia. No repetir auditorías/suites aprobadas sin un cambio que las afecte.
  Código encontrado o compilación no equivalen a recorrido de interfaz comprobado.
- No inventar reglas institucionales de opcionales/fórmulas/ponderaciones; mantener
  cálculos ambiguos fuera de resultados oficiales. IA/BI después de módulos principales,
  sin activar servicios, costos o claves externas sin autorización.
- Continuar autónomamente con tareas definidas: aceptación → pruebas → evidencia y
  roadmap → commit local → siguiente prioridad. Si hay bloqueo, registrar motivo y
  comando/punto de reanudación; avanzar con tareas independientes seguras.
