# =============================================================================
#  Hermes Agent Dockerfile — КАРКАС
#  Спека 10. ⚠️ T-030 (spike) должен подтвердить детали сборки.
#  Публичного образа нет — собираем из клона репозитория Nous Research.
# =============================================================================
# Базовый образ с Python + Node (Hermes требует оба).
FROM python:3.11-slim

# Системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl wget nodejs npm \
    && rm -rf /var/lib/apt/lists/*

# uv (быстрый пакетный менеджер, требует Hermes)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Рабочий каталог
WORKDIR /app

# ⚠️ Spike T-030: клонируем hermes-agent. Если репо приватный/недоступен —
# разработчик уточняет способ получения (release tarball, mirror).
# Вариант 1 — клон из GitHub:
RUN git clone https://github.com/NousResearch/hermes-agent.git . \
    && git checkout v0.20.0 || echo "⚠️ тег не найден, берём main"

# Вариант 2 (если клон упадёт на spike) — раскомментировать локальный copy:
# COPY ./hermes-agent/ .

# Установка зависимостей Hermes
RUN uv pip install --system -e ".[all]"

# Каталог данных (Hermes home)
ENV HERMES_HOME=/hermes-home
RUN mkdir -p $HERMES_HOME/memories $HERMES_HOME/skills

# Наш config и skills копируются через volume (docker-compose) — здесь только
# дефолты на случай, если volume не смонтирован.
COPY ./config.yaml $HERMES_HOME/config.yaml
COPY ./skills/ $HERMES_HOME/skills/

# Порт API Server (уточнить на spike: 8642 или 9119)
EXPOSE 8642

# Healthcheck (уточнить endpoint на spike: /health или /v1/models)
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://localhost:8642/health || exit 1

# ⚠️ Команда запуска — УТОЧНИТЬ НА SPIKE T-030.
# Документация противоречит: `hermes gateway` (api-server, порт 8642)
# vs `hermes serve` (dashboard, порт 9119).
# Нам нужен OpenAI-compatible API — кандидат `hermes gateway`.
CMD ["hermes", "gateway"]
