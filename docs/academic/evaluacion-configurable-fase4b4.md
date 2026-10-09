# Fase 4B.4: componentes iniciales sin Docker

Fecha: 09/10/2026. Rama: `dev/phase4b4-evaluation-offline`.
Autorización: desarrollar progresivamente con pruebas locales ligeras, manteniendo
Docker pausado y sin tocar la instalación institucional. Esto no cierra [4B.3](importacion-institucional-fase4b3.md).

## Alcance implementado y evidencia

| Componente | Implementación | Validación actual |
| --- | --- | --- |
| Competencias | Identificador estable, nombre, orden, estado; asociación de criterios y rechazo de referencias a competencias inactivas/inexistentes | Pruebas de dominio en memoria |
| Criterios | Adición/edición mediante nuevos documentos, dos bloques, orden, peso, opcionalidad, desactivación lógica, encabezado Excel y vínculo opcional al componente existente | Pruebas de dominio; conserva objetos anteriores |
| Ponderaciones | Reutiliza rango existente 0–100 y pesos relativos; denominador positivo por bloque; rechaza negativos, booleanos y no finitos | Pruebas de dominio; sin nuevas reglas de suma 100 |
| Fórmulas | Lenguaje numérico acotado, validación de referencias/ciclos y previsualización; operaciones +, −, ×, ÷; SUM, MEAN, MIN, MAX, ROUND | Pruebas de seguridad y aritmética |
| Plantilla | Dos bloques, cinco criterios por bloque, media mensual/final a un decimal y literal institucional existente | Comparación aritmética con fórmulas inspeccionadas de 4B.3 |
| Conversión de componentes | Copia componentes adicionales, opcionales e inactivos, conservando sus UUID; no escribe ni sustituye los originales | Pruebas de dominio |
| Revisiones | Curso/periodo, actor, motivo, fecha UTC, versión anterior, JSON inmutable y huella SHA-256; rechazo de revisión obsoleta/cambio de ámbito; restablecimiento produce otra revisión | Pruebas de dominio; **no persistido en PostgreSQL** |
| Compatibilidad Excel | Correspondencia por bloque y encabezado normalizado; nombres repetidos entre bloques permitidos; columnas derivadas excluidas | Pruebas de mapeo; **sin integración nueva en el importador** |
| API de plantilla/previsualización | Dos rutas en el router de cursos, reutilizando roles de lectura y asignaciones docentes existentes | Sintaxis y revisión estática; **HTTP/permisos no ejecutados** |

No se incorporaron pantallas nuevas, publicación persistente, migraciones ni recálculos
de notas. Las funciones anteriores de cursos, componentes, pesos e importación siguen
en sus rutas existentes. Las notas continúan usando `weighted_mean_v1` y los snapshots
de 0012; la identidad y la confirmación de 0013 no se modificaron.

## Archivos y contratos

- `backend/app/services/safe_formula.py`: intérprete limitado, sin ejecución de código.
- `backend/app/services/evaluation_configuration.py`: documentos, plantilla,
  conversión, mapeo Excel, previsualización y construcción de revisiones.
- `backend/app/schemas/courses.py`: `EvaluationPreviewRequest` conserva valores crudos
  para rechazar booleanos en lugar de convertirlos en notas.
- `backend/app/endpoints/courses.py`: `GET /courses/{course_id}/evaluation-template?period_id=...`
  y `POST /courses/{course_id}/evaluation-preview` con `{configuration, scores}`.
  Las rutas no publican configuraciones ni escriben calificaciones.
- `backend/tests/offline/`: pruebas exclusivamente con biblioteca estándar.

El documento indica `schema_version=1`, `formula_language=paideia_numeric_v1`,
`weight_mode=relative_legacy`, cuatro semanas por bloque y ocho por bimestre.
No asigna fechas de calendario ni identifica automáticamente un bimestre.
Los criterios conservan su clave al reordenarse; las posiciones no generan IDs.
No se inventaron nombres de competencias institucionales.

## Reglas y límites explícitos

- Vacío se representa como `None`, nunca como cero. Cero explícito es un dato válido.
  Falta de criterio obligatorio con peso positivo bloquea el resultado final de vista previa.
