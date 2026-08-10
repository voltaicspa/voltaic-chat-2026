# =====================================================================
#  Carga en Vercel las variables que Catalina necesita para funcionar.
#
#  Las claves NO van escritas en este archivo: se leen de las variables
#  de usuario de Windows, que ya estan configuradas en este PC. Lo unico
#  que se pide por teclado es lo que falte.
#
#  Uso: clic derecho -> "Ejecutar con PowerShell"
#       o:  powershell -ExecutionPolicy Bypass -File subir_claves_vercel.ps1
# =====================================================================

# El CLI de Vercel escribe su banner en stderr. Con ErrorActionPreference="Stop"
# PowerShell lo toma como error fatal y corta el script, aunque el comando haya
# funcionado. Por eso se deja en Continue y se revisa $LASTEXITCODE a mano.
$ErrorActionPreference = "Continue"
if (Get-Variable PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
    $PSNativeCommandUseErrorActionPreference = $false
}
Set-Location $PSScriptRoot

$VARIABLES = @(
    @{ Nombre = "SIMLI_API_KEY";       Para = "la cara de Catalina (Simli)";        Obligatoria = $true  },
    @{ Nombre = "ELEVENLABS_API_KEY";  Para = "la voz";                             Obligatoria = $true  },
    @{ Nombre = "QWEN_API_KEY";        Para = "el cerebro que responde";            Obligatoria = $true  },
    @{ Nombre = "QWEN_BASE_URL";       Para = "el dominio del workspace de Qwen";   Obligatoria = $true  },
    @{ Nombre = "CATALINA_PANEL_PASS"; Para = "el panel de datos /catalina/datos";  Obligatoria = $false }
)

$ENTORNOS = @("production", "preview", "development")

Write-Host ""
Write-Host "  Cargar claves de Catalina en Vercel" -ForegroundColor Cyan
Write-Host "  -----------------------------------" -ForegroundColor Cyan
Write-Host ""

# --- 1. Vercel CLI ----------------------------------------------------
$vercel = Get-Command vercel -ErrorAction SilentlyContinue
if (-not $vercel) {
    Write-Host "  No esta instalado el CLI de Vercel." -ForegroundColor Yellow
    Write-Host "  Instalalo con:  npm i -g vercel" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  (Si no tienes npm, puedes cargar las variables a mano en"
    Write-Host "   vercel.com -> tu proyecto -> Settings -> Environment Variables)"
    Read-Host "`n  Enter para salir"
    exit 1
}

# --- 2. Sesion iniciada ----------------------------------------------
$quien = (& vercel whoami 2>&1 | Out-String).Trim()
if ($LASTEXITCODE -ne 0) {
    Write-Host "  No hay sesion iniciada en Vercel. Abriendo el login..." -ForegroundColor Yellow
    & vercel login
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  No se pudo iniciar sesion." -ForegroundColor Red
        Read-Host "`n  Enter para salir"; exit 1
    }
} else {
    # whoami puede traer lineas de banner: nos quedamos con la ultima.
    $usuario = ($quien -split "`n" | Where-Object { $_.Trim() } | Select-Object -Last 1).Trim()
    Write-Host "  Sesion de Vercel  : $usuario" -ForegroundColor Green
}

# --- 3. Proyecto vinculado -------------------------------------------
# No basta con que exista .vercel: el enlace puede apuntar a un equipo al que
# ya no se tiene acceso, y ahi Vercel responde "Could not retrieve Project
# Settings". Se comprueba de verdad y, si esta obsoleto, se vuelve a vincular.
function Test-EnlaceValido {
    if (-not (Test-Path ".vercel\project.json")) { return $false }
    $salida = & vercel env ls production 2>&1 | Out-String
    return ($LASTEXITCODE -eq 0)
}

$PROYECTO_ESPERADO = "voltaic-chat"

if (-not (Test-EnlaceValido)) {
    if (Test-Path ".vercel\project.json") {
        Write-Host "`n  El enlace con Vercel esta obsoleto (apunta a un equipo" -ForegroundColor Yellow
        Write-Host "  al que ya no tienes acceso). Hay que volver a vincularlo." -ForegroundColor Yellow
        $respaldo = ".vercel_obsoleto_{0}" -f (Get-Date -Format "yyyyMMdd_HHmmss")
        Move-Item ".vercel" $respaldo
        Write-Host "  El enlace anterior quedo guardado en: $respaldo" -ForegroundColor DarkGray
    } else {
        Write-Host "`n  Este directorio no esta vinculado a un proyecto de Vercel." -ForegroundColor Yellow
    }

    # Una misma cuenta puede tener varios equipos y el proyecto vive en uno
    # solo. Si el equipo activo no lo tiene, "link" solo ofreceria crear uno
    # nuevo con OTRA url, que no es lo que queremos. Por eso se busca primero.
    $equipoOk = $false
    $salidaLs = & vercel ls 2>&1 | Out-String
    if ($salidaLs -match [regex]::Escape($PROYECTO_ESPERADO)) {
        $equipoOk = $true
    } else {
        Write-Host "`n  El equipo activo no tiene el proyecto '$PROYECTO_ESPERADO'." -ForegroundColor Yellow
        Write-Host "  Equipos disponibles en tu cuenta:" -ForegroundColor Cyan
        & vercel teams ls 2>&1 | Select-Object -Last 12
        Write-Host "`n  Se abrira el selector: elige el equipo dueno de '$PROYECTO_ESPERADO'." -ForegroundColor Cyan
        & vercel switch
        $salidaLs = & vercel ls 2>&1 | Out-String
        $equipoOk = ($salidaLs -match [regex]::Escape($PROYECTO_ESPERADO))
    }

    if (-not $equipoOk) {
        Write-Host "`n  No se encontro '$PROYECTO_ESPERADO' en ningun equipo de esta cuenta." -ForegroundColor Red
        Write-Host "  Puede que hayas entrado con otro correo. Prueba:" -ForegroundColor Yellow
        Write-Host "     vercel logout   y vuelve a entrar con el correo dueno del proyecto" -ForegroundColor Yellow
        Write-Host "  IMPORTANTE: no elijas 'Create a new project', eso crearia otra URL." -ForegroundColor Red
        Read-Host "`n  Enter para salir"; exit 1
    }

    Write-Host "`n  Elige el proyecto '$PROYECTO_ESPERADO' cuando te pregunte." -ForegroundColor Cyan
    Write-Host "  NO elijas 'Create a new project'.`n" -ForegroundColor Red
    & vercel link
    if (-not (Test-EnlaceValido)) {
        Write-Host "  No se pudo vincular el proyecto." -ForegroundColor Red
        Read-Host "`n  Enter para salir"; exit 1
    }
}
$proyecto = (Get-Content ".vercel\project.json" -Raw | ConvertFrom-Json).projectName
Write-Host "  Proyecto          : $proyecto" -ForegroundColor Green
Write-Host ""

