[CmdletBinding()]
param(
    [string]$OutputDirectory = "database/backups"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$environmentFile = Join-Path $projectRoot "config/local/phase4b3ui.env"

if (-not (Test-Path -LiteralPath $environmentFile)) {
    throw "No se encontró $environmentFile. Ejecuta el script desde una copia configurada del proyecto."
}

function Get-EnvironmentValue([string]$Name) {
    $line = Get-Content -LiteralPath $environmentFile | Where-Object { $_ -match "^$([regex]::Escape($Name))=" } | Select-Object -First 1
    if (-not $line) { throw "Falta $Name en $environmentFile." }
    return $line.Substring($Name.Length + 1).Trim('"')
}

$databaseUser = Get-EnvironmentValue "POSTGRES_USER"
$databaseName = Get-EnvironmentValue "POSTGRES_DB"
$targetDirectory = Join-Path $projectRoot $OutputDirectory
New-Item -ItemType Directory -Force -Path $targetDirectory | Out-Null

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$fileName = "paideia-presentacion-$timestamp.dump"
$outputPath = Join-Path $targetDirectory $fileName
$compose = @("compose", "--env-file", $environmentFile, "-f", (Join-Path $projectRoot "docker-compose.environment.yml"))
$containerId = (& docker @compose "ps" "-q" "postgres").Trim()
if (-not $containerId) { throw "No se encontró el contenedor PostgreSQL. Inicia el entorno con Docker Compose." }

Write-Host "Exportando datos institucionales..."
& docker exec $containerId pg_dump -U $databaseUser -d $databaseName --schema=public --format=custom --file="/tmp/$fileName"
if ($LASTEXITCODE -ne 0) { throw "No se pudo crear el respaldo de la base de datos." }

& docker cp "${containerId}:/tmp/$fileName" $outputPath
& docker exec $containerId rm -f "/tmp/$fileName"
if ($LASTEXITCODE -ne 0) { throw "No se pudo copiar el respaldo fuera del contenedor." }

Write-Host "Respaldo creado: $outputPath"
Write-Host "Compártelo por un medio privado. No lo subas a Git."
