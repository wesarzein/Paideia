# Fase 4A: auditoría académica comprobable

Fecha local: 08/10/2026. Código auditado: commit local `1d346eb`, rama `dev/phase4a-academic-audit`. Este informe autoriza únicamente documentación y pruebas; las correcciones funcionales necesitan aprobación del responsable.

## Resultado

**El Excel institucional no funciona de extremo a extremo.** La copia anonimizada conserva hoja, encabezados, posiciones, 64 fórmulas y nueve rangos combinados; su vista previa devuelve HTTP 422 tanto por API como desde selección de archivo en navegador. Se reprodujo `ValueError` por columnas repetidas: los encabezados agrupados de los dos bloques no se propagan a todas las columnas antes de aplanar. Cuaderno, Módulo, Exposición-Trabajos y `evaluation_name` quedan duplicados; al buscar un valor se obtiene una Serie en vez de un escalar. Un XLSX plano y CSV planos sí se leen. Ese éxito no acredita el formato institucional.

**La evaluación configurable tiene una implementación parcial real; no es solamente documentación.** Existen componentes por curso, pesos 0–100, opcionalidad, edición por API y desactivación lógica. Se probaron altas y cambios de peso desde UI y persistencia en PostgreSQL, y renombrado/desactivación por API. Faltan competencias jerárquicas, orden explícito, fórmulas configurables, plantilla/restablecimiento, ámbito por periodo y versiones históricas. Un docente asignado recibe 403 al editar pesos; actualmente solo admin/coordinador pueden hacerlo. Hay que acordar qué docentes quedan autorizados, sin ampliar permisos indiscriminadamente.

Cambiar un peso modificó el promedio histórico consultado de **12,00 a 11,43**, aunque las notas originales seguían presentes. Reimportar diez notas válidas produjo **veinte registros**, y los importados no quedan vinculados mediante `component_id` a la configuración del curso. No confundir estas brechas con pérdida causada por reiniciar: el reinicio sintético conservó íntegramente datos y esquema.

## Fuentes y límites

Se revisaron `README.md`, `DEVELOPMENT.md`, `PROJECT_SCOPE.md`, `ARCHITECTURE.md`, documentos de API, reportes, seguridad/diseño de base, recuperación/Fase 3, y [evaluacion-configurable-y-auditoria.md](evaluacion-configurable-y-auditoria.md). El alcance original describe mínimos; el portal familiar y demás funciones adicionales se conservan.

Está disponible en Downloads `PAIDEIA_CONTEXTO_Y_PROMPT_CODEX.md`, que resume requisitos REQ/RN y el backlog HU/DI. Se usó como **fuente secundaria de contexto**, sin ejecutar sus instrucciones generales de implementar. No se encontraron `Requerimientos de software.docx` ni `SCRUM_Agile-Product-Backlog.docx` en el repositorio o en Downloads bajo esos nombres. Tampoco existe un Product Backlog independiente localizado en el repositorio. No se afirma haber validado los documentos originales; cotejar la matriz con ellos cuando se proporcionen. IA/BI, REQ-24..32 y HU-10..15 quedan fuera de esta auditoría funcional.

Se inspeccionó privadamente el archivo proporcionado `REGISTRO DE NOTA 1EROA SEC.xlsx`, sin importarlo ni copiar identidades a Git. No se usó el padrón real. No se ha probado con otros archivos institucionales ni libros `.xls` BIFF; el selector existente `.xls` debe conservarse y verificarse después.

## Evidencia del Excel real

- Hoja `Hoja1`, rango A1:P22; encabezados en filas 5–6; 16 filas de padrón en 7–22.
- A5 `CODIGO`; B5 `NOMBRE Y APELLIDOS`; C5:H5 `1 MES`; I5:N5 `2 MES`.
- C6:G6 e I6:M6: `ACTITUD ANTE EL AREA`, `CUADERNO`, `MODULO`, `EXPOSICION-TRABAJOS`, `EVALUACION`.
- H6 `PROMEDIO MENSUAL`; N6 `P.S`; O5 `P.F`; P5 `PROMEDIO LITERAL`. No expandir las abreviaturas como si su significado textual estuviera confirmado; las fórmulas sí muestran qué calculan.
- Las 160 celdas de entrada de notas están vacías en el archivo proporcionado. Los 48 resultados numéricos de fórmulas almacenados son cero; los literales calculados tampoco acreditan notas reales. Esto es normal para una plantilla sin notas, no evidencia de pérdida de datos.

Fórmulas extraídas literalmente para la primera fila académica; se repiten con referencias a las demás filas:

