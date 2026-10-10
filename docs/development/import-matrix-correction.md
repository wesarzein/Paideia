# Corrección de importación institucional — 10/10/2026

- La plantilla institucional mantiene una fila visual por alumno y diez columnas de
  notas, agrupadas en 1 MES y 2 MES. La API conserva su representación interna por
  nota para reutilizar validación, permisos, identidad y revisión de concurrencia.
- La correspondencia se valida por código, nombre y grupo en el servidor, sin
  checkboxes por alumno. Cero es una nota válida; las celdas vacías se omiten.
  Una edición invalida la revisión previa. Las actualizaciones requieren una
  confirmación final conjunta y conservan los tokens de concurrencia por nota.
- La interfaz activa por defecto «Solo corregir notas existentes». El servidor
  omite nuevas identidades en ese modo; las actualizaciones conservan ID,
  configuración histórica y observaciones que la plantilla no proporciona.
- El mismo XLSX permite importar el padrón, sin arrastrar columnas de notas. Se
  conservan los nombres completos de referencia. Se reutiliza la separación del
  catálogo cuando código y nombre coinciden. Para alumnos nuevos, una coma separa
  apellidos de nombres; sin coma se propone para revisión la separación después
  de las dos primeras palabras. La interfaz explica esta propuesta y permite
  corregir apellidos compuestos antes de confirmar.
- El padrón actualiza por código existente dentro del grado/sección, omite
  coincidencias y conserva identidades. Los códigos externos con nombre exacto y
  único en el grupo no recrean al alumno. Ambigüedades, referencias repetidas y
  códigos de otros grupos se rechazan. Las operaciones son transaccionales y
  serializan la asignación de códigos por sección.

## Evidencia

- Archivo adjunto leído sin guardar datos: 16 alumnos, 160 notas, dos bloques de
  cinco criterios y cero errores de lectura. No se copiaron nombres a fixtures.
- Backend: 35 pruebas PostgreSQL aprobadas de plantilla, identidad y corrección;
  después, tres pruebas focalizadas aprobadas con el caso adicional de conservación
  de observaciones (36 casos distintos en total). Esquemas UUID desechables.
- Frontend: compilación Angular y tres pruebas de agrupación, cero/celdas vacías,
  invalidación de revisión y envío del modo de corrección aprobadas.
- Navegador en la versión inicial: 16 filas, 160 entradas numéricas, 16 selectores
  y 16 confirmaciones; validación al editar una nota fuera de rango y padrón de
  16 filas. Cero errores JavaScript y ningún commit de alumnos/notas.
- Laboratorio permitido: `paideia-dev-phase4b3ui`, `127.0.0.1:14211`. La base
  encontrada estaba en 0013 y tenía 10 notas. Se respaldó en
  `%LOCALAPPDATA%/Paideia/audit-phase4b3/import-review-before.dump`, se aplicaron
  las migraciones existentes 0014–0018 y se actualizaron backend/frontend.
  Comparación de todas las columnas originales contra el respaldo: las diez
  notas completas, incluidos sus snapshots, permanecen idénticas.
- No hubo publicación, push ni modificación de la instalación `paideia`.

## Corrección del bloqueo de alumnos

La primera comprobación visual verificó el número de filas, pero no el botón de
confirmación. Dejar nombres/apellidos vacíos bloqueaba la carga inicial con el
archivo sin comas. Ahora ambos campos se completan con la propuesta descrita arriba,
conservando siempre el nombre completo original. Se muestran los errores concretos
de la API y se recarga el catálogo después de guardar alumnos.

Validación posterior: 13 pruebas backend focalizadas y cinco frontend aprobadas.
Incluyen importar 16 alumnos nuevos con nombres sin coma, revisar sus 160 notas,
importar notas iniciales, reimportar sin duplicados y conservar la separación de
apellidos compuestos de alumnos existentes. PostgreSQL exclusivamente en UUID.
En navegador con el archivo adjunto: 16 nombres y 16 apellidos no vacíos y botón de
importación habilitado después de seleccionar nivel/grado/sección, sin guardar datos.
Backend y frontend actualizados en el laboratorio permitido; no se requieren
migraciones nuevas. Para cargar notas inicialmente hay que desactivar el modo
«Solo corregir notas existentes»; ese modo sigue activado por defecto para las
correcciones solicitadas originalmente.

## Simplificación del flujo y avisos

El contexto se selecciona antes de habilitar la carga del archivo: nivel, grado,
sección y, para calificaciones, curso, periodo, año, bimestre, modo de carga y
nombres/fechas de los dos bloques. La vista previa presenta ese contexto como
resumen y permite editar únicamente notas; cambiar el grupo descarta el archivo
y la revisión anterior. La importación de alumnos conserva edición de nombres.

«Guardar calificaciones» realiza la revisión automáticamente, presenta un diálogo
nativo accesible con los conteos de actualizaciones/nuevas/omitidas y solo envía el
commit después de confirmar. Los errores se anuncian con role=alert; los resultados
distinguen notas creadas, actualizadas, sin cambios y rechazadas. Los datos inválidos
explican el bloqueo mediante avisos; no hay botón silenciosamente deshabilitado por
confirmaciones pendientes. Si se usa solo correcciones para una carga inicial, el
resultado explica por qué las notas nuevas se omiten.

Evidencia final: Angular compila y 11 pruebas frontend focalizadas pasan, incluidas
confirmación conjunta de diferencias, errores de revisión/commit, notas fuera de
rango y descarte de contexto. Recorrido real con el XLSX: selección previa de grupo,
16 filas/160 entradas, cero checkboxes, contexto sin controles en la vista previa,
diálogo final y POST real aprobado (160 notas idénticas omitidas, cero escrituras de
notas). Se comprobó también la tabla con desplazamiento en viewport móvil de 390 px.
Cero errores JS. Los 170 registros completos y sus snapshots conservaron la huella
SHA256 `2a73014ff5a63eb07468b0edbe58a0e8bd2ba99529a86386a31d706f8e44926a`.
Frontend actualizado únicamente en el laboratorio `127.0.0.1:14211`.
