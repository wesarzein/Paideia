# Predicción experimental de rendimiento

Implementación y verificación local: 14/10/2026. Se conserva el registro de modelos
de riesgo y su flujo demostrativo; las proyecciones numéricas son un modelo local
independiente. No se habilitan alertas institucionales ni decisiones automáticas.

## Uso

En **IA**, las cuentas de área académica y dirección seleccionan grado, aula,
alumno opcional, curso opcional, periodo, fecha de corte y horizonte. La API también
permite lectura a administración y docentes, con sus ámbitos existentes. La
navegación conserva las responsabilidades definidas en `module-access.ts`.

- Próxima evaluación: mínimo tres fechas con notas del mismo alumno y curso.
  Agrupa los criterios registrados en cada fecha mediante sus pesos capturados.
  Son promedios de referencia, no una predicción de un criterio o examen específico.
- Próximo bimestre: mínimo tres bimestres observados y notas del último bimestre
  indicado en el periodo seleccionado. Debe indicarse el último bimestre completo;
  no se inventa el calendario institucional. Admite notas históricas sin fecha y
  evaluaciones con identidad de bimestre, conservando los pesos originales.
- Las notas posteriores al corte o al bimestre indicado quedan excluidas. Las
  notas históricas sin fecha no se convierten en exámenes fechados. Se distinguen
  el cero real, la ausencia de notas y la historia insuficiente.
- La asistencia no tiene identidad de bimestre. Para ese horizonte se usa solo
  asistencia de periodos previos cerrados; no se atribuyen fechas a bimestres.

Se muestran estimación sobre 20, rango, tendencia reciente, factores asociados,
orientaciones, historial utilizado, cobertura de casos y métricas sintéticas.
El promedio del aula incluye únicamente casos con proyección, con el mismo peso
por curso; no representa el promedio académico oficial del aula. No se escriben
notas, matrículas, asistencia ni seguimiento. Los enlaces a Analítica y Seguimiento
mantienen el trabajo del equipo académico en sus módulos correspondientes.

## Entrenamiento y datos

Generador determinista con semilla 20261014, **600 alumnos ficticios**, tres cursos
y dos horizontes; 12.240 ejemplos etiquetados en total. No consulta notas reales
ni usa nombres, documentos, contactos, identificadores reales o texto libre.
La muestra usada durante el entrenamiento no se conserva en el repositorio ni en el
laboratorio. El artefacto desplegado conserva la versión y huella necesarias para
auditar su procedencia.

Por horizonte: entrenamiento 5.400 ejemplos / 360 alumnos, calibración 360 / 120
y prueba 360 / 120. Los alumnos no se repiten entre conjuntos; los objetivos son
observaciones 3–7, 9 y 11 respectivamente. El escalado se ajusta exclusivamente
en entrenamiento. Ridge con alpha 10 se compara con repetir la última nota.
El rango del 90 % se calibra con residuos del conjunto de validación, sin usar
el conjunto de prueba para ajustar modelo, escalado o amplitud.

| Horizonte | MAE / 20 | RMSE | MAE de referencia | Cobertura en prueba ficticia |
| --- | --- | --- | --- | --- |
| Evaluación | 1,7461 | 2,2120 | 1,8657 | 92,5 % |
| Bimestre | 0,8069 | 1,0548 | 0,9010 | 90,0 % |

Estas cifras describen datos generados por reglas, no precisión institucional.
La cobertura del rango tampoco se garantiza para alumnos reales. Las orientaciones
son reglas de acompañamiento visibles, no intervenciones pedagógicas validadas.

Artefacto numérico versionado:
`backend/app/assets/performance-forecast-v1.json`. Contiene coeficientes, escalado,
amplitud, métricas, particiones y huella; no contiene datos personales ni objetos
ejecutables pickle. Inferencia sin sklearn, servicios externos, claves o costos.
La versión `synthetic-ridge-v1-3cb6f9df3d67` identifica el dataset de entrenamiento.

El servidor no reentrena al consultar ni altera el modelo de riesgo activo. La
adopción de un artefacto nuevo sigue la revisión de código y despliegue del proyecto.
El registro de aprobación y activación anterior sigue aplicándose a los modelos de
riesgo, no a este artefacto de proyección incluido con la aplicación.

## Contrato y evidencia

`GET /api/v1/academic-ai/forecast`: `period_id`, `student_id` o `section_id`,
`course_id` opcional, `horizon=exam|bimester`, `as_of` opcional y
`through_bimester` obligatorio para bimestres. La fecha por defecto usa Lima.
Rechaza cortes futuros, periodos inexistentes y alumnos fuera del ámbito.
Docentes requieren coincidencia de curso y aula; familias no tienen acceso.
El modelo ausente o inválido produce 503, sin resultados ficticios de respaldo.

- 9/9 pruebas del módulo aprobadas en PostgreSQL, con esquemas UUID aislados.
  Incluyen separación temporal, pesos, ceros, cortes, notas históricas, ausencia
  de evidencia, permisos cruzados y consulta sin escritura de notas.
- 83/83 pruebas frontend, incluidas seis nuevas de selección, validación, respuestas
  obsoletas, errores/reintentos y bloqueo de solicitudes duplicadas.
- Compilación Angular aprobada: 8,615 s usando imagen/caché existentes, un
  trabajador y límite de memoria; sin entrenamiento simultáneo.
- Edge/Playwright aprobado: aula, alumno, proyección de evaluación, bimestre con
  historia insuficiente, historial, error 503/reintento, móvil 390 px y recarga;
  cero errores JavaScript. El caso positivo de proyección bimestral está probado
  en API con datos históricos aislados; el laboratorio actual solo tiene un
  bimestre por alumno/curso y no se fabricó historia adicional en sus tablas.
- Las **250 notas existentes** y sus metadatos se conservaron. La huella HTTP
  antes/después es `ac88a39e8dd1d6f73b7efdfb90ed1fc60da165e269dfabc40304fef74ab1b102`.
  Se conserva también inventario PostgreSQL de las tablas académicas. El recorrido
  añadió únicamente una cuenta sintética académica reutilizable para probar el
  acceso real por rol; sus credenciales y capturas permanecen en `config/local`.

Verificador reproducible: `scripts/verify_performance_forecast_ui.py`. Solo opera
en el laboratorio `paideia-dev-phase4b3ui` / `127.0.0.1:14211`. Consulta el modelo
numérico y las notas sin entrenar; emplea el margen de 1 GiB del perfil de navegador
BI de solo lectura. No ejecutarlo junto con entrenamiento o compilación. Las
pruebas combinadas con worker conservan su margen de 1,5 GiB.

No se acredita producción, carga institucional, eficacia con historia real ni
reglas oficiales de cierre o calificación bimestral. La IA institucional conserva
los requisitos de datos suficientes, política y validación pedagógica documentados.
