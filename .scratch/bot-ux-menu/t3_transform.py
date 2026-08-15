#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T3: кнопка «📋 Меню» на всех TG Send-узлах + тупики + устаревшие тексты.
Правки: .scratch/bot-ux-menu/fixes/wf-tg-bot.json и wf-creatify-webhook.json.
"""
import json, sys

REPO = "/Users/aleksandrtrisenkov/Desktop/PROGRAMMING/РАБОЧИЕ ПРОЕКТЫ/КОНТЕНТ-ЗАВОД-API-MVP/.scratch/bot-ux-menu"
TG_BOT = f"{REPO}/fixes/wf-tg-bot.json"
WEBHOOK = f"{REPO}/fixes/wf-creatify-webhook.json"

MENU_BTN = {"text": "📋 Меню", "additionalFields": {"callback_data": "cmd:menu"}}

def btn(text, cb):
    return {"text": text, "additionalFields": {"callback_data": cb}}

def has_menu_btn(kb):
    if not kb:
        return False
    for r in kb.get("rows", []):
        for b in r.get("row", {}).get("buttons", []):
            cb = (b.get("additionalFields") or {}).get("callback_data", "")
            if "cmd:menu" in cb:
                return True
    return False

def append_menu_row(kb, extra_buttons=None):
    """Добавить строку(и) кнопок в конец клавиатуры; меню — последней кнопкой."""
    rows = kb.get("rows", [])
    if extra_buttons:
        rows.append({"row": {"buttons": extra_buttons + [MENU_BTN]}})
    else:
        rows.append({"row": {"buttons": [MENU_BTN]}})
    kb["rows"] = rows
    return kb

def load(path):
    d = json.load(open(path, encoding="utf-8"))
    return d

def save(path, d):
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps(d, ensure_ascii=False, indent=1))

# ---------------- wf-tg-bot.json ----------------
d = load(TG_BOT)
wf = d[0] if isinstance(d, list) else d
nodes = wf["nodes"]
by = {n["name"]: n for n in nodes}

# Доп. кнопки для тупиков (перед меню). Ключ = имя узла.
EXTRA = {
    "TG topic rejected": [btn("🔄 Запустить цикл", "cmd:start_cycle")],
    "TG script rejected": [btn("🔄 Запустить цикл", "cmd:start_cycle")],
    "TG gen rejected": [btn("⚡ URL→видео", "cmd:gen_url2video"), btn("🎬 AI Shorts", "cmd:gen_shorts")],
    "TG published": [btn("⚡ URL→видео", "cmd:gen_url2video"), btn("🎬 AI Shorts", "cmd:gen_shorts")],
    "TG generating": [btn("🧹 Отмена", "cmd:cancel")],
}

# Тексты тупиков (дословно спека §4.11), ключ = имя узла
TEXTS = {
    "TG topic rejected": "❌ Тема отклонена. Можно запустить цикл заново.",
    "TG script rejected": "❌ Сценарий отклонён. Можно запустить цикл заново.",
    "TG gen rejected": "❌ Видео отклонено. Можно сгенерировать новое.",
    "TG published": "✅ Опубликовано. Можно генерировать дальше.",
    "TG cancel": "✅ Отменено. Текущий шаг прерван.",
    "TG unknown": "Не понял. Нажми «📋 Меню» или напиши: меню",
    "TG ping": "✅ Бот работает (n8n wf-tg-bot active, webhook).",
    "TG generating": "🎬 Видео генерируется... Как только creatify ответит — пришлю ролик.",
    "TG regen": "🔁 Перегенерирую...",
}

added, texts_changed = [], []
for n in nodes:
    if n["type"] != "n8n-nodes-base.telegram":
        continue
    p = n["parameters"]
    if p.get("operation") == "answerQuery":  # answerCallbackQuery — не трогать
        continue
    name = n["name"]
    kb = p.get("inlineKeyboard")
    # 1) тексты тупиков
    if name in TEXTS:
        old = p.get("text")
        new = "={{ '" + TEXTS[name] + "' }}"
        if old != new:
            p["text"] = new
            texts_changed.append((name, old, new))
    # 2) кнопка меню
    if has_menu_btn(kb):
        continue
    if kb is None:
        kb = {"rows": []}
        p["inlineKeyboard"] = kb
    append_menu_row(kb, EXTRA.get(name))
    added.append(name)

save(TG_BOT, d)
print(f"wf-tg-bot: добавлена кнопка меню в {len(added)} узлов")
print("Узлы с добавленной кнопкой:", added)
print("\nИзменённые тексты:")
for name, old, new in texts_changed:
    print(f"  {name}:\n    {old}\n -> {new}")

# ---------------- wf-creatify-webhook.json ----------------
d2 = load(WEBHOOK)
wf2 = d2[0] if isinstance(d2, list) else d2
stage3 = None
for n in wf2["nodes"]:
    if n["name"] == "Telegram stage3":
        stage3 = n
        break
assert stage3 is not None, "Telegram stage3 не найден"
kb = stage3["parameters"].get("inlineKeyboard")
assert kb is not None, "нет inlineKeyboard у stage3"
assert not has_menu_btn(kb), "у stage3 уже есть меню — неожиданно"
append_menu_row(kb)
save(WEBHOOK, d2)
print("\nwf-creatify-webhook: кнопка меню добавлена в Telegram stage3")
print(json.dumps(stage3["parameters"]["inlineKeyboard"], ensure_ascii=False, indent=1))
