# Acceso administrativo a grados y secciones — 10/10/2026

Se añadió la entrada «Grados y secciones» al menú del administrador y la ruta
`/grados-secciones`, protegida por el guard de roles existente. Reutiliza el gestor
de Cursos con sus formularios abiertos. Permite elegir Primaria/Secundaria al crear
un grado y asociar cada sección al grado elegido. El gestor anterior sigue disponible.
No se añadieron grados ficticios al catálogo ni se cambiaron códigos o matrículas.

Validación: compilación Angular aprobada; cinco pruebas del gestor y tres regresiones
de importación aprobadas. Nueve casos PostgreSQL del catálogo aprobados en esquemas
UUID, incluidos permisos de cinco roles, identidad escolar, persistencia y concurrencia.
Navegador inicial: menú de administrador, dos formularios visibles, ambos niveles y asociación
de sección. Cero
errores JS; sin escrituras del recorrido visual. Frontend actualizado exclusivamente
en `paideia-dev-phase4b3ui`, `127.0.0.1:14211`.

Corrección posterior de permisos: el docente también accede a esta ruta en modo
consulta. Los GET de grados y secciones filtran sus asignaciones por cuenta docente;
crear el catálogo por sí solo no otorga acceso. El administrador debe vincular el
curso, grado y sección a una cuenta docente. Ya no se admite una asignación nueva
con solo el nombre libre del docente.

Las escrituras de cursos, componentes/configuración de evaluación, periodos,
alumnos, matrículas y asignaciones, y la importación de alumnos, exigen administrador
en la API. La interfaz docente oculta los formularios y conserva consulta, notas,
importación de calificaciones, analíticas, IA y reportes.

Validación de esta corrección: 36 pruebas PostgreSQL en esquemas UUID y 18 pruebas
frontend aprobadas; compilación Angular aprobada. Recorrido de interfaz con rol
docente simulado en almacenamiento local: catálogo de consulta, controles CRUD
ocultos, importación solo de calificaciones, cero errores JS y cero escrituras.
La autorización real y el alcance de asignaciones se verificaron en PostgreSQL.
Backend y frontend del laboratorio actualizados y saludables. La huella de las diez
notas originales permanece intacta; se observaron además 160 notas nuevas durante
la sesión, sin alterarlas ni eliminarlas.
