param(
    [string]$SourceRoot = "C:\Users\mpj_9\OneDrive\Experto en Sorteos\quiniela_predictor_mx",
    [string]$TargetRoot = "C:\Dev\quiniela_predictor_mx",
    [string]$CommitMessage = "Improve Streamlit production usability and web fixtures"
)

$ErrorActionPreference = "Stop"

function Assert-PathExists {
    param([string]$Path, [string]$Label)
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "$Label no existe: $Path"
    }
}

Assert-PathExists -Path $SourceRoot -Label "SourceRoot"
Assert-PathExists -Path $TargetRoot -Label "TargetRoot"
Assert-PathExists -Path (Join-Path $TargetRoot ".git") -Label "Repositorio Git destino"

$files = @(
    "app\streamlit_app.py",
    "src\active_draws\active_draws_service.py",
    "src\active_draws\draw_parser.py",
    "src\active_draws\draw_validator.py",
    "src\active_draws\ai_quiniela_extractor.py",
    "src\active_draws\official_guide_pdf.py",
    "src\active_draws\official_sources_client.py",
    "src\ai\__init__.py",
    "src\ai\llm_clients.py",
    "src\data_sources\espn_client.py",
    "src\data_sources\source_registry.py",
    "src\history\__init__.py",
    "src\history\evaluator.py",
    "src\history\learning.py",
    "src\history\storage.py",
    "src\home\home_cards.py",
    "src\home\home_dashboard.py",
    "src\home\home_recommendations.py",
    "src\prediction\predictor.py",
    "src\realtime\real_time_prediction_pipeline.py",
    ".env.example",
    ".gitignore",
    ".streamlit\secrets.example.toml",
    "README.md",
    "requirements.txt",
    "tests\test_active_draws_service.py",
    "tests\test_ai_quiniela_extractor.py",
    "tests\test_espn_client.py",
    "tests\test_official_guide_pdf.py",
    "tests\test_prediction_history.py",
    "infra\scripts\sync_production_fixes_to_dev.ps1"
)

foreach ($relativePath in $files) {
    $source = Join-Path $SourceRoot $relativePath
    $target = Join-Path $TargetRoot $relativePath
    Assert-PathExists -Path $source -Label "Archivo fuente"
    $targetDir = Split-Path -Parent $target
    if (-not (Test-Path -LiteralPath $targetDir)) {
        New-Item -ItemType Directory -Path $targetDir | Out-Null
    }
    Copy-Item -LiteralPath $source -Destination $target -Force
    Write-Host "Copiado: $relativePath"
}

Push-Location $TargetRoot
try {
    git status --short
    $gitFiles = @(
        "app/streamlit_app.py",
        "src/active_draws/active_draws_service.py",
        "src/active_draws/draw_parser.py",
        "src/active_draws/draw_validator.py",
        "src/active_draws/ai_quiniela_extractor.py",
        "src/active_draws/official_guide_pdf.py",
        "src/active_draws/official_sources_client.py",
        "src/ai/__init__.py",
        "src/ai/llm_clients.py",
        "src/data_sources/espn_client.py",
        "src/data_sources/source_registry.py",
        "src/history/__init__.py",
        "src/history/evaluator.py",
        "src/history/learning.py",
        "src/history/storage.py",
        "src/home/home_cards.py",
        "src/home/home_dashboard.py",
        "src/home/home_recommendations.py",
        "src/prediction/predictor.py",
        "src/realtime/real_time_prediction_pipeline.py",
        ".env.example",
        ".gitignore",
        ".streamlit/secrets.example.toml",
        "README.md",
        "requirements.txt",
        "tests/test_active_draws_service.py",
        "tests/test_ai_quiniela_extractor.py",
        "tests/test_espn_client.py",
        "tests/test_official_guide_pdf.py",
        "tests/test_prediction_history.py",
        "infra/scripts/sync_production_fixes_to_dev.ps1"
    )
    git add -- $gitFiles

    $changes = git status --short
    if (-not $changes) {
        Write-Host "No hay cambios para publicar."
        exit 0
    }

    git commit -m $CommitMessage
    git push origin main
    Write-Host ""
    Write-Host "Publicado en GitHub. Streamlit Cloud debe redeplegar automaticamente:"
    Write-Host "https://quinielamx.streamlit.app/"
}
finally {
    Pop-Location
}