- La media ponderada de diagnóstico y las fórmulas son resultados separados.
  **Modificar pesos no reescribe una fórmula explícita.** El docente deberá revisar ambas;
  la previsualización no publica ni consolida resultados académicos.
- Se conservan opcionalidad y criterios adicionales existentes. El promedio de
  diagnóstico omite opcionales ausentes; una fórmula que los referencia permanece
  incompleta. La política institucional de entradas parciales/optativas debe confirmarse
  antes de integrar publicación y cálculo oficial.
- `ROUND` admite 0–4 decimales, con redondeo decimal de mitad hacia arriba, contrastado
  con el caso institucional. Las expresiones no son cadenas Excel ejecutables: no
  hay macros, acceso al sistema, atributos, índices, importaciones ni funciones arbitrarias.
- Máximo 512 caracteres, 128 nodos y profundidad 20 por expresión; magnitud numérica
  hasta 1e9, precisión limitada y exponentes entre −28 y 9. Configuraciones con hasta
  64 criterios, 32 competencias y 32 fórmulas; esos límites no garantizan que cualquier
  combinación quepa en una sola fórmula. No se descartan componentes para hacerla caber.
- La huella detecta cambios de contenido; **no es una firma de autenticación ni una
  garantía transaccional**. La comparación de revisión anterior es local al dominio;
  la publicación concurrente exigirá garantías PostgreSQL.
- Los permisos actuales de modificación no se ampliaron. Las rutas nuevas son de
  lectura/previsualización: admin, coordinator, director y docentes con el curso asignado.
  Los permisos de publicación/restablecimiento y restricciones institucionales están pendientes.

## Pruebas realizadas

**26 pruebas locales aprobadas**, 0,034 segundos en la última ejecución: nueve del
motor y diecisiete de configuración. Casos: fórmulas institucionales, precisión y
redondeos, expresiones inseguras, límites de complejidad/exponentes, ceros/vacíos,
escala, ponderaciones, adición/edición/orden/desactivación, encabezados repetidos,
componentes adicionales, ciclos, serialización, cambios de ámbito, revisiones obsoletas,
conservación de contenido anterior y restablecimiento como nueva revisión.

Reproducción desde la raíz, sin instalar dependencias ni iniciar aplicaciones:

```powershell
$env:PYTHONPATH = 'backend'
python -B -m unittest discover -s backend/tests/offline -v
```

También se comprobó sintaxis Python mediante AST y `git diff --check`.
FastAPI, Pydantic, SQLAlchemy y Ruff no están instalados en los intérpretes locales
revisados; no se descargaron dependencias para esta sesión. No se ejecutaron las
92 pruebas anteriores ni pruebas Docker, PostgreSQL o navegador.

## Tareas siguientes, pequeñas y ordenadas

1. Probar las dos rutas con FastAPI y datos aislados: autenticación, roles, asignaciones,
   curso/periodo ajenos, documentos inválidos y ausencia de escrituras.
2. Preparar almacenamiento de revisiones PostgreSQL: documento completo por curso/periodo,
   versiones anexadas, referencia a la anterior, autor/motivo, unicidad y control concurrente.
   Diseñar y probar migración aditiva posterior a 0013. **Todavía no hay migración nueva.**
3. Implementar publicación/restablecimiento explícitos con vista previa y permisos
   institucionales; confirmar tratamiento de opcionales/parciales y fórmulas frente a pesos.
4. Asociar notas nuevas a la revisión correspondiente. Resolver el trigger de captura
   de 0012 mediante una migración posterior probada; conservar los snapshots anteriores.
   No retocar retrospectivamente 0012/0013 ni reconstruir configuración histórica desconocida.
5. Incorporar edición de documentos en la pantalla de cursos conservando las opciones
   existentes; comprobar formularios y recorrido en navegador cuando sea seguro.
6. Conectar el mapeo de criterios con el parser/importador existente, preservando
   identidad, confirmación de diferencias, fechas explícitas y rollback.
7. Validar PostgreSQL aislado, concurrencia, publicación/versionado, consultas históricas
   y reinicio. Retomar también la persistencia pendiente de 4B.3.

Los pasos que requieren Docker o datos persistentes permanecen pendientes de un entorno
seguro. El código implementado en esta entrega no acredita funcionamiento completo de 4B.4.
