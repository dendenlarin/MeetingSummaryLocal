# TODO

- [x] Утвердить план реализации сервиса watcher + transcript + summary.
- [x] Поднять каркас Python-проекта и базовые конфиги.
- [x] Реализовать пайплайн `m4a -> transcript -> ollama summary -> .md`.
- [x] Реализовать watcher каталога `calls/` с защитой от незавершённой записи.
- [x] Добавить документацию по запуску и конфигу.
- [x] Проверить проект и зафиксировать результат.
- [x] Добавить Docker-режим для запуска приложения в контейнере с подключением к локальному `ollama`.

# Review

- Реализован локальный Python-сервис для автоматической обработки `.m4a` из `calls/`.
- Добавлены watcher, транскрибация через `faster-whisper`, summary через `ollama`, генерация markdown и конфиг через `.env`.
- Проверено через `python3 -m compileall .` и `python3 -m unittest discover -s tests -v`.
- Добавлены `Dockerfile`, `.dockerignore` и `docker-compose.yml` для запуска приложения в контейнере с доступом к `ollama` на хосте.
