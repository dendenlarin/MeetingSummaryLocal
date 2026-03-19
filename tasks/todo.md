# TODO

## 2026-03-19 Исправить регрессии prompt hot-reload и optional diarization

- [x] Перевести Docker mount prompt с одного файла на каталог `meeting_summary/prompts`, сохранив `OLLAMA_PROMPT_PATH`
- [x] Вынести `pyannote.audio` из базовых зависимостей в optional extra для diarization
- [x] Убрать import-time зависимость `Transcriber` от diarization-стека и сохранить fail-soft fallback
- [x] Обновить README и добавить регрессионные тесты на packaging/runtime поведение
- [x] Прогнать compile и релевантные unit-тесты, затем дописать review-итог в этот TODO

## 2026-03-19 Исправить ошибочный English-only default model

- [x] Подтвердить по логам и конфигу, что контейнер реально грузит `distil-large-v3` при `language=ru`
- [x] Вернуть мультиязычный `large-v3` в `.env`, Docker defaults и config defaults
- [x] Убрать из README и тестов неверную рекомендацию `distil-large-v3` для русского контура
- [x] Обновить lessons/review и повторно проверить unit/runtime после смены default-модели

## 2026-03-19 Вернуть quality-first ASR в локальный Docker через faster-whisper

- [x] Зафиксировать безопасный quality-first runtime для Docker CPU на Apple Silicon без `openai-whisper large-v3`
- [x] Перевести `Transcriber` обратно на `faster-whisper` с VAD и glossary, не ломая downstream интерфейсы
- [x] Вернуть совместимый decode path для diarization без зависимости от `openai-whisper`
- [x] Обновить конфиг, Docker defaults, пример env и README под `distil-large-v3` / `large-v3`
- [x] Переписать релевантные unit-тесты и прогнать compile/tests/docker verify

## 2026-03-19 Stabilize diarization/runtime logging and improve mixed-language ASR

- [x] Зафиксировать причину шумных diarization warning/fallback и перевести `.m4a` на детерминированный decode path
- [x] Добавить controlled skip/guardrails для коротких или вырожденных waveform в diarization
- [x] Усилить quality-path Whisper через короткий glossary из конфига без длинного default prompt
- [x] Добавить stage-progress по файлу в Docker-логах без усложнения пайплайна
- [x] Перепроверить архитектурную простоту решения, обновить README, прогнать тесты и добавить review-итог

## 2026-03-19 Decode fallback для нестабильного openai-whisper

- [x] Зафиксировать retryable decode-crash и безопасный fallback-порядок для `Transcriber`
- [x] Убрать длинный glossary prompt из Docker default, сохранив поддержку пользовательского prompt
- [x] Добавить регрессионные тесты на staged retry и успешный fallback без `initial_prompt`
- [x] Обновить README с новым безопасным default для mixed-language звонков
- [x] Прогнать релевантные тесты, пересобрать контейнер и добавить review-итог

## 2026-03-19 Улучшение качества распознавания Whisper

- [x] Зафиксировать quality-first требования для русской речи с англоязычными терминами
- [x] Расширить конфиг и `Transcriber` параметрами языка, glossary prompt и quality decode settings
- [x] Обновить Docker и пример env без правки пользовательского `.env`
- [x] Добавить тесты на новые параметры `whisper` и обновить README
- [x] Прогнать релевантные проверки и добавить review-итог

## 2026-03-19 Переход с faster-whisper на openai-whisper

- [x] Зафиксировать совместимую миграцию в зависимостях, конфиге и Docker runtime
- [x] Перевести `Transcriber` на `openai-whisper` без изменения downstream-интерфейсов
- [x] Заменить fallback-декодирование аудио для diarization на `whisper.audio.load_audio`
- [x] Добавить unit-тесты на новый config/runtime и transcriber
- [x] Обновить README, прогнать релевантные тесты и добавить review-итог

## 2026-03-18 Hot reload prompt без рестарта

