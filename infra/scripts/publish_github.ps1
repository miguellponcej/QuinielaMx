param(
    [string]$RepositoryUrl = "https://github.com/miguellponcej/QuinielaMx.git",
    [string]$Branch = "main"
)

$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $RepoRoot
$SafeRepoRoot = $RepoRoot.Replace("\", "/")

git config --global --add safe.directory $SafeRepoRoot

function Invoke-Git {
    git -c "safe.directory=$SafeRepoRoot" @args
    if ($LASTEXITCODE -ne 0) {
        throw "Git fallo con codigo ${LASTEXITCODE}: git $args"
    }
}

function Invoke-GitPush {
    if ($env:GITHUB_TOKEN) {
        $basic = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("x-access-token:$env:GITHUB_TOKEN"))
        git -c "safe.directory=$SafeRepoRoot" -c "http.https://github.com/.extraheader=AUTHORIZATION: basic $basic" push -u origin $Branch
    } else {
        git -c "safe.directory=$SafeRepoRoot" push -u origin $Branch
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Git push fallo con codigo $LASTEXITCODE."
    }
}

if (-not (Test-Path ".git")) {
    Invoke-Git init -b $Branch
}

if (-not (Invoke-Git config user.name 2>$null)) {
    Invoke-Git config user.name "Miguel Angel"
}
if (-not (Invoke-Git config user.email 2>$null)) {
    Invoke-Git config user.email "miguellponcej@gmail.com"
}

git -c "safe.directory=$SafeRepoRoot" remote remove origin 2>$null
Invoke-Git remote add origin $RepositoryUrl

Invoke-Git add .

$HasCommit = git -c "safe.directory=$SafeRepoRoot" rev-parse --verify HEAD 2>$null
$HasChanges = git -c "safe.directory=$SafeRepoRoot" status --porcelain
if ($HasChanges) {
    Invoke-Git commit -m "Prepare QuinielaPredictor MX for Streamlit Cloud"
} elseif (-not $HasCommit) {
    throw "No hay archivos para commitear. Revisa .gitignore o permisos de la carpeta."
} else {
    Write-Host "No hay cambios nuevos para commitear."
}

Invoke-Git branch -M $Branch
Invoke-GitPush

Write-Host "Publicado en $RepositoryUrl rama $Branch"
