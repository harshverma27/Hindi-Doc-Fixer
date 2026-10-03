import difflib
import json
import re
import unicodedata
import urllib.request
from pathlib import Path

import docx

MODEL = "gemma3:1b"
DEVANAGARI = re.compile(r"[ऀ-ॿ]")
SPELLING = str.maketrans({
    "ी": "ि", "ू": "ु", "ै": "े", "ौ": "ो",
    "ई": "इ", "ऊ": "उ", "ऐ": "ए", "औ": "ओ",
    "ं": None, "ँ": None, "़": None,
})
LIST_MARK = re.compile(r"^\s*([0-9०-९]+|[a-zA-Zक-ह])[.)]\s+")

PROMPT = """तुम एक हिंदी शिक्षक हो। वाक्य में केवल वर्तनी और मात्रा की गलतियाँ ठीक करो। कोई शब्द मत हटाओ, कोई शब्द मत जोड़ो, अर्थ मत बदलो। केवल सुधरा हुआ वाक्य लौटाओ।

वाक्य: में कल बाजार जाउंगा।
सुधरा: मैं कल बाज़ार जाऊँगा।

वाक्य: छात्रो को पुस्तके पढनी चाहिये।
सुधरा: छात्रों को पुस्तकें पढ़नी चाहिए।

वाक्य: {text}
सुधरा:"""


def ask_model(text):
    body = json.dumps({
        "model": MODEL,
        "prompt": PROMPT.format(text=text),
        "stream": False,
        "options": {"temperature": 0},
    }).encode()
    req = urllib.request.Request("http://localhost:11434/api/generate", body)
    with urllib.request.urlopen(req) as r:
        return json.load(r)["response"].strip().splitlines()[0].strip()


def canon(word):
    # Collapse the differences voice typing gets wrong: vowel length, े/ै,
    # ो/ौ, nasal marks, nukta and ये/ए. Two words with the same canon differ
    # only in spelling; anything else is a different word or grammar.
    return unicodedata.normalize("NFD", word).translate(SPELLING).replace("ये", "ए")


def close(x, y):
    return x != y and canon(x) == canon(y)


def merge(old, new):
    # The small model sometimes drops, adds or swaps words. Keep only the
    # word-for-word spelling fixes, put them back in place so her spacing
    # stays, and leave everything else as she wrote it.
    a, b = old.split(), new.split()
    fixed = list(a)
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b).get_opcodes():
        if op == "replace" and i2 - i1 == j2 - j1:
            for k, (x, y) in enumerate(zip(a[i1:i2], b[j1:j2])):
                if close(x, y):
                    fixed[i1 + k] = y
    words = iter(fixed)
    return re.sub(r"\S+", lambda m: next(words), old)


def fix_text(text):
    if not DEVANAGARI.search(text):
        return text
    # list numbers like "1." or "क)" confuse the model, send only the sentence
    m = LIST_MARK.match(text)
    head, body = (m.group(), text[m.end():]) if m else ("", text)
    return head + merge(body, ask_model(body))


def fix_docx(path):
    doc = docx.Document(path)
    changes = []
    for p in doc.paragraphs:
        old = p.text
        if not old.strip():
            continue
        if old.lstrip().startswith("#"):
            # she marked this line to keep as is (e.g. a "correct this" question),
            # drop the marker and move on
            r = next(r for r in p.runs if "#" in r.text)
            r.text = re.sub(r"#\s*", "", r.text, count=1)
            continue
        new = fix_text(old)
        if new != old:
            # ponytail: whole paragraph takes the first run's formatting,
            # per-run rewrite if mid-line bold/italic matters
            for r in p.runs[1:]:
                r._element.getparent().remove(r._element)
            p.runs[0].text = new
            changes.append((old, new))
    out = Path(path).with_name(Path(path).stem + "_सुधरा.docx")
    doc.save(out)
    return out, changes


if __name__ == "__main__":
    import gradio as gr

    def run(file):
        out, changes = fix_docx(file)
        if not changes:
            return str(out), "कोई गलती नहीं मिली।"
        report = "\n\n".join(f"पहले: {a}\nअब:   {b}" for a, b in changes)
        return str(out), report

    gr.Interface(
        fn=run,
        inputs=gr.File(label="अपनी Word फ़ाइल डालें", file_types=[".docx"]),
        outputs=[gr.File(label="सुधरी हुई फ़ाइल"), gr.Textbox(label="बदलाव", lines=12)],
        title="मेरा दस्तावेज़ ठीक करो",
        flagging_mode="never",
    ).launch()