# --- 4. Reunir los valores -------------------------------------------
$aCargar = @{}
foreach ($v in $VARIABLES) {
    $nombre = $v.Nombre
    $valor = [Environment]::GetEnvironmentVariable($nombre, "User")
    if (-not $valor) { $valor = [Environment]::GetEnvironmentVariable($nombre, "Machine") }

    if ($valor) {
        Write-Host ("  {0,-22} encontrada en este PC ({1} caracteres)" -f $nombre, $valor.Length) -ForegroundColor Green
    } else {
        $etiqueta = if ($v.Obligatoria) { "obligatoria" } else { "opcional, Enter para omitir" }
        Write-Host ("  {0,-22} no esta en este PC - {1}" -f $nombre, $etiqueta) -ForegroundColor Yellow
        Write-Host ("     sirve para {0}" -f $v.Para) -ForegroundColor DarkGray
        $seguro = Read-Host "     pegala aca" -AsSecureString
        $valor = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
                    [Runtime.InteropServices.Marshal]::SecureStringToBSTR($seguro))
        if (-not $valor) {
            if ($v.Obligatoria) {
                Write-Host "     Sin esta clave Catalina no va a funcionar. Se omite igual." -ForegroundColor Red
            }
            continue
        }
    }
    $aCargar[$nombre] = $valor
}

if ($aCargar.Count -eq 0) {
    Write-Host "`n  No hay nada que cargar." -ForegroundColor Yellow
    Read-Host "  Enter para salir"; exit 0
}

# --- 5. Confirmar -----------------------------------------------------
Write-Host ""
Write-Host ("  Se van a cargar {0} variables en: {1}" -f $aCargar.Count, ($ENTORNOS -join ", "))
Write-Host "  Si alguna ya existe en Vercel, se reemplaza."
$ok = Read-Host "  Continuar? (s/n)"
if ($ok -notmatch '^[sSyY]') { Write-Host "  Cancelado."; exit 0 }

# --- 6. Cargar --------------------------------------------------------
Write-Host ""
$errores = 0
foreach ($nombre in $aCargar.Keys) {
    foreach ($entorno in $ENTORNOS) {
        # Se borra primero para que "add" no falle si ya existia. Que falle el
        # borrado es normal cuando la variable todavia no estaba: se ignora.
        $null = & vercel env rm $nombre $entorno --yes 2>&1

        # El valor entra por stdin: nunca aparece en la linea de comandos ni
        # queda en el historial de PowerShell.
        $salida = $aCargar[$nombre] | & vercel env add $nombre $entorno 2>&1
        $codigo = $LASTEXITCODE

        if ($codigo -eq 0) {
            Write-Host ("  OK    {0,-22} {1}" -f $nombre, $entorno) -ForegroundColor Green
        } else {
            Write-Host ("  FALLO {0,-22} {1}" -f $nombre, $entorno) -ForegroundColor Red
            ($salida | Out-String).Trim() -split "`n" |
                Select-Object -Last 2 |
                ForEach-Object { Write-Host "          $_" -ForegroundColor DarkGray }
            $errores++
        }
    }
}

# --- 7. Redesplegar ---------------------------------------------------
Write-Host ""
if ($errores -gt 0) {
    Write-Host "  Hubo $errores errores. Revisa arriba antes de redesplegar." -ForegroundColor Red
} else {
    Write-Host "  Todas las variables quedaron cargadas." -ForegroundColor Green
    Write-Host "  Vercel solo aplica las variables nuevas en el proximo despliegue."
    $red = Read-Host "  Redesplegar ahora? (s/n)"
    if ($red -match '^[sSyY]') {
        & vercel --prod
    } else {
        Write-Host "  Cuando quieras:  vercel --prod" -ForegroundColor DarkGray
    }
}

# --- 8. Comprobar -----------------------------------------------------
Write-Host ""
Write-Host "  Para comprobar que quedo bien, abre esta direccion:"
Write-Host "     https://voltaic-chat.vercel.app/api/simli/estado" -ForegroundColor Cyan
Write-Host "  Tiene que decir  configurado: true  y  falta: []"
Write-Host ""
Read-Host "  Enter para cerrar"