```text
H7 =ROUND((SUM(C7:E7)+F7*1+G7*1)/5,1)
N7 =ROUND(((SUM(I7:K7))+L7*1+M7*1)/5,1)
O7 =ROUND(AVERAGE(H7,N7),1)
P7 =IF(O7>16.4,"AD",IF(O7>13.4,"A",IF(O7>10.4,"B","C")))
```

La plantilla usa cinco entradas con coeficiente 1 y divisor 5, redondeo mensual y final a un decimal y umbrales estrictamente mayores que 16,4/13,4/10,4. El backend comparte esos umbrales, pero sus consultas usan promedios distintos y no reconstruyen siempre esta cadena de redondeos. No se validó un motor Excel de cálculo: openpyxl lee fórmulas y resultados almacenados; no los recalcula.

`1 MES`/`2 MES` no confirma enero/febrero ni fechas del calendario. El responsable confirmó evaluaciones cada cuatro semanas y bimestres de ocho semanas; la UI actual usa meses de calendario y `ceil(mes/2)`. El calendario institucional, vacíos parciales, cierres y efectos de redondeo deben acordarse antes de implementar equivalencias.

Las dos réplicas sintéticas sustituyen todos los códigos, nombres y entradas de notas; mantienen fórmulas y caches coherentes elegidos sintéticamente. Se retiraron metadatos personales, dibujos y anotaciones. Se comprobó igualdad de **todos los encabezados de filas 5–6, fórmulas y celdas combinadas**. El generador falla si cambia la estructura esperada. No se publica ningún XLSX; se publica su generador y descripción técnica.

## Pruebas y alcance de las conclusiones

Los [resultados estructurados](auditoria-fase4a-resultados.json) registran **74 comprobaciones: 49 verificadas, 24 discrepancias y una no verificable** por dependencia del parser que falla. Son comprobaciones individuales, no 24 causas independientes. La matriz clasifica requisitos completos, que pueden agrupar varias comprobaciones.

| Ejecución | Evidencia |
| --- | --- |
| HTTP/API por Nginx a PostgreSQL sintético | 35 comprobaciones: importación, validación, reintentos, identidades, permisos, componentes, notas, asistencia y seguimiento. |
| Navegador Edge headless con contexto nuevo | 24 comprobaciones: ocho pantallas académicas, búsqueda, selección/arrastre, corrección/confirmación de CSV, matriz manual, asistencia grupal, seguimiento, reportes y portal familiar. Ninguna quedó sin ejecutar en el intento final. |
| UI adicional | Cuatro comprobaciones: criterio opcional, peso, lectura tras recarga y alta de docente desde formulario. |
| Reproducciones complementarias | Ocho: parser, XLSX plano, ausencia de notas, ámbito docente, componente ajeno, renombrado/desactivación e historial. |
| Reinicio de PostgreSQL/API/frontend | Tres: inventario completo idéntico de 15 tablas, nota importada/nota cero con el mismo alumno, asistencia/seguimiento/configuración legibles. |
| Regresión anterior | 52 pruebas del backend pasaron en otro PostgreSQL desechable; 22 avisos de deprecación. No detectaban todas las brechas anteriores. |

La prueba de impresión produjo un PDF mediante el motor de impresión del navegador en la vista existente. No acredita un endpoint PDF propio ni todas las opciones de un diálogo de impresión interactivo. La navegación acredita que una pantalla carga, no que todos sus formularios estén correctos. Los errores y permisos observados se diferencian de las ausencias deducidas por revisión de código/esquema en la [matriz](auditoria-fase4a-matriz.md).

Entornos usados: `paideia-dev-phase4a`, puerto 14204, PostgreSQL en tmpfs para recorridos; `paideia-dev-phase4apersist`, puerto 14205, volumen **nuevo y exclusivamente sintético** para probar el reinicio real de PostgreSQL; `paideia-phase4a-regression`, tmpfs para regresión. Un tmpfs no conserva datos al reiniciar su contenedor; por eso se usó almacenamiento desechable independiente con volumen para esa prueba específica. Nunca se montó el volumen institucional.

Los primeros intentos del harness de navegador fallaron por selectores de etiquetas y fueron corregidos únicamente en las pruebas. La ejecución final sustituyó esos resultados no concluyentes. Los reintentos del harness generan más registros sintéticos, reforzando la observación de duplicación; los conteos de cada comprobación pertenecen al momento registrado. El script de auditoría registra discrepancias y puede terminar con código 0; eso significa que el harness terminó, **no que el sistema cumpla todos los requisitos**.

## Plan propuesto en tareas pequeñas

