INSERT INTO roles (id, code, name, created_at)
VALUES
  (gen_random_uuid(), 'admin', 'Administrador', NOW()),
  (gen_random_uuid(), 'teacher', 'Docente', NOW()),
  (gen_random_uuid(), 'coordinator', 'Coordinador', NOW()),
  (gen_random_uuid(), 'director', 'Directivo', NOW()),
  (gen_random_uuid(), 'student', 'Estudiante', NOW()),
  (gen_random_uuid(), 'parent', 'Padre de familia', NOW())
ON CONFLICT (code) DO NOTHING;
