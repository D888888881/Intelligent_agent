# 本机 Django 开发服务（默认 8088，避免占用 8000）
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        if ($_ -match '^\s*([^#=]+)=(.*)$') {
            [System.Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), "Process")
        }
    }
}

$port = if ($env:DJANGO_PORT) { $env:DJANGO_PORT } else { "8088" }
$hostName = if ($env:DJANGO_HOST) { $env:DJANGO_HOST } else { "127.0.0.1" }

Write-Host "Django runserver http://${hostName}:$port/"
& .\.venv\Scripts\python.exe manage.py runserver "${hostName}:$port"
