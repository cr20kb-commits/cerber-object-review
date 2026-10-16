"""Local evidence envelope around the existing record contract; no network I/O."""

from datetime import date, datetime, timezone
import hashlib
from pathlib import Path
import re
from urllib.parse import urlsplit

from .core import render, source_url, strings, text, validate


FIELDS = {"format_version", "record", "provenance", "searches", "comparisons", "conclusion"}
PROVENANCE = {"image_url", "retrieved_at", "sha256", "byte_length", "rights_note", "processing"}
SEARCH = {"query", "kind", "executed_on", "result_note", "sources"}
COMPARISON = {"name", "sources", "matches", "contradictions", "decision", "reason", "next_checks"}


def fingerprint(path):
    """Hash the supplied local bytes, without uploading or modifying the file."""
    digest = hashlib.sha256()
    size = 0
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
            size += len(block)
    return {"sha256": digest.hexdigest(), "byte_length": size}


def utc_time(value):
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.utcoffset() == timezone.utc.utcoffset(parsed)
    except ValueError:
        return False


def source_list(value, demo, allow_empty=False):
    return (value == [] and allow_empty) or (
        strings(value) and all(source_url(item, demo) for item in value)
    )


def image_url(value, demo):
    if demo:
        return source_url(value, True)
    if not isinstance(value, str) or re.search(r"\s|[\\<>]", value):
        return False
    try:
        u = urlsplit(value)
        # A public image-style query may be part of the official URL; never fetch it here.
        return (u.scheme == "https" and u.netloc == "www.europol.europa.eu"
                and u.path.startswith("/cms/sites/default/files/") and not u.fragment)
    except ValueError:
        return False


def validate_pilot(pilot, image_path=None):
    """Validate the log and optionally compare supplied image bytes with recorded SHA-256."""
    if not isinstance(pilot, dict) or set(pilot) != FIELDS:
        return ["pilot: expected exactly the documented envelope fields"]
    errors = []
    if type(pilot["format_version"]) is not int or pilot["format_version"] != 1:
        errors.append("format_version: expected integer 1")
    errors += ["record: " + e for e in validate(pilot["record"])]
    demo = isinstance(pilot["record"], dict) and pilot["record"].get("demo") is True
    p = pilot["provenance"]
    if not isinstance(p, dict) or set(p) != PROVENANCE:
        errors.append("provenance: expected exactly the documented fields")
    else:
        if not image_url(p["image_url"], demo) or not utc_time(p["retrieved_at"]):
            errors.append("provenance: invalid image URL or UTC retrieval time")
        if not isinstance(p["sha256"], str) or not re.fullmatch(r"[a-f0-9]{64}", p["sha256"]):
            errors.append("provenance: expected lowercase SHA-256")
        if type(p["byte_length"]) is not int or p["byte_length"] <= 0:
            errors.append("provenance: invalid byte length")
        if not text(p["rights_note"]) or not strings(p["processing"]):
            errors.append("provenance: rights and processing notes required")
        if image_path is not None:
            actual = fingerprint(image_path)
            if actual["sha256"] != p["sha256"] or actual["byte_length"] != p["byte_length"]:
                errors.append("provenance: supplied image bytes do not match recorded evidence")
    searches = pilot["searches"]
    if not isinstance(searches, list) or not 1 <= len(searches) <= 100:
        errors.append("searches: expected 1 to 100 executed queries")
    else:
        for item in searches:
            if not isinstance(item, dict) or set(item) != SEARCH:
                errors.append("searches: invalid entry fields")
                continue
            if not text(item["query"]) or not text(item["result_note"]):
                errors.append("searches: query and result note required")
            if item["kind"] not in ("web_search", "web_image_search"):
                errors.append("searches: unsupported search kind")
            try:
                if not isinstance(item["executed_on"], str) or date.fromisoformat(item["executed_on"]).isoformat() != item["executed_on"]:
                    raise ValueError()
            except (ValueError, TypeError):
                errors.append("searches: expected execution date YYYY-MM-DD")
            if not source_list(item["sources"], demo, allow_empty=True):
                errors.append("searches: invalid source URLs")
    comparisons = pilot["comparisons"]
    if not isinstance(comparisons, list) or len(comparisons) > 50:
        errors.append("comparisons: expected a list of at most 50 reviewed candidates")
    else:
        if not comparisons and (not isinstance(pilot["record"], dict) or pilot["record"].get("outcome") != "insufficient_data"):
            errors.append("comparisons: empty list requires insufficient_data after a logged search")
        retained = False
        retained_sources = set()
        for item in comparisons:
            if not isinstance(item, dict) or set(item) != COMPARISON:
                errors.append("comparisons: invalid entry fields")
                continue
            for field in ("name", "reason"):
                if not text(item[field]):
                    errors.append("comparisons: invalid " + field)
            for field in ("matches", "contradictions", "next_checks"):
                if not strings(item[field]):
                    errors.append("comparisons: invalid " + field)
            if item["decision"] not in ("rejected", "retained", "inconclusive"):
                errors.append("comparisons: unsupported decision")
            retained = retained or item["decision"] == "retained"
            if not source_list(item["sources"], demo):
                errors.append("comparisons: verified source links required")
            elif item["decision"] == "retained":
                retained_sources.update(item["sources"])
        record = pilot["record"]
        if isinstance(record, dict):
            if retained and record.get("outcome") == "insufficient_data":
                errors.append("comparisons: retained hypothesis requires candidate record outcome")
            if record.get("outcome") == "candidate":
                if not retained:
                    errors.append("comparisons: candidate outcome requires a retained comparison")
                elif isinstance(record.get("leads"), list):
                    for index, lead in enumerate(record["leads"]):
                        # Shared source URLs link the existing structures without changing their fields.
                        # Whether the comparison actually supports the text still needs human review.
                        if isinstance(lead, dict) and strings(lead.get("sources")) and not retained_sources.intersection(lead["sources"]):
                            errors.append("record: leads[" + str(index) + "]: expected a source shared with a retained comparison")
    if not text(pilot["conclusion"]):
        errors.append("conclusion: expected explicit bounded result")
    return errors


