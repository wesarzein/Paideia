[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$DumpPath
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$environmentFile = Join-Path $projectRoot "config/local/phase4b3ui.env"
$resolvedDump = (Resolve-Path -LiteralPath $DumpPath).Path

if (-not (Test-Path -LiteralPath $environmentFile)) {
    throw "No se encontró $environmentFile. Configura primero el entorno local."
}

function Get-EnvironmentValue([string]$Name) {
    $line = Get-Content -LiteralPath $environmentFile | Where-Object { $_ -match "^$([regex]::Escape($Name))=" } | Select-Object -First 1
    if (-not $line) { throw "Falta $Name en $environmentFile." }
    return $line.Substring($Name.Length + 1).Trim('"')
}

$databaseUser = Get-EnvironmentValue "POSTGRES_USER"
$databaseName = Get-EnvironmentValue "POSTGRES_DB"
$compose = @("compose", "--env-file", $environmentFile, "-f", (Join-Path $projectRoot "docker-compose.environment.yml"))

Write-Warning "Esta operación reemplazará la base local de presentación con los datos de $resolvedDump."
if ((Read-Host "Escribe RESTAURAR para continuar") -cne "RESTAURAR") {
    Write-Host "Importación cancelada."
    exit 0
}

& docker @compose "stop" "backend" "frontend"
if ($LASTEXITCODE -ne 0) { throw "No se pudo detener la aplicación antes de restaurar." }

$containerId = (& docker @compose "ps" "-q" "postgres").Trim()
if (-not $containerId) { throw "No se encontró el contenedor PostgreSQL." }
$temporaryDump = "/tmp/paideia-import-$([guid]::NewGuid().ToString()).dump"

try {
    Write-Host "Restaurando datos institucionales..."
    & docker cp $resolvedDump "${containerId}:$temporaryDump"
    if ($LASTEXITCODE -ne 0) { throw "No se pudo copiar el respaldo al contenedor PostgreSQL." }
    & docker exec $containerId pg_restore -U $databaseUser -d $databaseName --clean --if-exists --no-owner --no-privileges --exit-on-error $temporaryDump
    if ($LASTEXITCODE -ne 0) { throw "No se pudo restaurar el respaldo." }
}
finally {
    & docker exec $containerId rm -f $temporaryDump 2>$null
    & docker @compose "up" "-d" "backend" "frontend"
}

Write-Host "Importación terminada. Espera a que los servicios estén saludables antes de abrir la plataforma."