- [x] Зафиксировать требование: prompt должен обновляться без пересборки и без рестарта контейнера
- [x] Перевести загрузку prompt на обычный файловый путь без process-level cache
- [x] Примонтировать prompt-файл в контейнер через volume
- [x] Обновить тесты на чтение prompt из файла
- [x] Обновить README с новым поведением
- [x] Прогнать релевантные тесты и добавить review

## 2026-03-18 Prompt для Ollama в отдельном файле

- [x] Найти текущее место хранения prompt для summary и зафиксировать решение
- [x] Вынести prompt в отдельный `.md`-ресурс внутри пакета
- [x] Подключить загрузку prompt из файла в `OllamaClient`
- [x] Обновить тесты и упаковку ресурса
- [x] Прогнать релевантные тесты
- [x] Добавить краткий review-итог по задаче

- [x] Расширить модели и конфигурацию для diarization
- [x] Добавить модуль интеграции с pyannote и маппинг спикеров к сегментам whisper
- [x] Обновить transcriber, markdown writer и prompt для Ollama
- [x] Обновить README и зависимости
- [x] Добавить и прогнать тесты

## 2026-03-18 Пересборка контейнеров

- [x] Проверить compose-конфигурацию и текущие проектные инструкции
- [x] Пересобрать и поднять контейнеры проекта
- [x] Проверить статус контейнеров и логи после запуска

## 2026-03-18 Починка diarization в Docker

- [x] Подтвердить корень проблемы по логам контейнера и версиям `pyannote`/`torchaudio`
- [x] Зафиксировать совместимый стек зависимостей и Docker runtime
- [x] Обновить интеграцию diarization на совместимый API `pyannote` с загрузкой waveform в память
- [x] Обновить тесты и документацию под новый runtime
- [x] Пересобрать контейнер и проверить, что diarization не уходит в fallback на старте

## 2026-03-18 Fix review regressions in config

- [x] Починить дефолтный `OLLAMA_PROMPT_PATH`, чтобы он ссылался на ресурс установленного пакета, а не на `cwd`
- [x] Починить парсинг `ENABLE_DIARIZATION`, чтобы пустое значение считалось выключенным
- [x] Добавить прямые unit-тесты на `Settings.load()` для prompt path и boolean-флагов
- [x] Обновить README и добавить review-итог
- [x] Прогнать релевантные тесты

## 2026-03-18 Починка загрузки `.m4a` для diarization

- [x] Подтвердить причину fallback по логам и коду загрузки аудио
- [x] Добавить fallback-декодирование аудио для pyannote, если `torchaudio.load` не читает контейнер
- [x] Добавить unit-тесты на новый путь загрузки
- [x] Прогнать релевантные тесты и при возможности проверить в контейнере

## 2026-03-18 Fix review regressions in prompt-file handling

- [x] Убрать интерпретацию произвольных `{}` в пользовательском prompt как Python format fields
- [x] Привязать относительный `OLLAMA_PROMPT_PATH` к `base_dir`, а не к process `cwd`
- [x] Добавить регрессионные тесты на literal braces и относительный prompt path
- [x] Обновить README и review-итог
- [x] Прогнать релевантные тесты

# Review

- Подтвержден корень проблемы с англоязычной кашей: контейнер действительно грузил `distil-large-v3` при `WHISPER_LANGUAGE=ru`, но эта модель не подходит как default для русского ASR.
- Default-модель для проекта и Docker исправлена на мультиязычную `large-v3`; `distil-large-v3` убран из `.env`, `.env.example`, `docker-compose.yml`, `Settings.load()` и документации как recommendation для русского контура.
- Обновлены unit-тесты на новый effective default и lesson о том, что при выборе Whisper-модели нужно отдельно проверять multilingual coverage, а не только latency.

