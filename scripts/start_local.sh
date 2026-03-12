#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

LOG_DIR="$ROOT_DIR/logs"
mkdir -p "$LOG_DIR"

info() { echo "[INFO] $*"; }
warn() { echo "[WARN] $*"; }
fail() { echo "[ERROR] $*"; exit 1; }

pick_python() {
  if command -v py >/dev/null 2>&1; then
    echo "py"
    return
  fi
  if command -v python3 >/dev/null 2>&1; then
    echo "python3"
    return
  fi
  if command -v python >/dev/null 2>&1; then
    echo "python"
    return
  fi
  fail "Python not found. Install Python 3 first."
}

load_env_file() {
  local env_file="$1"
  while IFS= read -r line || [ -n "$line" ]; do
    line="${line%$'\r'}"
    [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
    [[ "$line" != *=* ]] && continue

    local key="${line%%=*}"
    local value="${line#*=}"

    key="${key//[[:space:]]/}"
    if [[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
      export "$key=$value"
    fi
  done < "$env_file"
}

if [ -f "$ROOT_DIR/.env" ]; then
  load_env_file "$ROOT_DIR/.env"
  info "Loaded .env"
else
  warn ".env not found; using current shell env/defaults"
fi

if ! command -v curl >/dev/null 2>&1; then
  fail "curl not found. Install curl first."
fi

if ! command -v ollama >/dev/null 2>&1; then
  fail "ollama not found. Install Ollama first."
fi

PY_CMD="$(pick_python)"
info "Using Python command: $PY_CMD"

# Local mode defaults (force container-style hostnames to localhost)
if [ "${OLLAMA_URL:-}" = "" ] || [[ "${OLLAMA_URL:-}" == "http://ollama:"* ]]; then
  export OLLAMA_URL="http://localhost:11434"
fi
if [ "${DB_URL:-}" = "" ] || [[ "${DB_URL:-}" == "http://vedaaide-db:"* ]]; then
  export DB_URL="http://localhost:5000"
fi

export DATABASE_PATH="${DATABASE_PATH:-./data}"

if [ -z "${TELEGRAM_BOT_TOKEN:-}" ]; then
  fail "TELEGRAM_BOT_TOKEN is empty. Set it in .env before starting."
fi

# 避免本地 polling 与容器 polling 冲突
if command -v docker >/dev/null 2>&1; then
  if docker compose ps vedaaide-bot 2>/dev/null | grep -q "Up"; then
    if [ "${AUTO_STOP_DOCKER_BOT:-1}" = "1" ]; then
      warn "Detected running container bot instance; stopping it to avoid TelegramConflictError"
      docker compose stop vedaaide-bot >/dev/null 2>&1 || true
      info "Container bot stopped"
    else
      fail "Container bot is running. Stop it first: docker compose stop vedaaide-bot"
    fi
  fi
fi

if ! ollama list >/dev/null 2>&1; then
  fail "Ollama is not running. Start it with: ollama serve"
fi

if ! ollama list | grep -q "qwen:7b-chat"; then
  warn "Model qwen:7b-chat not found. Pull with: ollama pull qwen:7b-chat"
fi

DB_PID=""
cleanup() {
  if [ -n "$DB_PID" ] && kill -0 "$DB_PID" >/dev/null 2>&1; then
    info "Stopping local SQLite API (PID $DB_PID)"
    kill "$DB_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

if curl -fsS "${DB_URL}/health" >/dev/null 2>&1; then
  info "SQLite API already running at ${DB_URL}"
else
  info "Starting SQLite API on ${DB_URL}"
  "$PY_CMD" "$ROOT_DIR/sqlite_app/app.py" >"$LOG_DIR/local-sqlite.log" 2>&1 &
  DB_PID=$!

  for _ in $(seq 1 30); do
    if curl -fsS "${DB_URL}/health" >/dev/null 2>&1; then
      info "SQLite API is ready"
      break
    fi
    sleep 1
  done

  if ! curl -fsS "${DB_URL}/health" >/dev/null 2>&1; then
    fail "SQLite API failed to start. Check $LOG_DIR/local-sqlite.log"
  fi
fi

info "Starting bot runner with OLLAMA_URL=${OLLAMA_URL} DB_URL=${DB_URL}"
exec "$PY_CMD" "$ROOT_DIR/scripts/restartable_bot_runner.py"
