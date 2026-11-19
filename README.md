# Intelligent Agent

类 ChatGPT 的对话 + 参考图套图生成（每用户单线程顺序生图）。

## 环境

1. PostgreSQL 数据库 `intelligent_agent`（账号密码见 `.env`）
2. 可选 Redis（生产 Celery 必须；开发可在 `.env` 设 `CELERY_TASK_ALWAYS_EAGER=True` 同步执行）
3. **对话**：`OPENAI_API_KEY` + `OPENAI_BASE_URL`（OpenAI 兼容中转，如 `https://api.openai-proxy.org/v1`）
4. **生图**：`GRSAI_API_KEY` + `GRSAI_BASE_URL`（国内节点 `https://grsai.dakka.com.cn`，全球 `https://grsaiapi.com`），模型见工具栏 `nano-banana-*` / `gpt-image-*`

## 端口（本机默认避开 8000 / 5173）

在 `.env` 中配置：

- `DJANGO_PORT=8088` — Django 开发服务
- `VITE_DEV_PORT=3000` — Vue/Vite 开发服务（`strictPort`，不会回退到 5173）

## 启动

```powershell
cd e:\py_projiect\Intelligent_agent
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python manage.py migrate
.\.venv\Scripts\python manage.py createsuperuser
.\scripts\runserver.ps1
```

或手动指定端口：

```powershell
.\.venv\Scripts\python manage.py runserver 127.0.0.1:8088
```

可选 Vue 开发（将来迁移 SPA 时用）：

```powershell
.\scripts\run-frontend.ps1
```

生产生图队列（Redis 已启动时）：

```powershell
# Windows 推荐（避免 prefork 的 WinError 5「拒绝访问」）
.\scripts\run-celery.ps1

# 或手动：solo 单进程（开发够用）
.\.venv\Scripts\celery -A Intelligent_agent worker -Q image --pool=solo -c 1 -l info

# Linux / macOS 可用多进程
# .\.venv\Scripts\celery -A Intelligent_agent worker -Q image -c 4 -l info
```

浏览器打开 **http://127.0.0.1:8088/login/** 注册/登录（主界面）。

## Docker 部署（Ubuntu 一键）

将项目放到服务器后，在**项目根目录**执行：

```bash
chmod +x scripts/deploy-docker-ubuntu.sh docker/entrypoint.sh
sudo bash scripts/deploy-docker-ubuntu.sh
```

脚本会：安装 Docker（若缺失）→ 从 `.env.docker.example` 生成 `.env`（若尚无）→ `docker compose build` → 启动 **Postgres、Redis、Gunicorn、Celery、Nginx**。

首次部署前请编辑 `.env`（至少 `SECRET_KEY`、`DB_PASSWORD`、`ALLOWED_HOSTS`、`PUBLIC_SITE_URL`、API 与 COS）。默认 HTTP 端口 **80**（`HTTP_PORT` 可改）。

```bash
docker compose exec web python manage.py createsuperuser   # 可选
docker compose logs -f web celery
```

生产需 **HTTPS** 时，可在前再加腾讯云负载均衡/证书，或自行改 `docker/nginx` 配置。Vue 前端**不必**构建或运行。

## 健康检查

`GET /health/` 检查数据库连接。
