"""UI resource file parsing/reconstruction — Design ref: `LOCKED_Design_v1.0.md`
§4.3; `Requirements_Document.md` §3.3 (expected formats: JSON, XML,
Properties, YAML, RESX — exact formats pending UI-resource analysis, an open
item per `Requirements/Open_Items_Tracker.md`). Story 5.3.

Each format extracts to the same shape — `{dotted.key.path: source_text}` —
so the rest of the pipeline (Lokalise upload, translation-key naming,
reconstruction) is format-agnostic.
"""
import json
from typing import Any

import yaml
from lxml import etree

SUPPORTED_FORMATS = ("json", "yaml", "properties", "xml", "resx")


def detect_format(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext in ("yml", "yaml"):
        return "yaml"
    if ext in SUPPORTED_FORMATS:
        return ext
    raise ValueError(f"Unsupported UI resource format for '{filename}' (expected one of {SUPPORTED_FORMATS})")


def extract_strings(file_bytes: bytes, fmt: str) -> dict[str, str]:
    if fmt == "json":
        return _json_extract(json.loads(file_bytes.decode("utf-8")))
    if fmt == "yaml":
        return _json_extract(yaml.safe_load(file_bytes.decode("utf-8")) or {})
    if fmt == "properties":
        return _properties_extract(file_bytes.decode("utf-8"))
    if fmt in ("xml", "resx"):
        return _xml_extract(file_bytes)
    raise ValueError(f"Unsupported format '{fmt}'")


def reconstruct(file_bytes: bytes, fmt: str, translations: dict[str, str]) -> bytes:
    if fmt == "json":
        data = json.loads(file_bytes.decode("utf-8"))
        _json_apply(data, translations)
        return json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    if fmt == "yaml":
        data = yaml.safe_load(file_bytes.decode("utf-8")) or {}
        _json_apply(data, translations)
        return yaml.safe_dump(data, allow_unicode=True, sort_keys=False).encode("utf-8")
    if fmt == "properties":
        return _properties_reconstruct(file_bytes.decode("utf-8"), translations)
    if fmt in ("xml", "resx"):
        return _xml_reconstruct(file_bytes, translations)
    raise ValueError(f"Unsupported format '{fmt}'")


# ---- JSON / YAML (shared tree-walk since yaml.safe_load produces dict/list too) ----


def _json_extract(node: Any, prefix: str = "") -> dict[str, str]:
    strings: dict[str, str] = {}
    if isinstance(node, dict):
        for key, value in node.items():
            strings.update(_json_extract(value, f"{prefix}.{key}" if prefix else str(key)))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            strings.update(_json_extract(value, f"{prefix}[{index}]"))
    elif isinstance(node, str) and node.strip():
        strings[prefix] = node
    return strings


def _json_apply(node: Any, translations: dict[str, str], prefix: str = "") -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if isinstance(value, str) and path in translations:
                node[key] = translations[path]
            else:
                _json_apply(value, translations, path)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            path = f"{prefix}[{index}]"
            if isinstance(value, str) and path in translations:
                node[index] = translations[path]
            else:
                _json_apply(value, translations, path)


# ---- Properties (Java-style key=value) ----


def _properties_extract(text: str) -> dict[str, str]:
    strings: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "!")) or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        strings[key.strip()] = value.strip()
    return strings


def _properties_reconstruct(text: str, translations: dict[str, str]) -> bytes:
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith(("#", "!")) and "=" in stripped:
            key, _, _ = stripped.partition("=")
            key = key.strip()
            if key in translations:
                lines.append(f"{key}={translations[key]}")
                continue
        lines.append(line)
    return ("\n".join(lines) + "\n").encode("utf-8")


# ---- XML (generic + Android `strings.xml` + .NET RESX dialects) ----


def _xml_extract(file_bytes: bytes) -> dict[str, str]:
    root = etree.fromstring(file_bytes)
    strings: dict[str, str] = {}

    if root.tag == "resources":  # Android strings.xml
        for element in root.findall("string"):
            name = element.get("name")
            if name and element.text:
                strings[name] = element.text
        return strings

    if root.tag == "root" and root.find("data") is not None:  # .NET RESX
        for element in root.findall("data"):
            name = element.get("name")
            value_el = element.find("value")
            if name and value_el is not None and value_el.text:
                strings[name] = value_el.text
        return strings

    # Generic fallback: every leaf element's text, keyed by an XPath-ish path.
    for element in root.iter():
        if list(element):
            continue
        if element.text and element.text.strip():
            strings[_element_path(element)] = element.text
    return strings


def _xml_reconstruct(file_bytes: bytes, translations: dict[str, str]) -> bytes:
    root = etree.fromstring(file_bytes)

    if root.tag == "resources":
        for element in root.findall("string"):
            name = element.get("name")
            if name in translations:
                element.text = translations[name]
        return etree.tostring(root, xml_declaration=True, encoding="UTF-8")

    if root.tag == "root" and root.find("data") is not None:
        for element in root.findall("data"):
            name = element.get("name")
            value_el = element.find("value")
            if name in translations and value_el is not None:
                value_el.text = translations[name]
        return etree.tostring(root, xml_declaration=True, encoding="UTF-8")

    for element in root.iter():
        if list(element):
            continue
        path = _element_path(element)
        if path in translations:
            element.text = translations[path]
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8")


def _element_path(element: etree._Element) -> str:
    parts = []
    node = element
    while node is not None:
        parts.append(node.tag)
        node = node.getparent()
    return "/".join(reversed(parts))
