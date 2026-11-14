"""
Verifica cobertura de páginas entre faixas e capítulos entre rotas.
Usa apenas metadados (ingest.json, conversao.json, nomes de arquivos).
Saída ≤ 20 linhas.
"""
import json
import os
import re

BASE = "/app/data/processed"

HASHES = {
    "full":  "8648c8a89ec5c8c75e28228a9d222e241370c10e711b65ea17bf3dd4b646dbde",
    "p1-40": "e40ecc1a069cc78566546a0a1bb05f83089d4d607b0e6f92002370703d490b6c",
}

DOCLING_VERSION = "2.150.0-noocr-notables-imgplaceholder-b1"


def load(hash_key, filename):
    path = os.path.join(BASE, HASHES[hash_key], filename)
    with open(path) as f:
        return json.load(f)


# ── 1. Cobertura de páginas 1-379 (faixas do livro completo) ─────────────────
docling_dir = os.path.join(BASE, HASHES["full"], "docling", DOCLING_VERSION)
range_files = sorted(os.listdir(docling_dir))

covered = set()
duplicates = []
for fname in range_files:
    m = re.match(r"pages_(\d+)-(\d+)\.json", fname)
    if not m:
        continue
    start, end = int(m.group(1)), int(m.group(2))
    for p in range(start, end + 1):
        if p in covered:
            duplicates.append(p)
        covered.add(p)

all_pages = set(range(1, 380))
gaps = sorted(all_pages - covered)

# Motivos de ausência: ingest.json removed + conversao.json removidos
ingest_full = load("full", "ingest.json")
conv_full   = load("full", "conversao.json")

removed_map = {}  # page -> reason
for item in ingest_full.get("removed", []):
    removed_map[item["page"]] = item.get("reason", "removida")
for item in conv_full.get("removidos", []):
    removed_map[item["page"]] = item.get("reason", "removida")

# ── 2. Capítulos: comparar as duas rotas ────────────────────────────────────
ingest_p40 = load("p1-40", "ingest.json")

chapters_full = {ch["title"]: ch for ch in ingest_full["chapters"]}
chapters_p40  = {ch["title"]: ch for ch in ingest_p40["chapters"]}

# Capítulos extras na rota p1-40 (detectados como layout, não numerados no full)
conv_full_alerts = conv_full.get("alertas", [])
layout_titles = set()
for alert in conv_full_alerts:
    m = re.search(r'"(.+?)"', alert)
    if m:
        layout_titles.add(m.group(1))

only_in_full = {t: ch for t, ch in chapters_full.items() if t not in chapters_p40}
only_in_p40  = {t: ch for t, ch in chapters_p40.items()  if t not in chapters_full}

# Mapeia título → página percorrendo markers e headings no documento.md
def build_chapter_pages(hash_key):
    doc_path = os.path.join(BASE, HASHES[hash_key], "documento.md")
    markers = []   # (lineno, page)
    headings = []  # (lineno, title)
    with open(doc_path) as f:
        for lineno, line in enumerate(f, 1):
            line = line.rstrip()
            m = re.match(r"<!-- p\.(\d+) -->", line)
            if m:
                markers.append((lineno, int(m.group(1))))
            if line.startswith("# "):
                headings.append((lineno, line[2:]))
    result = {}
    for hline, title in headings:
        page = "?"
        for mline, mpage in markers:
            if mline < hline:
                page = mpage
            else:
                break
        result[title] = page
    return result


# ── Saída ────────────────────────────────────────────────────────────────────
print("=== 1. PÁGINAS AUSENTES / DUPLICADAS (faixas 1-379) ===")
if not gaps and not duplicates:
    print("  Faixas cobrem 1-379 sem lacunas nem sobreposições.")
else:
    for p in gaps:
        motivo = removed_map.get(p, "sem texto")
        print(f"  p.{p:3d} ausente — {motivo}")
    for p in duplicates:
        print(f"  p.{p:3d} duplicada entre faixas")

removed_outside_gaps = {p: r for p, r in removed_map.items() if p not in gaps}
if removed_outside_gaps:
    print("  Páginas removidas (dentro de faixas cobertas):")
    for p, r in sorted(removed_outside_gaps.items()):
        print(f"    p.{p:3d} → {r}")

print()
print("=== 2. CAPÍTULOS PRESENTES NUMA ROTA E AUSENTES NA OUTRA ===")

pages_full = build_chapter_pages("full")
pages_p40  = build_chapter_pages("p1-40")

if only_in_full:
    print("  Só no livro completo (full):")
    for title, ch in only_in_full.items():
        pg = pages_full.get(title, "?")
        print(f"    [{ch['index']:2d}] {title[:55]}  (p.{pg})")

if only_in_p40:
    print("  Só na rota p1-40:")
    for title, ch in only_in_p40.items():
        pg = pages_p40.get(title, "?")
        flag = " ← layout não numerado no full" if title in layout_titles else ""
        print(f"    {title[:55]}  (p.{pg}){flag}")

if not only_in_full and not only_in_p40:
    print("  Nenhuma diferença de capítulos.")
