INSERT INTO users (id, role_id, email, password_hash, full_name, created_at, updated_at)
SELECT gen_random_uuid(), r.id, 'admin@paideia.local', '$argon2id$v=19$m=65536,t=3,p=4$A4n6q0jv3w9E0KxM9+Qdsg$orJ2LZ3AMf4c9bT7jVYm2iLQj9AnI0v7zA0R4qDiTnM', 'Administrador Demo', NOW(), NOW()
FROM roles r
WHERE r.code = 'admin'
ON CONFLICT (email) DO NOTHING;
