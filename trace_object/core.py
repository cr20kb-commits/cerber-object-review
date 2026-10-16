"""Validate structure only. No recognition, redaction, networking or submissions."""

import ipaddress
import re
from urllib.parse import urlsplit


FIELDS = {
    "schema_version", "demo", "object_id", "official_url", "description",
    "observations", "limitations", "outcome", "leads",
}
LEAD_FIELDS = {
    "hypothesis", "sources", "matches", "contradictions", "confidence", "next_checks",
}


def text(value):
    return isinstance(value, str) and bool(value.strip()) and len(value) <= 2000 and not any(
        ord(c) < 32 and c not in "\n\t" for c in value
    )


def strings(value):
    return isinstance(value, list) and 0 < len(value) <= 50 and all(text(v) for v in value)


def source_url(value, demo):
    if not isinstance(value, str) or len(value) > 2000 or re.search(r"\s|[\\<>]", value):
        return False
    try:
        u = urlsplit(value)
        host = u.hostname or ""
        if u.scheme != "https" or u.username is not None or u.password is not None or u.port is not None or u.query or u.fragment:
            return False
        if demo:
            return host == "example.invalid" and u.netloc == host
        if not re.fullmatch(r"[a-z0-9]+(?:[a-z0-9.-]*[a-z0-9])?", host):
            return False
        if "." not in host or host.endswith((".invalid", ".localhost", ".local", ".test", ".example")):
            return False
        try:
            ipaddress.ip_address(host)
            return False
        except ValueError:
            return u.netloc == host
    except ValueError:
        return False


def validate(record):
    """Return structural errors without echoing potentially sensitive field values."""
    if not isinstance(record, dict) or set(record) != FIELDS:
        return ["record: expected exactly the documented fields"]
    errors = []
    demo = record["demo"]
    if type(record["schema_version"]) is not int or record["schema_version"] != 1:
        errors.append("schema_version: expected integer 1")
    if type(demo) is not bool:
        errors.append("demo: expected boolean")
    oid = record["object_id"]
    if not isinstance(oid, str) or not re.fullmatch(r"DEMO-[A-Z0-9-]{1,40}" if demo is True else r"C[0-9]{6,12}", oid):
        errors.append("object_id: invalid format")
    url = record["official_url"]
    if demo is True:
        if url is not None:
            errors.append("official_url: demo must use null")
    elif not isinstance(url, str) or not re.fullmatch(r"https://www\.europol\.europa\.eu/stopchildabuse/[0-9]+", url):
        errors.append("official_url: expected official numeric card URL")
    if not text(record["description"]):
        errors.append("description: expected nonempty text")
    for field in ("observations", "limitations"):
        if not strings(record[field]):
            errors.append(field + ": expected nonempty text list")
    outcome = record["outcome"]
    if outcome not in ("candidate", "insufficient_data"):
        errors.append("outcome: unsupported state")
    leads = record["leads"]
    if not isinstance(leads, list) or len(leads) > 20:
        errors.append("leads: expected list of at most 20 items")
        return errors
    if (outcome == "candidate" and not leads) or (outcome == "insufficient_data" and leads):
        errors.append("leads: inconsistent with outcome")
    for index, lead in enumerate(leads):
        prefix = "leads[" + str(index) + "]: "
        if not isinstance(lead, dict) or set(lead) != LEAD_FIELDS:
            errors.append(prefix + "expected exactly the documented fields")
            continue
        if not text(lead["hypothesis"]):
            errors.append(prefix + "invalid hypothesis")
        for field in ("matches", "contradictions", "next_checks"):
            if not strings(lead[field]):
                errors.append(prefix + "invalid " + field)
        if lead["confidence"] not in ("low", "medium"):
            errors.append(prefix + "confidence must remain qualitative and unconfirmed")
        if not strings(lead["sources"]) or not all(source_url(u, demo is True) for u in lead["sources"]):
            errors.append(prefix + "invalid source URLs")
    return errors


def render(record):
    errors = validate(record)
    if errors:
        raise ValueError("; ".join(errors))
    lines = [
        "ЛОКАЛЬНЫЙ РАБОЧИЙ ОТЧЁТ — НЕ ДЛЯ ПУБЛИКАЦИИ",
        "DEMO: вымышленный сценарий" if record["demo"] else "Требуется проверка человеком",
        "ID: " + record["object_id"],
        "Карточка: " + (record["official_url"] or "нет, синтетический пример"),
        "Предмет: " + record["description"],
        "Результат: " + ("неподтверждённый кандидат" if record["outcome"] == "candidate" else "недостаточно данных"),
        "НАБЛЮДЕНИЯ:", *record["observations"],
        "ОГРАНИЧЕНИЯ:", *record["limitations"],
    ]
    for lead in record["leads"]:
        lines += ["ГИПОТЕЗА: " + lead["hypothesis"], "ИСТОЧНИКИ:", *lead["sources"],
                  "СОВПАДЕНИЯ:", *lead["matches"], "ПРОТИВОРЕЧИЯ:", *lead["contradictions"],
                  "УВЕРЕННОСТЬ: " + lead["confidence"], "ЧТО ПРОВЕРИТЬ:", *lead["next_checks"]]
    lines.append("Совпадение предмета не устанавливает личность. Отправка возможна только человеком через Europol.")
    return "\n".join(lines) + "\n"
