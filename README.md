# Meeting Summary

Локальный Python-сервис, который следит за каталогом `calls/`, автоматически расшифровывает новые `.m4a` через `faster-whisper`, делает summary через локальный `ollama` и сохраняет результат в `.md` рядом с исходным файлом.

## Что делает

- следит за `./calls` и обрабатывает новые `.m4a`
- при старте может обработать уже существующие записи
- пропускает аудио, если рядом уже есть одноимённый `.md`
- ждёт, пока файл перестанет расти, чтобы не начинать обработку слишком рано

## Требования

- Python 3.11+
- установленный `ffmpeg`
- запущенный локально `ollama`
- загруженная в `ollama` модель для summary

Пример установки `ffmpeg` на macOS:

```bash
brew install ffmpeg
```

Пример загрузки модели в `ollama`:

```bash
ollama pull llama3.1:8b
```

## Установка

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
```

## Запуск в Docker

Если `ollama` уже запущена локально на Mac, можно поднять только контейнер приложения:

```bash
docker compose up --build -d
```

Что происходит:

- контейнер использует `OLLAMA_BASE_URL=http://host.docker.internal:11434`
- каталог `./calls` монтируется внутрь контейнера как `/app/calls`
- кэш моделей `faster-whisper` сохраняется в docker volume `whisper_cache`

Полезные команды:

```bash
docker compose logs -f meeting-summary
docker compose down
```

Для Docker-режима важно, чтобы локальный `ollama` был доступен на хосте и чтобы нужная модель уже существовала или могла быть выбрана через `OLLAMA_MODEL=auto`.

## Конфиг

Файл `.env`:

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

Основные параметры:

- `OLLAMA_MODEL`: модель для summary
- `OLLAMA_MODEL=auto`: взять первую локально установленную модель из `ollama`
- `OLLAMA_BASE_URL`: адрес локального API `ollama`
- `WHISPER_MODEL_SIZE`: размер модели `faster-whisper`
- `CALLS_DIR`: каталог с `.m4a`
- `FILE_READY_CHECKS` и `FILE_READY_INTERVAL_SECONDS`: сколько раз подряд файл должен иметь одинаковый размер, чтобы считаться готовым

В Docker `OLLAMA_BASE_URL` и `CALLS_DIR` переопределяются автоматически:

- `OLLAMA_BASE_URL=http://host.docker.internal:11434`
- `CALLS_DIR=/app/calls`

## Запуск

```bash
meeting-summary
```

или

```bash
python -m meeting_summary
```

или

```bash
python -m meeting_summary.main
```

Через Docker:

```bash
docker compose up --build
```

После запуска сервис:

1. создаст каталог `calls/`, если его ещё нет
2. просканирует уже существующие `.m4a`, если включён `INITIAL_SCAN`
3. перейдёт в режим постоянного наблюдения

## Формат результата

Для файла `calls/demo.m4a` будет создан файл `calls/demo.md`.

Внутри:

- заголовок с именем файла
- служебная мета-информация
- блок `## Summary`
- блок `## Transcript`

## Замечания

- summary запрашивается у `ollama` на русском языке
- если указанной модели нет, сервис попытается взять первую локально установленную модель и залогирует это
- если `ollama` или транскрибация дадут ошибку, watcher продолжит работу и не завершится
- если рядом уже есть `.md`, файл считается обработанным и пропускается
