from pathlib import Path
import re

p = Path(__file__).resolve().parents[1] / "game" / "data" / "floors.py"
t = p.read_text(encoding="utf-8")
t2 = re.sub(r'("description": "[^"]+")\),', r"\1,", t)
p.write_text(t2, encoding="utf-8")
print("fixed" if t2 != t else "unchanged")