def render_pilot(pilot, image_path):
    errors = validate_pilot(pilot, image_path)
    if errors:
        raise ValueError("; ".join(errors))
    p = pilot["provenance"]
    lines = ["ЛОКАЛЬНЫЙ ПИЛОТ — НЕ ДЛЯ ПУБЛИКАЦИИ", "ВЫВОД: " + pilot["conclusion"],
             "ЗАПРОСОВ: " + str(len(pilot["searches"])) + "; РАССМОТРЕНО КАНДИДАТОВ: " + str(len(pilot["comparisons"])),
             "КРАТКИЕ РЕШЕНИЯ:"]
    for item in pilot["comparisons"]:
        lines.append(item["name"] + " / " + item["decision"] + ": " + item["reason"])
    if not pilot["comparisons"]:
        lines.append("Кандидаты не найдены по выполненному поиску; сравнивать нечего.")
    lines += ["ПОДРОБНАЯ ЗАПИСЬ:", render(pilot["record"]), "ПРОИСХОЖДЕНИЕ И ПРОВЕРКА БАЙТОВ:",
             "URL изображения: " + p["image_url"], "Получено UTC: " + p["retrieved_at"],
             "SHA-256: " + p["sha256"], "Размер в байтах: " + str(p["byte_length"]),
             "Предоставленные локальные байты совпадают с записью: ДА",
             "Права: " + p["rights_note"], "Преобразования:", *p["processing"],
             "ЖУРНАЛ ФАКТИЧЕСКИХ ПОИСКОВ:"]
    for index, item in enumerate(pilot["searches"], 1):
        lines += [str(index) + ". " + item["kind"] + " / " + item["executed_on"],
                  item["query"], item["result_note"], *item["sources"]]
    lines.append("СРАВНЕНИЯ:")
    for item in pilot["comparisons"]:
        lines += [item["name"], "ИСТОЧНИКИ:", *item["sources"], "СОВПАДЕНИЯ:", *item["matches"],
                  "ПРОТИВОРЕЧИЯ:", *item["contradictions"], "РЕШЕНИЕ: " + item["decision"],
                  item["reason"], "ЧТО ПРОВЕРИТЬ:", *item["next_checks"]]
    lines += ["ВЫВОД:", pilot["conclusion"], "ИСПОЛНИТЕЛИ:",
              "Программа: проверка структуры, SHA-256/размера и формирование этого отчёта.",
              "Codex/оператор: просмотр изображения, чтение признаков, запросы, проверка страниц и внесение решений.",
              "Человек: независимая проверка значимой гипотезы, прав и любого сообщения Europol.",
              "Журнал введён оператором. Программа не доказывает выполнение поиска или истинность выводов."]
    return "\n".join(lines) + "\n"
