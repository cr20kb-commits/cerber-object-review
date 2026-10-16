# Проверка перед публикацией / Publication review

Публичный модуль выделен в новый репозиторий с самостоятельной историей.
Родительская папка CERBER не являлась Git-репозиторием при осмотре 2026-10-16.
Её исходники, сборки, evidence, резервные копии, движки и локальные отчёты не импортировались.

Публикуются только собственный код модуля, документация, GitHub-шаблоны,
проверки и два вымышленных JSON-примера. Изображений и материалов дел нет.

Перед каждой публикацией:

1. `git status --short --branch`; проверить фактический индекс и diff.
2. Добавлять только явно рассмотренные файлы, не использовать широкое добавление из родительской папки.
3. `python -m unittest discover -s tests -v` и `python -m trace_object demo`.
4. `python tools/audit_publication.py` проверяет индекс, соответствие рабочим файлам,
   все доступные refs/reflogs, пути, двоичные файлы, типичные ключи, личные пути и email.
   Не обходить FAIL. После коммита запустить аудит снова для проверки metadata/history.
   В PR workflow проверяет конкретный head-коммит ветки и его историю. GitHub
   формирует отдельный временный merge-коммит со служебными/profile metadata;
   он не является авторским коммитом ветки. Совместимость после слияния с будущими
   изменениями base-ветки этим запуском не подтверждается.
5. Отдельно прочитать весь публикуемый текст: пароли в произвольной форме, имена,
   адреса и рабочие материалы не определяются надёжно регулярными выражениями.
6. Проверить `git check-ignore` для `.local/reports/`, `.env`, изображений, архивов,
   SQLite и рабочих материалов. `.gitignore` не удаляет уже отслеживаемое.
7. После публикации проверить GitHub API и страницу без Authorization/cookies:
   репозиторий public, файлы доступны. Не выдавать локальные проверки за прошедший remote CI.

MIT относится к собственным материалам. Ни лицензия, ни аудит не дают прав на
внешние картинки. Issues не заменяют официальный канал Europol и могут содержать
небезопасный пользовательский текст: требуются модерация и проверка человеком.

The audit covers indexed blobs and reachable/reflog commit content and metadata,
not deleted unreachable Git objects, arbitrary untracked local files or remote user content.
It is a common-secret/path check, not a complete secret or personal-data detector.
Future maintainers must inspect actual content and history before publishing.
