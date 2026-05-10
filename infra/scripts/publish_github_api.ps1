param(
    [string]$Owner = "miguellponcej",
    [string]$Repo = "QuinielaMx",
    [string]$Branch = "main"
)

$ErrorActionPreference = "Stop"

if (-not $env:GITHUB_TOKEN) {
    throw "Define GITHUB_TOKEN antes de ejecutar este script."
}

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$ApiBase = "https://api.github.com/repos/$Owner/$Repo"
$Headers = @{
    Authorization = "Bearer $env:GITHUB_TOKEN"
    Accept = "application/vnd.github+json"
    "X-GitHub-Api-Version" = "2022-11-28"
    "User-Agent" = "QuinielaPredictorMX-Publisher"
}

function Invoke-GitHubJson {
    param(
        [string]$Method,
        [string]$Uri,
        [object]$Body = $null
    )
    if ($null -eq $Body) {
        return Invoke-RestMethod -Method $Method -Uri $Uri -Headers $Headers
    }
    $json = $Body | ConvertTo-Json -Depth 20 -Compress
    return Invoke-RestMethod -Method $Method -Uri $Uri -Headers $Headers -Body $json -ContentType "application/json"
}

function Test-IncludedPath {
    param([string]$RelativePath)
    $p = $RelativePath.Replace("\", "/")
    if ($p -eq ".env" -or $p -eq ".streamlit/secrets.toml") { return $false }
    if ($p -like ".git/*" -or $p -like ".venv/*" -or $p -like ".pytest_cache/*" -or $p -like ".pytest_tmp/*") { return $false }
    if ($p -like "publish_tmp_*/*" -or $p -like "QuinielaMx_streamlit_cloud_*.zip") { return $false }
    if ($p -like "*/__pycache__/*" -or $p -like "*.pyc") { return $false }
    if ($p -like "data/raw/*" -or $p -like "data/processed/*" -or $p -like "data/current/*") { return $false }
    if ($p -like "data/source_cache/*" -or $p -like "data/prediction_logs/*" -or $p -like "data/security_logs/*") { return $false }
    if ($p -like "data/active_draws/cache/*" -or $p -like "data/active_draws/logs/*" -or $p -like "data/active_draws/snapshots/*") { return $false }
    if ($p -like "*.log") { return $false }
    return $true
}

$publishItems = @(
    ".dockerignore",
    ".env.example",
    ".gitignore",
    ".streamlit",
    "DEPLOYMENT_SUMMARY.md",
    "Dockerfile",
    "README.md",
    "README_DEPLOYMENT.md",
    "STREAMLIT_CLOUD.md",
    "app",
    "data/examples",
    "data/templates",
    "deploy",
    "docker-compose.yml",
    "infra",
    "pyproject.toml",
    "requirements.txt",
    "scripts",
    "src",
    "tests"
)

$files = @()
foreach ($item in $publishItems) {
    $path = Join-Path $RepoRoot $item
    if (-not (Test-Path $path)) {
        continue
    }
    if ((Get-Item $path).PSIsContainer) {
        $children = Get-ChildItem -Path $path -File -Recurse -Force -ErrorAction SilentlyContinue
    } else {
        $children = @(Get-Item $path)
    }
    foreach ($child in $children) {
        $relative = $child.FullName.Substring($RepoRoot.Length).TrimStart("\", "/").Replace("\", "/")
        if (Test-IncludedPath $relative) {
            $files += [PSCustomObject]@{ FullName = $child.FullName; Relative = $relative }
        }
    }
}
$files = $files | Sort-Object Relative -Unique

if (-not $files) {
    throw "No hay archivos publicables."
}

$tree = @()
foreach ($file in $files) {
    $bytes = [System.IO.File]::ReadAllBytes($file.FullName)
    $content = [Convert]::ToBase64String($bytes)
    $blob = Invoke-GitHubJson -Method "POST" -Uri "$ApiBase/git/blobs" -Body @{
        content = $content
        encoding = "base64"
    }
    $tree += @{
        path = $file.Relative
        mode = "100644"
        type = "blob"
        sha = $blob.sha
    }
}

$parentSha = $null
$baseTreeSha = $null
try {
    $ref = Invoke-GitHubJson -Method "GET" -Uri "$ApiBase/git/ref/heads/$Branch"
    $parentSha = $ref.object.sha
    $parentCommit = Invoke-GitHubJson -Method "GET" -Uri "$ApiBase/git/commits/$parentSha"
    $baseTreeSha = $parentCommit.tree.sha
} catch {
    $parentSha = $null
    $baseTreeSha = $null
}

$treeBody = @{ tree = $tree }
if ($baseTreeSha) {
    $treeBody.base_tree = $baseTreeSha
}
$newTree = Invoke-GitHubJson -Method "POST" -Uri "$ApiBase/git/trees" -Body $treeBody

$commitBody = @{
    message = "Prepare QuinielaPredictor MX for Streamlit Cloud"
    tree = $newTree.sha
}
if ($parentSha) {
    $commitBody.parents = @($parentSha)
}
$commit = Invoke-GitHubJson -Method "POST" -Uri "$ApiBase/git/commits" -Body $commitBody

if ($parentSha) {
    Invoke-GitHubJson -Method "PATCH" -Uri "$ApiBase/git/refs/heads/$Branch" -Body @{
        sha = $commit.sha
        force = $false
    } | Out-Null
} else {
    Invoke-GitHubJson -Method "POST" -Uri "$ApiBase/git/refs" -Body @{
        ref = "refs/heads/$Branch"
        sha = $commit.sha
    } | Out-Null
}

Write-Host "Publicado commit $($commit.sha) en https://github.com/$Owner/$Repo/tree/$Branch"
