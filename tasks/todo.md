# TODO

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
