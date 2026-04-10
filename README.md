# Meeting Summary

Локальный сервис для обработки `.m4a` на macOS.

Что делает:
- следит за папкой `calls/`
- расшифровывает запись через `faster-whisper`
- делает diarization через `pyannote`
- отправляет транскрипт в локальный `ollama`
- сохраняет итог в `.md` рядом с исходным файлом

Поддерживается только нативный macOS runtime. Docker и лишняя опциональность убраны.
Diarization всегда включён.

## Что нужно

- `python3.11`, `python3.12` или `python3.13`
- запущенный `ollama`
- модель в `ollama`, например:

```bash
ollama pull gemma3:4b
```

- Hugging Face token с доступом к `pyannote/speaker-diarization-community-1`

## Настройка

1. Нажми `Agree` на странице модели:
   `https://huggingface.co/pyannote/speaker-diarization-community-1`
2. Заполни `HF_TOKEN` в [`.env`](/Users/hashlinski/Projects/MeetingSummary/.env).
   Если [`.env`](/Users/hashlinski/Projects/MeetingSummary/.env) ещё нет, он создастся из [`.env.example`](/Users/hashlinski/Projects/MeetingSummary/.env.example) при первом `./run`.

Минимальный рабочий [`.env`](/Users/hashlinski/Projects/MeetingSummary/.env):

```dotenv
OLLAMA_MODEL=gemma3:4b
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_PROMPT_PATH=./meeting_summary/prompts/summary.md
WHISPER_MODEL=medium
WHISPER_DEVICE=auto
WHISPER_COMPUTE_TYPE=auto
WHISPER_LANGUAGE=ru
WHISPER_INITIAL_PROMPT=
WHISPER_TERMS=Docker,GitHub,API,backend,frontend,deploy,pipeline,OpenAI,Whisper,Ollama
WHISPER_BEAM_SIZE=5
WHISPER_BEST_OF=5
WHISPER_TEMPERATURE=0
WHISPER_VAD_FILTER=true
HF_TOKEN=hf_...
PYANNOTE_DEVICE=auto
CALLS_DIR=./calls
FILE_READY_CHECKS=3
FILE_READY_INTERVAL_SECONDS=2
FILE_DUPLICATE_COOLDOWN_SECONDS=120
INITIAL_SCAN=true
```

Промпт для summary берётся из [`summary.md`](/Users/hashlinski/Projects/MeetingSummary/meeting_summary/prompts/summary.md).

## Запуск

Всегда одна команда:

```bash
./run
```

Если старый `.venv` был создан на `python3.14`, пересоздай его:

```bash
rm -rf .venv
./run
```

После запуска просто положи `.m4a` в [`calls`](/Users/hashlinski/Projects/MeetingSummary/calls).

## Обновление

```bash
git switch main
git fetch origin
git pull --ff-only origin main
./run
```
