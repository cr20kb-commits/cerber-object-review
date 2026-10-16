# Участие / Contributing

Проект независим от Europol. Помочь можно кодом, тестами, переводом и проверкой
товарных аналогов; никаких специальных доступов и платных сервисов не требуется.

## Разработка / Development

1. Выберите задачу из [VOLUNTEER_TASKS.md](VOLUNTEER_TASKS.md), проверьте существующие Issues.
2. Создайте fork и отдельную ветку. Изменяйте минимальный необходимый объём.
3. Не добавляйте зависимости без объяснения необходимости; не включайте реальные
   материалы дел в тесты. Новые примеры должны быть полностью вымышленными.
4. Выполните `python -m unittest discover -s tests -v` и `python tools/audit_publication.py`.
5. Перед PR просмотрите diff и новые файлы вручную. Укажите поведение, проверки и ограничения.

Fork, use a focused branch, add synthetic tests, run the commands above and describe
the change and its limits. Contributions are provided under the repository's MIT licence;
submit only material you have the right to license. Third-party assets require separate review.

## Проверка совпадений / Reviewing matches

Используйте шаблон распознавания предмета: официальный ID + URL, описание объекта,
наблюдение → гипотеза → источники → совпадения → противоречия → уверенность → что проверить.
Ссылки на открытые каталоги производителей и продавцов допустимы; не копируйте их изображения.
Проверяйте дату, модель, варианты, признаки и альтернативы. Сходство и рынок продаж
не устанавливают личность и место съёмки. Не выдавайте вывод ИИ за наблюдение.
Независимый человек должен попытаться опровергнуть кандидата по признакам.

Use official card IDs/links and public product sources. Record observations, hypotheses,
matches, contradictions, confidence and next checks. A second human should challenge
the candidate. An AI suggestion is not evidence and an object match is not an identification.

## Публичные обсуждения / Public discussions

Issues и PR общедоступны. Никаких личных данных, имён предполагаемых подозреваемых,
адресов потерпевших, обвинений, узнаваемых людей и рабочих отчётов.
Не прикрепляйте изображения, логи, архивы или снимки экрана с данными дел.
Не переносите исходные материалы насилия и не ищите их. Не контактируйте с людьми по гипотезам.
Пишите о свойствах предмета и товарных источниках, без историй о причастности людей.

Public Issues/PRs must not contain personal data, suspected persons, victim addresses,
accusations, case reports or identifying imagery. Do not upload case attachments or
contact people based on hypotheses. Recheck all free text manually; templates do not redact it.

Существенные сведения после проверки человеком направляются через официальную карточку
[Europol](https://www.europol.europa.eu/stopchildabuse), не через GitHub и не автоматически.
Обозначьте применение ИИ и ограничения. Предварительный английский черновик храните локально.

After human verification, submit significant information using the official Europol
card form, disclosing AI assistance if used. No automatic submission. Keep drafts local.

## Модерация / Moderation

При появлении чувствительных сведений не цитируйте и не тиражируйте их.
Автор должен удалить содержимое; сопровождающий скрывает/удаляет доступные ему публикации
и при необходимости обращается в GitHub Support за удалением истории.
Удаление текста из текущей версии не гарантирует удаления копий и уведомлений.
Не сообщайте об утечке публичным Issue; используйте приватный канал GitHub из [SECURITY.md](SECURITY.md).
