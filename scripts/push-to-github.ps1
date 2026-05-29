param(
  [Parameter(Mandatory = $true)]
  [string]$RepositoryUrl
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path ".git")) {
  git init -b main
}

if (-not (git remote | Select-String -SimpleMatch "origin")) {
  git remote add origin $RepositoryUrl
} else {
  git remote set-url origin $RepositoryUrl
}

git status --short
git push -u origin main
