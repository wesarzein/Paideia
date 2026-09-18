# Desarrollo

## Docker

```bash
cp .env.example .env
docker compose up --build
```

## Backend local

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Frontend local

Angular 22 requiere Node.js 22.22.3+, 24.15.0+ o 26+.

```bash
cd frontend
npm ci
npm start
```

## Make en Windows

Si `make` no esta disponible, ejecutar directamente los comandos equivalentes de Docker, Pytest y npm.
