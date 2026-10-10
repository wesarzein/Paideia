# Fase 4B.5: integración y estabilización académica

**Actualización segunda laptop, 09/10/2026:** 4B.3 tiene cierre técnico en el volumen
nuevo. PostgreSQL real, contexto manual explícito, configuración publicada frente
a borradores, snapshots estables, identidad de criterios e importación/reimportación
XLSX comprobados. Angular compiló y el laboratorio completo responde saludable en
`127.0.0.1:14211`. La interfaz sigue sin recorrido visual nuevo por RAM insuficiente;
**4B.5 no tiene cierre integral todavía**. Véase
[informe de validación, correcciones y continuación](validacion-segunda-laptop-fase4b.md).

El texto siguiente conserva las condiciones y pendientes de la sesión anterior,
actualizados por el informe enlazado; no describe el estado actual de esta laptop.

Fecha: 09/10/2026. Rama: `dev/phase4b5-academic-stabilization`.

## Condición de ejecución

La sesión comenzó con 0,49 GiB de RAM disponible. Docker Desktop, su servicio y sus
procesos no estaban activos. No se invocó el cliente Docker, no se inició ningún
contenedor y no se creó ninguna imagen, red o volumen. Node/npm tampoco estaban
disponibles. Por estas condiciones no se ejecutaron PostgreSQL, reinicios, Angular ni
Playwright.

## Estado de 4B.3

4B.3 continúa implementada pero **no cerrada**. La evidencia anterior de importación,
consulta e idempotencia permanece válida; sigue faltando observar las mismas diez notas
después de reiniciar PostgreSQL.

Se añadió `scripts/verify_phase4b3_persistence.py` como comprobación ligera para el
laboratorio existente `paideia-dev-phase4b3ui`. El script:

- admite únicamente `config/local/phase4b3ui.env` y valida nombre, base, usuario y modo sintético;
- usa API HTTP, inventario del backend y hashes SHA-256; no importa Playwright;
- exige exactamente diez notas y la corrección previamente observada con valor 5;
- compara IDs, valores, snapshots e inventario antes y después;
- reinicia exclusivamente PostgreSQL y espera la recuperación de la API;
- no crea, reconstruye ni elimina recursos.

El script no fue ejecutado porque hacerlo habría activado Docker contra la instrucción
vigente. Solo un resultado `passed: true` permitirá cambiar 4B.3 a cerrada.

## Integración académica implementada

El registro manual dejó de deducir el bimestre mediante `ceil(mes / 2)`. Ahora solicita
explícitamente:

- bimestre institucional, sin imponer una cantidad máxima no documentada;
- bloque 1 (semana 4) o bloque 2 (semana 8);
- nombre de la evaluación;
- fecha de evaluación;
- curso y periodo.

La consulta por mes se conserva como filtro independiente y no determina el contexto
académico. Si existe una revisión publicada, la matriz usa sus criterios activos del
bloque seleccionado. Los borradores no afectan nuevas notas. Sin publicación se mantienen
los componentes actuales para no interrumpir la funcionalidad existente.

Las nuevas columnas nullable de 0014 son `academic_bimester`, `evaluation_block` y
`evaluation_criterion_key`. Una nota asociada a una revisión publicada requiere las tres.
El backend verifica ámbito, estado publicado, criterio activo y bloque; el snapshot guarda
clave, bimestre, bloque, peso, ID, versión y huella de revisión. El peso procede de la
revisión publicada, no del componente legado. Versiones posteriores no cambian ese snapshot.

La identidad de 0013 se conserva para registros legados. 0014 añade una identidad v2 con
clave estable de criterio para notas configurables, de modo que criterios distintos no se
confundan aunque compartan nombre de evaluación, tipo, fecha o componente. Al reimportar,
la aplicación busca primero la identidad configurable y después una coincidencia legada;
esto evita duplicar notas anteriores que todavía no poseen clave de criterio.

