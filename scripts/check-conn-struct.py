import json

with open('workflows/wf-tg-bot.json', encoding='utf-8') as f:
    raw = json.load(f)

d = raw[0]
print("Keys:", list(d.keys()))
c = d.get('connections', {})
print("Connections type:", type(c))
print("Connections keys:", list(c.keys())[:5])
if c:
    k = list(c.keys())[0]
    print("Sample connection:", k, "->", c[k])
