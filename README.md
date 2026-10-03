# Hindi doc fixer

My mom teaches Hindi. She types her Word files with Gboard's Hindi handwriting and voice input, and the text comes out with small spelling and matra mistakes. Fixing them by hand takes her a long time.

This is a small page on my laptop. She uploads a .docx and gets back a fixed copy. Her original file is not touched.

It runs Gemma 3 1B through Ollama on the laptop, so her files never leave it.

## What it fixes

Only spelling-type mistakes:

- short or long matra (ि/ी, ु/ू)
- े/ै and ो/ौ
- missing or extra ं and ँ
- nukta (ढ/ढ़)
- ये/ए (लिये to लिए)

If the model changes a word into a different word, drops a word, or touches punctuation, that change is thrown away and her text stays as it was. Spacing, headings and English lines are left alone.

## Keeping a line as it is

Start the line with `#`. The app skips it and removes the `#` in the fixed copy. Useful for a student's sentence that is wrong on purpose.

## Setup

You need Python 3 and [Ollama](https://ollama.com).

```bash
ollama pull gemma3:1b
python -m venv .venv
.venv/bin/pip install python-docx gradio
```

## Run

```bash
.venv/bin/python app.py
```

Open http://localhost:7860, upload a .docx, download the fixed file. The page also lists every line it changed.

Try it with `sample_day_report.docx`.

## Test

```bash
.venv/bin/python test_fix.py
```

Needs Ollama running.

## Limits

- Tables are not checked yet.
- If a line gets fixed, bold or italic on a single word inside that line is lost.
- The 1B model misses some mistakes. It's better to miss one than to change her words.
