param(
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8501,
    [string]$AuthorizedEmail = "miguellponcej@gmail.com"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $ProjectRoot

$securePassword = Read-Host "Password local temporal para $AuthorizedEmail" -AsSecureString
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
try {
    $plainPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
}
finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
}

$env:QP_LOCAL_PASSWORD = $plainPassword
$passwordHash = & ".\.venv\Scripts\python.exe" -c "import os; from src.auth.auth_service import hash_password; print(hash_password(os.environ['QP_LOCAL_PASSWORD']))"
Remove-Item Env:\QP_LOCAL_PASSWORD -ErrorAction SilentlyContinue

$env:APP_ENV = "production"
$env:PRIVATE_BY_DEFAULT = "true"
$env:APP_SECRET_KEY = [Guid]::NewGuid().ToString("N") + [Guid]::NewGuid().ToString("N")
$env:SESSION_SECRET = [Guid]::NewGuid().ToString("N") + [Guid]::NewGuid().ToString("N")
$env:AUTHORIZED_EMAILS = $AuthorizedEmail
$env:AUTH_PASSWORD_HASH = $passwordHash
$env:ENABLE_IP_ALLOWLIST = "false"
$env:LOG_LEVEL = "INFO"
$env:ACTIVE_DRAWS_REFRESH_MINUTES = "60"

Write-Host "QuinielaPredictor MX local"
Write-Host "URL: http://$HostAddress`:$Port"
Write-Host "Correo autorizado: $AuthorizedEmail"
Write-Host "Manten esta ventana abierta mientras uses la app."

& ".\.venv\Scripts\streamlit.exe" run "app\streamlit_app.py" `
    --server.address $HostAddress `
    --server.port $Port `
    --server.headless true `
    --browser.gatherUsageStats false
