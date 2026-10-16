# Контракт записи / Record contract

UTF-8 JSON object; все перечисленные поля обязательны, неизвестные поля отклоняются.
См. два синтетических файла в `examples/`. Текст проверяется человеком.

| Поле | Тип / правило |
| --- | --- |
| schema_version | integer `1` |
| demo | boolean; только вымышленные примеры используют `true` |
| object_id | `DEMO-...` для demo; `C` + 6–12 цифр для официальной карточки |
| official_url | `null` для demo; `https://www.europol.europa.eu/stopchildabuse/<числовой ID>` для реальной |
| description | непустое описание предмета, до 2000 символов |
| observations | массив непустых строк с видимыми признаками |
| limitations | непустой массив строк с ограничениями |
| outcome | `candidate` или `insufficient_data` |
| leads | массив кандидатов; непустой только для `candidate` |

Каждый элемент `leads` содержит только `hypothesis` (строка), `sources` (массив
HTTPS-ссылок без логина, пароля, query и fragment), `matches`, `contradictions`,
`next_checks` (непустые массивы строк), `confidence` (`low` или `medium`).
Если противоречия неизвестны, укажите это явно, а не утверждайте их отсутствие.
В demo товарные ссылки должны вести на зарезервированный `example.invalid`.
В реальных записях демонстрационные и локальные адреса запрещены; валидатор
не загружает ссылки и не гарантирует их публичность или безопасность назначения.

Only qualitative, unconfirmed confidence is supported. Structural validation cannot
verify facts, the ID-to-URL relationship, URL availability, rights or personal-data absence.
No field may contain identifying people or accusations. Work records remain local.
