#!/usr/bin/env python3
"""Статические тесты приёмки тикета 04 — качество промптов hermes-скиллов.

Проверяет публичный интерфейс промптов: отсутствие хардкода Robotec,
использование активного профиля, формат сценария 30 сек, json-builder без
markdown-обёртки. Не вызывает LLM и не тратит кредиты.
"""
import re
import sys
from pathlib import Path

SKILLS_DIR = Path.cwd() / "hermes" / "skills"
SKILLS = {
    "analyst": {"active": True},
    "scriptwriter": {"active": True, "words": (90, 110), "repeat": True},
    "json-builder": {"active": True, "no_markdown": True},
    "onboarding": {"active": False},  # строит новый профиль из URL
    "orchestrator": {"active": True},
    "caption-adapter": {"active": True, "platforms": True},
}


def read(skill):
    return (SKILLS_DIR / f"{skill}.md").read_text(encoding="utf-8")


def assert_no_robotec(skill, text):
    if re.search(r"(?i)robotec", text) and not re.search(r"[Нн]е хардкоди.*Robotec", text):
        fail(skill, "найден хардкод 'Robotec'")


def assert_active_profile(skill, text, cfg):
    markers = [
        "active_client_id",
        "активный профиль",
        "профиль клиента",
        "client_profile",
        "active_client_name",
    ]
    if cfg.get("active") and not any(m in text for m in markers):
        fail(skill, "не указано использование активного профиля клиента")


def assert_scriptwriter_format(text):
    if not re.search(r"90[–\-]110\s+слов", text):
        fail("scriptwriter", "не найден лимит 90–110 слов")
    if not re.search(r"30\s+(сек|секунд)", text):
        fail("scriptwriter", "не найдена длительность 30 сек")
    if not re.search(r"повтор", text, re.IGNORECASE):
        fail("scriptwriter", "не найдено правило про 1 повтор")
    if "markdown-обёртки" not in text and "```json" not in text:
        if "без markdown" not in text:
            fail("scriptwriter", "не найдено требование strict JSON без markdown")


def assert_json_builder_no_markdown(text):
    if "markdown-обёртки" not in text and "```json" not in text:
        fail("json-builder", "не найдено требование выводить JSON без markdown-обёртки")
    m = re.search(r'"name"\s*:\s*"([^"]+)"', text)
    if m and ("robotec" in m.group(1).lower() or "welding" in m.group(1).lower()):
        fail("json-builder", f"пример name содержит хардкод: {m.group(1)}")


def assert_caption_adapter(text):
    required_platforms = [
        "instagram",
        "tiktok",
        "youtube",
        "telegram",
        "x",
        "threads",
        "vk",
    ]
    lower = text.lower()
    for p in required_platforms:
        if p not in lower:
            fail("caption-adapter", f"не упомянута платформа {p}")
    if "280" not in text:
        fail("caption-adapter", "не найдено ограничение 280 символов для X")
    if "telegram" not in lower or "markdown" not in lower:
        fail("caption-adapter", "не найдено требование markdown для Telegram")
    if "raw url" not in lower and "markdown-ссылок" not in lower and "без markdown" not in lower:
        fail("caption-adapter", "не найдено требование raw URL/без markdown-ссылок для VK")


def fail(skill, msg):
    print(f"FAIL {skill}: {msg}")
    sys.exit(1)


def main():
    print("RUN test-04-content-quality-prompts")
    for skill, cfg in SKILLS.items():
        text = read(skill)
        assert_no_robotec(skill, text)
        assert_active_profile(skill, text, cfg)
        if skill == "scriptwriter":
            assert_scriptwriter_format(text)
        if skill == "json-builder":
            assert_json_builder_no_markdown(text)
        if skill == "caption-adapter":
            assert_caption_adapter(text)
        print(f"PASS {skill}")
    print("OK all checks passed")


if __name__ == "__main__":
    main()
