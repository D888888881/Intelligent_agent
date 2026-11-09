# Vue/Vite 开发服务（默认 3000，避免占用 5173）
$ErrorActionPreference = "Stop"
Set-Location (Join-Path (Split-Path $PSScriptRoot -Parent) "frontend")

if (-not (Test-Path "node_modules")) {
    npm install
}

if (Test-Path "..\.env") {
    Get-Content "..\.env" | ForEach-Object {
        if ($_ -match '^\s*([^#=]+)=(.*)$') {
            [System.Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), "Process")
        }
    }
}

$port = if ($env:VITE_DEV_PORT) { $env:VITE_DEV_PORT } else { "3000" }
Write-Host "Vite dev server http://127.0.0.1:$port/ (API 代理到 Django)"
npm run dev -- --port $port --strictPort
