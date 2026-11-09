# Windows 上 Celery 默认 prefork 多进程易触发 WinError 5，请用 solo 或 threads。
Set-Location $PSScriptRoot\..

$pool = if ($env:CELERY_WORKER_POOL) { $env:CELERY_WORKER_POOL } else { "solo" }
$concurrency = if ($pool -eq "solo") { "1" } elseif ($env:CELERY_WORKER_CONCURRENCY) { $env:CELERY_WORKER_CONCURRENCY } else { "4" }

Write-Host "Starting Celery worker (pool=$pool, concurrency=$concurrency, queue=image)..." -ForegroundColor Cyan
& .\.venv\Scripts\celery.exe -A Intelligent_agent worker -Q image --pool=$pool -c $concurrency -l info
