# Первые задачи / First volunteer tasks

Все проверки — на вымышленных примерах или обычных предметах с разрешёнными материалами.
Не добавляйте реальные дела в fixtures. Открывайте отдельный Issue по выбранной задаче.

| Задача / Task | Готово, когда / Acceptance |
| --- | --- |
| RU/EN: вычитать документацию | Обе версии одинаково описывают запуск, ограничения и правила публикации |
| Тесты URL | Добавлены проверки Unicode-host, портов, userinfo, redirects-as-query без сетевых запросов |
| Дубликаты карточек | Предложен локальный реестр ID/URL с тестом повторного импорта, без публикации данных |
| Даты и происхождение | Спроектированы local-only retrieved_at/SHA-256 и тесты без реальных изображений |
| Проверка кандидатов | Описан воспроизводимый процесс сравнения формы/надписей и опровержения гипотез |
| Доступность отчёта | Проверена читаемость русского отчёта и предложена EN-версия на синтетических данных |
| Контракт JSON | Подготовлена схема JSON Schema, согласованная с существующим валидатором |
| Безопасность публикации | Найдены пробелы проверки истории/индекса и добавлены синтетические regression tests |

Start with documentation parity, adversarial URL tests, a private duplicate registry,
local provenance design, candidate falsification, report accessibility, JSON Schema or
publication-audit tests. Each PR must explain its acceptance checks. No task authorises
scraping, contacting people, submitting leads or uploading third-party images.
