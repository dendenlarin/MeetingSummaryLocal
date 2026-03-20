# Meeting Summary

Open source сервис для локальной обработки аудиозаписей звонков в `.m4a`.

Приложение следит за папкой `calls/`, расшифровывает новые файлы через локальный `faster-whisper`, отправляет транскрипцию в локально запущенный `ollama` для summary и сохраняет результат в `.md` рядом с аудиофайлом.

## Что умеет

- отслеживает новые `.m4a` в папке `calls/`
- обрабатывает уже существующие записи при старте
- ждёт завершения записи файла перед обработкой
- пропускает файл, если рядом уже есть готовый `.md`
- сохраняет summary и полную транскрипцию в одном markdown-файле
- умеет размечать разных спикеров через `pyannote` при включённом diarization
- работает локально и через Docker

## Что не хранить в репозитории

- ваши `.env`-файлы с локальными настройками
- папку `calls/` с аудио и готовыми markdown-результатами
- кэши моделей, build-артефакты и служебные рабочие заметки

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
- признак, удалось ли определить спикеров
- раздел `## Summary`
- раздел `## Transcript`

## Требования

- Python 3.11+ для локального запуска
- `ffmpeg`
- локально запущенный `ollama`
- хотя бы одна доступная модель в `ollama`
- достаточно CPU или GPU для запуска `faster-whisper`
- для diarization: optional extra `.[diarization]`, модель `pyannote` и, как правило, токен Hugging Face для первой загрузки

`faster-whisper` работает полностью локально и бесплатно, без обращения к API OpenAI. Для русскоязычных звонков quality-default в этом проекте это `large-v3`: это мультиязычная модель, в отличие от `distil-large-v3`, который не подходит как default для русского контура.

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

Если нужен speaker diarization, установите optional extra:

```bash
pip install -e .[diarization]
```

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
- `OLLAMA_PROMPT_PATH=/app/runtime-prompts/summary.md`

Папки `./calls` и `./meeting_summary/prompts` монтируются в контейнер, а кэши `whisper` и `huggingface` сохраняются в docker volume.
Prompt можно менять на хосте без пересборки образа и без рестарта сервиса: следующий summary возьмёт уже новую версию файла.

## Конфигурация

Пример `.env`:

```dotenv
OLLAMA_MODEL=auto
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_PROMPT_PATH=./meeting_summary/prompts/summary.md
WHISPER_MODEL=large-v3
WHISPER_DEVICE=auto
WHISPER_COMPUTE_TYPE=auto
WHISPER_LANGUAGE=ru
WHISPER_INITIAL_PROMPT=
WHISPER_TERMS=Docker,GitHub,API,backend,frontend,deploy,pipeline,OpenAI,Whisper,Ollama
WHISPER_BEAM_SIZE=5
WHISPER_BEST_OF=5
WHISPER_TEMPERATURE=0
WHISPER_VAD_FILTER=true
ENABLE_DIARIZATION=false
HF_TOKEN=
PYANNOTE_DEVICE=auto
CALLS_DIR=./calls
FILE_READY_CHECKS=3
FILE_READY_INTERVAL_SECONDS=2
FILE_DUPLICATE_COOLDOWN_SECONDS=120
INITIAL_SCAN=true
```

Описание параметров:

- `OLLAMA_MODEL`:
  модель для summary; значение `auto` выбирает первую локально установленную модель
- `OLLAMA_BASE_URL`:
  адрес локального API `ollama`
- `OLLAMA_PROMPT_PATH`:
  путь до markdown-шаблона prompt для `ollama`; файл перечитывается при каждом новом summary
- если переменная не задана, используется встроенный prompt из ресурсов пакета `meeting_summary/prompts/summary.md`
- если путь относительный, он резолвится относительно директории загрузки конфигурации (`base_dir` / текущая директория запуска)
- в шаблоне подставляются только `{language}`, `{duration_seconds}` и `{transcript_block}`; остальные `{}` остаются обычным текстом
- `WHISPER_MODEL`:
  имя модели `faster-whisper`, например `large-v3`, `medium` или `small`; `distil-large-v3` не использовать как default для русскоязычных звонков
- `WHISPER_DEVICE`:
  устройство для `faster-whisper`, обычно `auto`, `cpu` или `cuda`
- `WHISPER_COMPUTE_TYPE`:
  compute type для `faster-whisper`; значение `auto` выбирает `int8` на CPU и `float16` на CUDA
- `WHISPER_LANGUAGE`:
  язык распознавания; для русскоязычных звонков рекомендуется `ru`, чтобы модель не блуждала между языками
- `WHISPER_INITIAL_PROMPT`:
  optional glossary prompt для имен, брендов и англоязычных технических терминов; лучше держать его коротким списком терминов, а не длинной инструкцией
- `WHISPER_TERMS`:
  короткий список терминов для auto-glossary prompt; используется только если `WHISPER_INITIAL_PROMPT` не задан
- `WHISPER_BEAM_SIZE`:
  ширина beam search; больше значение обычно улучшает качество, но замедляет обработку
- `WHISPER_BEST_OF`:
  сколько кандидатов сравнивать при декодировании
- `WHISPER_TEMPERATURE`:
  температура декодирования; для стабильной транскрибации рекомендуется `0`