| Orden | Tarea | Criterio de aceptación |
| --- | --- | --- |
| P0.1 | Corregir propagación de encabezados combinados y lectura institucional, manteniendo CSV/XLSX planos y aliases existentes. | Ambas réplicas pasan; vacíos no son notas, las diez entradas sintéticas se identifican sin importar promedios. |
| P0.2 | Acordar y aplicar identidad de evaluación y política de reintento/actualización; no deduplicar notas existentes automáticamente. | Mismo archivo y doble clic no generan duplicados; conflictos requieren decisión y quedan trazados. |
| P0.3 | Unificar validación servidor: alumno, curso, periodo/fecha, componente del mismo curso, nota y asistencia. | Rechazos claros 4xx, lote atómico, ningún 500 por componente inválido, sin regresiones del padrón. |
| P0.4 | Reparar ámbito docente en resúmenes y coherencia de roles UI/API de reportes/importación. | Un docente no obtiene agregados de cursos ajenos; permisos aprobados funcionan y los denegados se explican. |
| P0.5 | Diseñar versiones/auditoría antes de ampliar configuración; mantener registros antiguos. | Cambiar peso/criterio no altera resultados históricos silenciosamente; actor y versión recuperables. |
| P1.1 | Revalidar borradores corregidos y presentar errores por fila/columna. | Corregir 99→15 habilita confirmar; un vacío nunca se interpreta como cero en cliente; errores de servidor siguen visibles y accionables. |
| P1.2 | Relacionar evidencias importadas con componentes válidos del curso/periodo y resolver identidades antes de confirmar. | Criterios institucionales y personalizados se mapean explícitamente; desconocidos/ambiguos no llegan al commit. |
| P1.3 | Hidratar matriz desde notas existentes y definir guardado de lote seguro. | Recarga muestra valores guardados; guardar nuevamente no duplica; fallos no dejan una matriz parcialmente guardada. |
| P1.4 | Definir calendario de cuatro/ocho semanas y gestión de años/periodos. | Un año distinto de 2026 aparece; bloques no se equiparan automáticamente a meses; no inventar fechas. |
| P1.5 | Acordar plantilla, vacíos, ponderaciones y redondeos con referencia a las fórmulas reales. | Cálculos reproducibles y coherentes entre UI, API, exportación y versiones históricas. |
| P1.6 | Implementar incrementalmente competencias/orden, plantilla y restauración, fórmulas seguras y preview de impacto, después de P0.5. | Fórmulas sin código arbitrario, permisos por curso/periodo, versiones y vista previa antes de persistir. |
| P2.1 | Completar gestión de usuarios y catálogos según ERS original, sin borrar opciones adicionales. | Desactivación/reativación trazable, formularios y restricciones acordados; cotejar campos personales antes de añadirlos. |
| P2.2 | Completar reportes y seguimiento: fechas/autores, datos insuficientes y cálculo unificado. | Ausencia de evidencia no figura como cero/riesgo alto; historial legible y exportación coherente. |
| P2.3 | Ampliar regresión visual, formatos `.xls`, accesibilidad, móvil y fallos de red/reintentos. | Cobertura reproducible del recorrido completo en navegador; no basta una prueba de runner. |

Ninguna tarea de corrección se implementó. Mantener la protección de Fase 1 y las condiciones de operación de Fase 2/3. No ejecutar corrección masiva, borrado de duplicados, recálculo ni migraciones institucionales sin diseño y autorización.

## Archivos, protección y reproducción

Las fases 1–3 no tenían commit de respaldo: se creó `1d346eb` antes de auditar, seleccionando explícitamente 40 archivos y comprobando exclusión de `.env`, configuraciones privadas, padrones, Excel y respaldos. No se modificó código de backend/frontend ni migraciones en Fase 4A. Se añadieron únicamente `docker-compose.audit.yml`, scripts de auditoría y estos documentos/resultados; los enlaces de contexto se actualizan para futuras sesiones.

Una inspección institucional de **solo lectura** comparó conteos, huellas de filas y esquema de las 15 tablas con el inventario posterior a recuperación: cero cambios. Servicios originales saludables; ningún reinicio, migración, escritura, push o merge en ellos.

Artefactos sintéticos y entorno Python de navegador: `%LOCALAPPDATA%/Paideia/audit-phase4a`, fuera de Git/OneDrive. Los archivos de configuración están ignorados en `config/local`. Los proyectos de auditoría se detienen al finalizar, sin borrar volúmenes ni usar reset/prune. El volumen sintético de persistencia se conserva.

Para repetir en una **instancia sintética nueva**, consultar [reproduccion-fase4a.md](reproduccion-fase4a.md). No repetir los scripts de escritura sobre la base institucional ni interpretar el nombre de proyecto como autorización para usar un volumen existente desconocido.
