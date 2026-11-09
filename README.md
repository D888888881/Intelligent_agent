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

## 健康检查

`GET /health/` 检查数据库连接。