El importador institucional toma bimestre y bloque del contexto confirmado por el docente,
mapea el encabezado contra la revisión publicada y asigna la clave estable. No deduce fechas,
no modifica la confirmación de diferencias y conserva el rollback e idempotencia existentes.

## Migración y pruebas PostgreSQL preparadas

0014 sigue siendo aditiva y reversible y 0012/0013 no se modificaron. Además de las
revisiones, 0014 ahora:

- agrega el contexto académico nullable, sin rellenar datos históricos desconocidos;
- amplía el trigger de snapshots sin reescribir snapshots existentes;
- crea la identidad v2 manteniendo la función de 0013 para filas legadas;
- restaura las funciones de 0012/0013 durante el downgrade antes de retirar sus columnas.

Se generó correctamente el SQL offline de upgrade y downgrade. La prueba PostgreSQL
preparada cubre una migración desde cero y un ciclo 0014 → 0013 → 0014 con una nota
legada existente, comprobando ID, valor, peso, snapshot y columnas nuevas en `NULL`.
También cubre concurrencia, historial append-only, snapshots y dos criterios distintos
con las demás dimensiones iguales.

La salvaguarda de pruebas permite reutilizar la base sintética de `phase4b3ui` únicamente
cuando `PAIDEIA_TEST_PROJECT=paideia-dev-phase4b3ui`; cada prueba usa un esquema UUID
aislado. Cualquier otro host, base o usuario continúa rechazado. No se toca el esquema
`public` poblado por 4B.3.

## Validación local realizada

- 33 pruebas focalizadas aprobadas en la ejecución principal (dominio, API y SQLite).
- 13 pruebas adicionales de esquemas y evidencias aprobadas.
- Las tres pruebas PostgreSQL se recolectaron y omitieron por ausencia del entorno.
- OpenAPI generó las ocho rutas de plantilla, vista previa, revisión actual,
  configuración activa publicada, historial, borrador, publicación y restauración.
- SQL offline Alembic de upgrade/downgrade generado sin error.
- Ruff focalizado y AST Python aprobados.
- Archivos TypeScript en UTF-8 y literales de plantilla balanceados.

Estas comprobaciones no equivalen a PostgreSQL, compilación Angular ni navegador.

## Única ejecución posterior

Cuando el responsable reactive Docker con memoria suficiente, el cierre debe usar solo
`paideia-dev-phase4b3ui` y ejecutarse secuencialmente:

1. Ejecutar el verificador ligero de 4B.3 y conservar su salida JSON.
2. Reconstruir una vez backend y frontend del mismo proyecto, porque las imágenes actuales
   no contienen 0014 ni la interfaz 4B.5.
3. Ejecutar las pruebas PostgreSQL en esquemas aislados de esa misma base sintética.
4. Ejecutar migraciones solo en una copia/esquema aislado; no migrar todavía el esquema
   poblado de 4B.3 hasta revisar los resultados.
5. Compilar Angular y corregir únicamente errores comprobados.
6. Ejecutar un recorrido esencial de navegador: configuración → borrador → publicación →
   registro con bimestre/bloque → consulta → versión posterior → historia estable.

## Pendientes y decisiones institucionales

- Evidencia real de reinicio para cerrar 4B.3.
- PostgreSQL real para 0014, instalación limpia, actualización y concurrencia.
- Compilación Angular y validación visual del editor y la matriz manual.
- Fórmulas configurables como cálculo oficial de consultas: continúan en previsualización.
  No se habilitó su uso oficial porque falta confirmar la política de criterios opcionales,
  entradas parciales y precedencia entre pesos y fórmulas.
- Despliegue institucional de 0012–0014 requiere respaldo verificado y autorización separada.

Estado: 4B.3 pendiente de reinicio; 4B.4/4B.5 implementadas y probadas localmente, pero
pendientes de PostgreSQL y navegador antes de declararlas cerradas.
