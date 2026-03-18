# Meeting Summary

Локальный сервис для автоматической обработки аудиозаписей звонков в `.m4a`.

Сервис следит за папкой `calls/`, расшифровывает новые файлы через `faster-whisper`, отправляет транскрипцию в локально запущенный `ollama` для summary и сохраняет результат в `.md` рядом с аудиофайлом.

## Что умеет

- отслеживает новые `.m4a` в папке `calls/`
- обрабатывает уже существующие записи при старте
- ждёт завершения записи файла перед обработкой
- пропускает файл, если рядом уже есть готовый `.md`
- сохраняет summary и полную транскрипцию в одном markdown-файле
- работает локально и через Docker

## Как выглядит результат

Для файла:

```text
calls/demo.m4a
```

будет создан файл:

```text
calls/demo.md
```

Внутри будут:

- имя исходного файла
- мета-информация о времени обработки, языке и длительности
- раздел `## Summary`
- раздел `## Transcript`

## Требования

- Python 3.11+ для локального запуска
- `ffmpeg`
- локально запущенный `ollama`
- хотя бы одна доступная модель в `ollama`

Установка `ffmpeg` на macOS:

```bash
brew install ffmpeg
```

Пример загрузки модели:

```bash
ollama pull llama3.1:8b
```

Проверить доступные локальные модели:

```bash
ollama list
```

## Быстрый старт

### Локальный запуск

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
meeting-summary
```

После запуска просто положите `.m4a` в папку `calls/`.

### Docker

Если `ollama` уже запущена на хост-машине, можно поднять только контейнер приложения:

```bash
docker compose up --build -d
```

Полезные команды:

```bash
docker compose logs -f meeting-summary
docker compose down
```

В Docker сервис автоматически использует:

- `CALLS_DIR=/app/calls`
- `OLLAMA_BASE_URL=http://host.docker.internal:11434`

Папка `./calls` монтируется в контейнер, а кэш `faster-whisper` сохраняется в docker volume.

## Конфигурация

Пример `.env`:

```dotenv
OLLAMA_MODEL=auto
OLLAMA_BASE_URL=http://localhost:11434
WHISPER_MODEL_SIZE=small
WHISPER_DEVICE=auto
WHISPER_COMPUTE_TYPE=default
CALLS_DIR=./calls
FILE_READY_CHECKS=3
FILE_READY_INTERVAL_SECONDS=2
INITIAL_SCAN=true
```

Описание параметров:

- `OLLAMA_MODEL`:
  модель для summary; значение `auto` выбирает первую локально установленную модель
- `OLLAMA_BASE_URL`:
  адрес локального API `ollama`
- `WHISPER_MODEL_SIZE`:
  размер модели `faster-whisper`, например `small` или `medium`
- `WHISPER_DEVICE`:
  устройство для `faster-whisper`, обычно `auto` или `cpu`
- `WHISPER_COMPUTE_TYPE`:
  режим вычислений, например `default` или `int8`
- `CALLS_DIR`:
  папка, за которой следит сервис
- `FILE_READY_CHECKS`:
  сколько стабильных проверок размера файла нужно до старта обработки
- `FILE_READY_INTERVAL_SECONDS`:
  интервал между проверками готовности файла
- `INITIAL_SCAN`:
  обрабатывать ли существующие файлы при старте

## Поведение при ошибках

- если указанной модели нет, сервис попробует выбрать первую доступную локальную модель
- ошибка по одному файлу не останавливает watcher
- если `ollama` недоступна, сервис продолжает работать и пишет ошибку в лог
- если `.md` уже существует, файл считается обработанным

## Варианты запуска

```bash
meeting-summary
```

```bash
python -m meeting_summary
```

```bash
python -m meeting_summary.main
```

```bash
docker compose up --build
```

## Для чего подходит

- созвоны и стендапы
- интервью
- клиентские звонки
- голосовые заметки в `.m4a`
