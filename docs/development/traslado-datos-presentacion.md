# Trasladar datos para una presentación

Git contiene el código, no la base de datos local. Para mostrar los mismos alumnos, notas, asistencia, usuarios y asignaciones en otra laptop, crea y restaura un respaldo privado de PostgreSQL. El respaldo incluye solamente el esquema activo `public` del proyecto.

En la laptop que tiene los datos, desde la raíz del proyecto:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\export-presentation-data.ps1
```

El archivo se crea en `database/backups` con extensión `.dump`. Esa carpeta está ignorada por Git. Transfiere el archivo por Drive, USB u otro canal privado.

En la laptop de presentación, primero descarga el mismo commit de Git, configura `config/local/phase4b3ui.env` y levanta Docker Compose. Luego ejecuta:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\import-presentation-data.ps1 -DumpPath "C:\Ruta\paideia-presentacion-AAAAMMDD-HHMMSS.dump"
```

El script solicita escribir `RESTAURAR`, detiene temporalmente la aplicación, reemplaza la base local de destino y vuelve a iniciar backend y frontend. No subas el archivo `.dump` a Git: incluye datos institucionales.
