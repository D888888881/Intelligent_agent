#!/usr/bin/env bash
# Ubuntu 一键 Docker 部署 Intelligent Agent（Web + Celery + Postgres + Redis + Nginx）
# 用法：sudo bash scripts/deploy-docker-ubuntu.sh
# 或：  bash scripts/deploy-docker-ubuntu.sh   （需当前用户已在 docker 组）

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

info() { echo -e "\033[1;36m[deploy]\033[0m $*"; }
warn() { echo -e "\033[1;33m[deploy]\033[0m $*"; }
err()  { echo -e "\033[1;31m[deploy]\033[0m $*" >&2; }

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    return 1
  fi
}

install_docker_ubuntu() {
  if need_cmd docker && docker compose version >/dev/null 2>&1; then
    info "Docker 已安装"
    return 0
  fi

  if ! grep -qi ubuntu /etc/os-release 2>/dev/null; then
    err "当前脚本面向 Ubuntu；请手动安装 Docker 与 Compose 插件后重试"
    exit 1
  fi

  info "安装 Docker 与 Compose 插件…"
  export DEBIAN_FRONTEND=noninteractive
  sudo apt-get update -qq
  sudo apt-get install -y -qq ca-certificates curl gnupg

  if ! need_cmd docker; then
    sudo apt-get install -y -qq docker.io
    sudo systemctl enable --now docker
  fi

  if ! docker compose version >/dev/null 2>&1; then
    sudo apt-get install -y -qq docker-compose-v2 || sudo apt-get install -y -qq docker-compose-plugin
  fi

  if [ -n "${SUDO_USER:-}" ]; then
    sudo usermod -aG docker "$SUDO_USER" || true
    warn "已将用户 $SUDO_USER 加入 docker 组；重新登录后可直接 docker 无需 sudo"
  fi
}

prepare_env() {
  if [ ! -f .env ]; then
    if [ -f .env.docker.example ]; then
      cp .env.docker.example .env
      warn "已从 .env.docker.example 生成 .env —— 部署前请务必编辑："
      warn "  SECRET_KEY、DB_PASSWORD、ALLOWED_HOSTS、PUBLIC_SITE_URL"
      warn "  OPENAI_*、GRSAI_API_KEY、COS_*"
    else
      err "缺少 .env.docker.example"
      exit 1
    fi
  else
    info "使用已有 .env"
  fi

  if grep -q '请替换' .env 2>/dev/null; then
    warn ".env 仍含占位符「请替换」，生产环境请修改后再对外服务"
  fi
}

compose() {
  if docker compose version >/dev/null 2>&1; then
    docker compose "$@"
  elif need_cmd docker-compose; then
    docker-compose "$@"
  else
    err "未找到 docker compose"
    exit 1
  fi
}

run_deploy() {
  install_docker_ubuntu
  prepare_env

  info "构建镜像…"
  compose build

  info "启动服务…"
  compose up -d

  info "等待 Web 健康检查（migrate / collectstatic）…"
  sleep 5
  if compose exec -T web python manage.py shell -c "from django.db import connection; connection.ensure_connection()" >/dev/null 2>&1; then
    info "数据库连接正常"
  else
    warn "数据库尚未就绪，可稍后执行: docker compose logs -f web"
  fi

  PORT="${HTTP_PORT:-80}"
  if [ -f .env ] && grep -q '^HTTP_PORT=' .env; then
    PORT="$(grep '^HTTP_PORT=' .env | tail -1 | cut -d= -f2-)"
  fi

  info "部署完成"
  echo ""
  echo "  访问: http://$(hostname -I 2>/dev/null | awk '{print $1}' || echo 127.0.0.1):${PORT}/login/"
  echo "  健康: http://127.0.0.1:${PORT}/health/"
  echo ""
  echo "  常用命令（在项目根目录）："
  echo "    docker compose ps"
  echo "    docker compose logs -f web celery"
  echo "    docker compose exec web python manage.py createsuperuser"
  echo "    docker compose down"
  echo ""
}

run_deploy