- ASR backend снова переведен на `faster-whisper`: `Transcriber` теперь использует `WhisperModel`, автоматически выбирает `compute_type=int8` на CPU и `float16` на CUDA, строит короткий glossary из `WHISPER_TERMS` и включает `vad_filter` как штатный quality path.
- Для Docker на CPU quality-default изменен с непрактичного `openai-whisper large-v3` на `faster-whisper distil-large-v3`; в конфиг возвращены `WHISPER_COMPUTE_TYPE` и `WHISPER_VAD_FILTER`, а в корень проекта добавлен отсутствовавший `.env.example`.
- Для diarization `.m4a` decode path больше не зависит от `openai-whisper`: используется `faster_whisper.audio.decode_audio`, а существующие guardrails и controlled skip сохранены.
- Переписаны unit-тесты на новый runtime contract `faster-whisper`, `compute_type`, `vad_filter` и glossary prompt; stage-progress в логах также обновлен под новый backend.
- Проверено: `python3 -m compileall meeting_summary tests`
- Проверено: `.venv/bin/python -m unittest discover -s tests -v`
- Проверено: `.venv/bin/python -c "import faster_whisper; print(faster_whisper.__file__)"`
- Проверено: `docker-compose up --build -d`
- Проверено: `docker-compose ps`
- Проверено: `docker inspect meeting-summary --format '{{.RestartCount}} {{.State.Status}} {{.State.OOMKilled}} {{.State.ExitCode}}'`
- Итог Docker verify после пересборки: `RestartCount=0`, `running`, `OOMKilled=false`, `ExitCode=0`, то есть прежний crash-loop `137` после миграции больше не воспроизводится на старте контейнера.