- `WHISPER_VAD_FILTER`:
  включает VAD-фильтрацию до декодирования, чтобы убирать тишину и снижать hallucinations на длинных паузах
- `WHISPER_MODEL_SIZE`:
  deprecated fallback для обратной совместимости; используется только если `WHISPER_MODEL` не задан
- `ENABLE_DIARIZATION`:
  включает speaker diarization через `pyannote`
- пустое значение трактуется как `false`
- `HF_TOKEN`:
  токен Hugging Face для первой загрузки модели diarization; если модель уже закеширована локально, может не понадобиться
- `PYANNOTE_DEVICE`:
  устройство для diarization, например `auto`, `cpu` или `cuda`
- `CALLS_DIR`:
  папка, за которой следит сервис
- `FILE_READY_CHECKS`:
  сколько стабильных проверок размера файла нужно до старта обработки
- `FILE_READY_INTERVAL_SECONDS`:
  интервал между проверками готовности файла
- `FILE_DUPLICATE_COOLDOWN_SECONDS`:
  окно в секундах, в течение которого одинаковый `.m4a` с тем же размером и `mtime` не будет повторно обрабатываться после нового `created`/`moved` события
- `INITIAL_SCAN`:
  обрабатывать ли существующие файлы при старте

## Поведение при ошибках

- если указано некорректное имя модели `whisper`, загрузка завершится ошибкой при старте сервиса
- ошибка по одному файлу не останавливает watcher
- если `ollama` недоступна, сервис продолжает работать и пишет ошибку в лог
- если `.md` уже существует, файл считается обработанным
- watcher подавляет повторную обработку того же файла в пределах `FILE_DUPLICATE_COOLDOWN_SECONDS`, если fingerprint файла не изменился
- если diarization не настроен или упал, файл всё равно будет обработан, но без спикеров
- для `.m4a` diarization использует ffmpeg/`faster-whisper` decode как штатный путь, а не как шумный runtime fallback
- в логах по каждому файлу печатаются stage-based статусы прогресса обработки

## Рекомендации по качеству

- Для русскоязычных звонков с техническими терминами не используйте `small` как quality-first режим; мультиязычный quality-first default здесь это `large-v3`
- Если железо позволяет и latency не критична, для максимального качества лучше `large-v3`
- Для mixed-language звонков лучше фиксировать `WHISPER_LANGUAGE=ru`, а glossary задавать коротким prompt или `WHISPER_TERMS` вроде `Docker,GitHub,API,backend,frontend,deploy`
- В Docker quality-default задаётся через `docker-compose.yml`, даже если в локальном `.env` остался legacy `WHISPER_MODEL_SIZE=small`
- `distil-large-v3` не подходит как quality-default для русского контура: если нужен русский, выбирайте мультиязычный `large-v3` или компромиссный `medium`

## Прогресс в логах

Во время обработки сервис пишет stage-progress по файлу, например:

```text
[record_test.m4a] 10% | processing_started | File is stable. Starting analysis.
[record_test.m4a] 20% | transcribing | Transcribing audio with faster-whisper.
[record_test.m4a] 34% | transcribing_progress | Processed 12.4 / 37.1 min of audio.
[record_test.m4a] 75% | diarization_complete | Diarization finished with 2 speakers.
[record_test.m4a] 85% | summarizing | Generating summary with Ollama.
[record_test.m4a] 100% | completed | Saved markdown to record_test.md.
```

Это не внутренний процент самой модели Whisper, а устойчивый прогресс по стадиям пайплайна.
Стадия `transcribing` начинается на `20%`, а во время долгого CPU/GPU-распознавания сервис дополнительно пишет heartbeat-обновления `transcribing_progress` до `55%`, чтобы было видно, что обработка не зависла и не стартовала заново.

## Troubleshooting

- Если `WHISPER_VAD_FILTER=true`, в Docker/VM может появляться строка вида `onnxruntime cpuid_info warning: Unknown CPU vendor...`
- Это benign warning от ONNXRuntime/VAD и само по себе не означает рестарт обработки файла
- Повтор `0% -> 20%` должен происходить только при новом filesystem event, новом fingerprint файла или после истечения `FILE_DUPLICATE_COOLDOWN_SECONDS`

## Speaker Diarization

По умолчанию diarization выключен. Чтобы включить определение спикеров:

```bash
pip install -e .[diarization]
```

```dotenv
ENABLE_DIARIZATION=true
HF_TOKEN=hf_...
PYANNOTE_DEVICE=auto
```

Перед первым запуском нужно:

- иметь аккаунт Hugging Face
- принять доступ к моделям `pyannote/segmentation-3.0` и `pyannote/speaker-diarization-3.1`
- создать `HF_TOKEN` с правами чтения

После первой успешной загрузки модель остаётся в локальном кэше, поэтому на той же машине diarization обычно может работать оффлайн.
Если `ENABLE_DIARIZATION=true`, но optional extra не установлен или `pyannote` не инициализировался, сервис продолжит обработку файла без спикеров и запишет warning в лог.

После этого раздел `## Transcript` будет выглядеть примерно так:

```text
[00:00-00:04] Speaker 1: Добрый день, начинаем.
[00:04-00:07] Speaker 2: Да, давайте.
```

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
