# TODO

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
