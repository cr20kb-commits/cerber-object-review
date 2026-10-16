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
LINK = {"lead_index", "comparison_id"}


def comparison_id(value):
    return isinstance(value, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", value) is not None


def validate_links(links, record, comparisons):
    """Require a one-to-one link between record leads and retained comparison IDs."""
    if not isinstance(links, list) or len(links) > 20:
        return ["lead_links: expected a list of at most 20 links"]
    errors = []
    leads = record.get("leads") if isinstance(record, dict) else None
    seen_leads, seen_comparisons = set(), set()
    for link in links:
        if not isinstance(link, dict) or set(link) != LINK:
            errors.append("lead_links: expected lead_index and comparison_id")
            continue
        index, cid = link["lead_index"], link["comparison_id"]
        if type(index) is not int or not isinstance(leads, list) or not 0 <= index < len(leads):
            errors.append("lead_links: lead_index must identify an existing lead")
            continue
        if index in seen_leads:
            errors.append("lead_links: each lead must have exactly one link")
        seen_leads.add(index)
        if not comparison_id(cid) or cid not in comparisons:
            errors.append("lead_links: comparison_id must identify an existing comparison")
            continue
        if cid in seen_comparisons:
            errors.append("lead_links: a comparison cannot support multiple leads")
        seen_comparisons.add(cid)
        item = comparisons[cid]
        if item["decision"] != "retained":
            errors.append("lead_links: a lead must reference a retained comparison")
        lead = leads[index]
        if isinstance(lead, dict) and strings(lead.get("sources")) and strings(item["sources"]):
            if not set(lead["sources"]).issubset(item["sources"]):
                errors.append("lead_links: lead sources must belong to its referenced comparison")
    if isinstance(leads, list) and seen_leads != set(range(len(leads))):
        errors.append("lead_links: every lead requires a link")
    retained = {cid for cid, item in comparisons.items() if item["decision"] == "retained"}
    if retained - seen_comparisons:
        errors.append("lead_links: every retained comparison requires a lead")
    return errors


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
    if not isinstance(pilot, dict):
        return ["pilot: expected exactly the documented envelope fields"]
    version = pilot.get("format_version")
    if type(version) is not int or version not in (1, 2):
        return ["format_version: expected integer 1 or 2"]
    fields = FIELDS | {"lead_links"} if version == 2 else FIELDS
    if set(pilot) != fields:
        return ["pilot: expected exactly the documented envelope fields"]
    errors = []
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
        identities, by_id = set(), {}
        for item in comparisons:
            fields = COMPARISON | {"comparison_id"} if version == 2 else COMPARISON
            if not isinstance(item, dict) or set(item) != fields:
                errors.append("comparisons: invalid entry fields")
                continue
            if version == 2:
                cid = item["comparison_id"]
                if not comparison_id(cid):
                    errors.append("comparisons: invalid comparison_id")
                elif cid in by_id:
                    errors.append("comparisons: duplicate comparison_id")
                else:
                    by_id[cid] = item
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
            elif text(item["name"]):
                # Reassigning an ID must not hide two decisions for the same declared variant.
                identity = (" ".join(item["name"].split()).casefold(), frozenset(item["sources"]))
                if identity in identities:
                    errors.append("comparisons: duplicate candidate name and sources")
                identities.add(identity)
        record = pilot["record"]
        if isinstance(record, dict):
            if retained and record.get("outcome") == "insufficient_data":
                errors.append("comparisons: retained hypothesis requires candidate record outcome")
            if record.get("outcome") == "candidate":
                if not retained:
                    errors.append("comparisons: candidate outcome requires a retained comparison")
                if version == 1:
                    errors.append("format_version: candidate pilots require version 2 with explicit lead_links")
        if version == 2:
            errors += validate_links(pilot["lead_links"], record, by_id)
    if not text(pilot["conclusion"]):
        errors.append("conclusion: expected explicit bounded result")
    return errors


def render_pilot(pilot, image_path):
    if image_path is None:
        raise ValueError("image_path: a local file is required to render a pilot")
    errors = validate_pilot(pilot, image_path)
    if errors:
        raise ValueError("; ".join(errors))
    p = pilot["provenance"]
    result = ("неподтверждённый кандидат" if pilot["record"]["outcome"] == "candidate" else "недостаточно данных")
    lines = ["ЛОКАЛЬНЫЙ ПИЛОТ — НЕ ДЛЯ ПУБЛИКАЦИИ", "РЕЗУЛЬТАТ ПО OUTCOME: " + result,
             "ЗАПРОСОВ: " + str(len(pilot["searches"])) + "; РАССМОТРЕНО КАНДИДАТОВ: " + str(len(pilot["comparisons"])),
             "КРАТКИЕ РЕШЕНИЯ:"]
    for item in pilot["comparisons"]:
        label = (item["comparison_id"] + " / ") if pilot["format_version"] == 2 else ""
        lines.append(label + item["name"] + " / " + item["decision"] + ": " + item["reason"])
    if not pilot["comparisons"]:
        lines.append("Кандидаты не найдены по выполненному поиску; сравнивать нечего.")
    if pilot["format_version"] == 2:
        lines.append("СВЯЗИ ГИПОТЕЗ СО СРАВНЕНИЯМИ:")
        for link in pilot["lead_links"]:
            lines.append("leads[" + str(link["lead_index"]) + "] -> " + link["comparison_id"])
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
        label = (item["comparison_id"] + " / ") if pilot["format_version"] == 2 else ""
        lines += [label + item["name"], "ИСТОЧНИКИ:", *item["sources"], "СОВПАДЕНИЯ:", *item["matches"],
                  "ПРОТИВОРЕЧИЯ:", *item["contradictions"], "РЕШЕНИЕ: " + item["decision"],
                  item["reason"], "ЧТО ПРОВЕРИТЬ:", *item["next_checks"]]
    lines += ["КОММЕНТАРИЙ ОПЕРАТОРА — НЕ ПРОВЕРЕН ПРОГРАММОЙ:"]
    lines += ["> " + line for line in pilot["conclusion"].splitlines()]
    lines += ["ИТОГ ПО OUTCOME: " + result, "ИСПОЛНИТЕЛИ:",
              "Программа: проверка структуры, SHA-256/размера и формирование этого отчёта.",
              "Codex/оператор: просмотр изображения, чтение признаков, запросы, проверка страниц и внесение решений.",
              "Человек: независимая проверка значимой гипотезы, прав и любого сообщения Europol.",
              "Журнал введён оператором. Программа не доказывает выполнение поиска или истинность выводов."]
    return "\n".join(lines) + "\n"
