# Diseno de base de datos

## Tablas iniciales

- `users`: usuarios del sistema con `password_hash`.
- `roles`: roles institucionales.
- `students`: estudiantes.
- `academic_periods`: periodos academicos.
- `grades`: grados.
- `sections`: secciones asociadas a grados.
- `courses`: cursos.

La migración `0001_initial_structure` se ejecuta automáticamente al iniciar el contenedor del backend. El MVP utiliza actualmente `students` para el alta, consulta, búsqueda, actualización y baja desde la interfaz Angular.

## Modelo previsto

`permissions`, `enrollments`, `evaluations`, `grades_records`, `attendance`, `academic_follow_up`, `risk_predictions`, `interventions`, `imports`, `import_errors` y `audit_logs` se agregaran por sprint.

## Criterios

UUID como identificador interno, claves foraneas, 3FN, timestamps timezone-aware y datos en UTF-8.