- Для hot-reload добавлен явный путь `OLLAMA_PROMPT_PATH`, prompt теперь читается из файла при каждом новом summary.
- В Docker `./meeting_summary/prompts/summary.md` примонтирован в контейнер как bind mount, поэтому правки на хосте видны без пересборки и без рестарта.
- Добавлены тесты на перечитывание prompt-файла и на понятную ошибку при битом шаблоне.
- Проверено: `.venv/bin/python -m unittest discover -s tests -v`
- Prompt для summary вынесен из `meeting_summary/ollama_client.py` в `meeting_summary/prompts/summary.md`.
- Проверено: `.venv/bin/python -m unittest tests.test_ollama_client -v`
- Добавлен мягкий fallback: при проблеме с `pyannote` обработка файла продолжается без разметки спикеров.
- Маркировка спикеров нормализуется в `Speaker 1`, `Speaker 2`, чтобы markdown и summary были читаемыми.
- Проверено: `.venv/bin/python -m unittest discover -s tests -v`
- Контейнер `meeting-summary` пересобран и поднят через `docker-compose up --build -d`; `docker-compose ps` показывает статус `Up`.
- По логам сервис стартует и watcher активен, но diarization в контейнере не инициализируется: `AttributeError: module 'torchaudio' has no attribute 'AudioMetaData'`.
- Для Docker зафиксирован совместимый стек `pyannote.audio 3.4.0 + huggingface-hub < 1 + torch 2.5.1 + torchaudio 2.5.1` через `constraints-docker.txt`.
- `PyannoteDiarizer` теперь совместим с разными сигнатурами `Pipeline.from_pretrained(...)` и подаёт в pipeline уже загруженный waveform, а не путь к файлу.
- Реальная проверка Docker пройдена: `docker-compose up --build -d`, затем `docker-compose logs --tail=200 meeting-summary` показывает `Loaded pyannote diarization pipeline 'pyannote/speaker-diarization-3.1'.`
- Проверено: `.venv/bin/python -m unittest discover -s tests -v`
- `Settings.load()` теперь берёт дефолтный prompt из package resource `meeting_summary/prompts/summary.md`, поэтому запуск из установленного пакета не зависит от текущей рабочей директории.
- Пустые значения `ENABLE_DIARIZATION=` и `INITIAL_SCAN=` теперь трактуются как выключенные, без ложного включения функциональности из-за пустого env.
- Проверено: `.venv/bin/python -m unittest tests.test_config tests.test_ollama_client tests.test_diarization -v`
- Проверено: `.venv/bin/python -m unittest discover -s tests -v`
- Причина падения diarization на `.m4a` была в том, что `pyannote` грузил аудио через `torchaudio.load`, а этот backend в контейнере не читает текущий контейнер/кодек, хотя `faster-whisper` читает тот же файл нормально.
- Для загрузки аудио в diarization добавлен fallback на `faster_whisper.audio.decode_audio`, который декодирует файл через PyAV/FFmpeg и отдаёт waveform в формате, подходящем для `pyannote`.
- Добавлены unit-тесты на оба сценария: успешный `torchaudio.load` и fallback после ошибки `Format not recognised`.
- Проверено: `.venv/bin/python -m unittest discover -s tests -v`
- Проверено: `docker-compose up --build -d`
- Проверено: `docker-compose ps`
- Проверено: `docker-compose logs --tail=120 meeting-summary`
- Проверено: `docker-compose logs --tail=120 meeting-summary`
- Prompt-шаблон больше не прогоняется через `str.format`, поэтому literal `{}` в редактируемом `.md` не ломают генерацию summary; подставляются только `{language}`, `{duration_seconds}` и `{transcript_block}`.
- `OLLAMA_PROMPT_PATH` теперь резолвится относительно `base_dir`, если задан относительным путём, что выравнивает его поведение с `CALLS_DIR` и сценариями `Settings.load(base_dir=...)`.
- Добавлены регрессионные тесты на literal braces в prompt и на относительный `OLLAMA_PROMPT_PATH`.
- Проверено: `.venv/bin/python -m unittest tests.test_config tests.test_ollama_client -v`
- Проверено: `.venv/bin/python -m unittest discover -s tests -v`
- Транскрибация полностью переведена на `openai-whisper`: `Settings` теперь использует `WHISPER_MODEL` c legacy fallback на `WHISPER_MODEL_SIZE`, а `WHISPER_COMPUTE_TYPE` удалён из активного runtime.
- `Transcriber` теперь загружает модель через `whisper.load_model(...)`, сам резолвит `WHISPER_DEVICE=auto` в `cpu`/`cuda` и собирает `TranscriptionResult` из сегментов `openai-whisper` без изменения downstream-моделей.
- Fallback загрузки аудио для diarization больше не зависит от `faster-whisper`: используется `whisper.load_audio(...)`, а в Docker добавлен отдельный volume для кэша `whisper` при сохранении `huggingface` кэша для `pyannote`.
- Добавлены unit-тесты на новый config fallback и на `Transcriber`; релевантные тесты и полный тестовый набор зелёные.
- Проверено: `python3 -m compileall meeting_summary tests`
- Проверено: `.venv/bin/python -m unittest tests.test_config tests.test_diarization tests.test_transcriber -v`
- Проверено: `.venv/bin/python -m unittest discover -s tests -v`
- Проверено: `.venv/bin/pip install -e .`
- Проверено: `.venv/bin/python -c "import whisper; import meeting_summary.transcriber as transcriber; print(whisper.__file__); print('medium' in whisper.available_models())"`
- Проверено: `docker-compose up --build -d`
- Проверено: `docker-compose ps`
- Для качества распознавания добавлены явные параметры `WHISPER_LANGUAGE`, `WHISPER_INITIAL_PROMPT`, `WHISPER_BEAM_SIZE`, `WHISPER_BEST_OF` и `WHISPER_TEMPERATURE`; `Transcriber` теперь передает их в `openai-whisper`.
- В runtime учтено ограничение текущего `openai-whisper`: `beam_size` и `best_of` нельзя передавать вместе, а `best_of` несовместим с `temperature=0`; поэтому код автоматически использует `beam_size` при `temperature=0` и `best_of` только при ненулевой температуре.
- В `docker-compose.yml` quality-default теперь принудительно задает `WHISPER_MODEL=medium`, `WHISPER_LANGUAGE=ru` и glossary prompt, чтобы контейнер не деградировал из-за legacy `WHISPER_MODEL_SIZE=small` в пользовательском `.env`.
- Документация и `.env.example` переведены на новый quality-first профиль для русского разговора с англоязычными техническими терминами.
- Добавлены unit-тесты на новые настройки config и на фактические аргументы вызова `whisper.transcribe(...)`.
- Проверено: `python3 -m compileall meeting_summary tests`
- Проверено: `.venv/bin/python -m unittest tests.test_config tests.test_transcriber tests.test_diarization -v`
- Проверено: `.venv/bin/python -m unittest discover -s tests -v`
- Проверено: `docker-compose up --build -d`
- Проверено: `docker-compose ps`
- Для `openai-whisper` добавлен staged fallback внутри `Transcriber`: после retryable decode-crash сервис повторяет транскрибацию без `initial_prompt`, затем без `condition_on_previous_text`, а в конце в безопасном greedy-профиле без beam/best_of.
- Retry включается только для конкретного внутреннего decode runtime-error `cannot reshape tensor of 0 elements ...`, чтобы не маскировать реальные ошибки чтения файла или инфраструктуры.
- Длинный glossary prompt больше не навязывается Docker default: `WHISPER_INITIAL_PROMPT` по умолчанию пустой, но поддержка пользовательского prompt сохранена.
- README обновлен: для mixed-language звонков рекомендован короткий glossary prompt, а не длинная инструкция; также зафиксировано автоматическое fallback-поведение при decode-сбое.
- Добавлены регрессионные unit-тесты на staged retry, safe greedy fallback и отсутствие fallback для нерелевантных runtime-ошибок.
- Проверено: `python3 -m compileall meeting_summary tests`
- Проверено: `.venv/bin/python -m unittest tests.test_transcriber tests.test_config tests.test_diarization -v`
- Проверено: `.venv/bin/python -m unittest discover -s tests -v`
- Проверено: `docker-compose up --build -d`
- Для diarization `.m4a` больше не идет по пути `torchaudio -> fallback`: сервис детерминированно декодирует контейнер через `whisper.load_audio`, а `torchaudio` остается основным путем только для PCM-friendly форматов вроде `.wav`.
- В `PyannoteDiarizer` добавлены guardrails для пустых и слишком коротких waveform, поэтому diarization теперь делает controlled skip вместо шумных внутренних warning и бесполезных попыток на вырожденном аудио.
- Для mixed-language качества добавлен `WHISPER_TERMS`: если явный `WHISPER_INITIAL_PROMPT` не задан, `Transcriber` автоматически строит короткий glossary prompt из списка терминов без длинной instruction-style строки.
- В логах появился stage-progress по файлу: watcher сообщает ожидание стабилизации, processor/transcriber логируют стадии `processing_started`, `transcribing`, `diarizing`, `summarizing`, `writing_output`, `completed` или `failed`.
- Шум от сторонних библиотек на старте сервиса снижен в `configure_logging()`: `speechbrain`, `matplotlib` и `lightning*` переведены на `WARNING`, а известное предупреждение `torch.load(weights_only=False)` подавлено как низкосигнальное для этого сервиса.
- Архитектурно решение осталось простым: пайплайн по-прежнему линейный `watcher -> processor -> transcriber/ollama -> markdown`, без лишней очереди или state-machine-модуля; для прогресса добавлен только тонкий callback между `processor` и `transcriber`.
- Добавлены тесты на primary decode path для `.m4a`, controlled skip diarization, `WHISPER_TERMS` и порядок progress-stage логов.
- Проверено: `python3 -m compileall meeting_summary tests`
- Проверено: `.venv/bin/python -m unittest discover -s tests -v`
- Проверено: `docker-compose up --build -d`
- Проверено: `docker-compose ps`
- Docker hot-reload prompt исправлен на mount каталога `meeting_summary/prompts`, поэтому atomic save в VS Code/JetBrains больше не оставляет контейнер на старом inode.
- `pyannote.audio` вынесен в optional extra `.[diarization]`; базовая установка больше не тянет Torch-стек, а `Transcriber` не импортирует diarization-код до фактического включения функции.
- Для сценария `ENABLE_DIARIZATION=true` без установленного extra сохранен fail-soft путь: сервис пишет понятный warning и продолжает обработку без speaker labels.
- Добавлены регрессионные тесты на `docker-compose.yml`, `pyproject.toml` и lazy diarization initialization.
- Проверено: `python3 -m compileall meeting_summary tests`
- Проверено: `.venv/bin/python -m unittest discover -s tests -v`
