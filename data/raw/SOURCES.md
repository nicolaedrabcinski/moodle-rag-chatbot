# Course Materials Sources

Course materials in `data/raw/` are not tracked by git (too large, third-party content).
To re-download and re-ingest, use the links and commands below.

---

## ECD-2026 — Etica, Comunicare si Drept

Materials from the real ELSE FCIM UTM platform (requires login):
- `else.fcim.utm.md/course/view.php?id=3` (ECD-2026 course)

Already present in this repo: materials were uploaded to the local Moodle instance.

---

## FILOS-2026 — Filosofie

Materials from the real ELSE FCIM UTM platform (requires login):
- `else.fcim.utm.md/course/view.php?id=2` (FILOS-2026 course)

---

## ASD-2026 — Algoritmi si Structuri de Date

Open-access academic materials:

| File | Source |
|---|---|
| `01_structuri_date_algoritmi.pdf` | Adrian Carabineanu — *Structuri de Date* (113 pgs) — http://www.lbi.ro/~oana/11%20F/CARA_STRUCTURI.pdf |
| `02_curs_SDA_UBB.pdf` | UBB Cluj-Napoca, Lect. dr. Trîmbițaș M.-G. (40 pgs) — https://www.cs.ubbcluj.ro/~gabitr/curs1_2.pdf |
| `03_introducere_ASD.pdf` | UVT Timișoara, prof. Daniela Zaharie (18 pgs) — https://staff.fmi.uvt.ro/~daniela.zaharie/alg/ASD_introducere.pdf |
| `04_arbori_ASE.pdf` | ASE București, Curs Popa — Arbori (19 pgs) — https://www.acs.ase.ro/Media/Default/documents/structuri/CursPopa/2025/06_Arbori.pdf |

```bash
mkdir -p data/raw/ASD-2026
curl -L -o data/raw/ASD-2026/01_structuri_date_algoritmi.pdf \
  "http://www.lbi.ro/~oana/11%20F/CARA_STRUCTURI.pdf"
curl -L -o data/raw/ASD-2026/02_curs_SDA_UBB.pdf \
  "https://www.cs.ubbcluj.ro/~gabitr/curs1_2.pdf"
curl -L -o data/raw/ASD-2026/03_introducere_ASD.pdf \
  "https://staff.fmi.uvt.ro/~daniela.zaharie/alg/ASD_introducere.pdf"
curl -L -o data/raw/ASD-2026/04_arbori_ASE.pdf \
  "https://www.acs.ase.ro/Media/Default/documents/structuri/CursPopa/2025/06_Arbori.pdf"
python scripts/ingestion/add_course.py --course-id ASD-2026
```

---

## BD-2026 — Baze de Date

Open-access materials from ELSE FCIM UTM (public pluginfile links) + Univ. Al.I.Cuza Iași:

| File | Source |
|---|---|
| `01_BD_si_SGBD.docx` | ELSE UTM — https://else.fcim.utm.md/pluginfile.php/147283/mod_folder/content/0/BD__LIT_1_RO_BD%20SI%20SGBD.docx |
| `02_BD_curs_complet.docx` | ELSE UTM — https://else.fcim.utm.md/pluginfile.php/35315/mod_folder/content/0/BD__LIT_2_RO_BD__CURS.doc (converted .doc→.docx) |
| `03_normalizare.docx` | ELSE UTM — https://else.fcim.utm.md/pluginfile.php/147283/mod_folder/content/0/BD__Normalizarea.doc |
| `04_baze_relationale.docx` | ELSE UTM — https://else.fcim.utm.md/pluginfile.php/147283/mod_folder/content/0/BD__relationale.docx |
| `05_bazele_design.pdf` | ELSE UTM — https://else.fcim.utm.md/pluginfile.php/147305/mod_folder/content/0/0__BAZELE%20DESIGN_LUI.pdf |
| `06_introducere_BD.pptx` | Univ. Iași, M. Fotache — github.com/marinfotache/Baze-de-date-I |
| `07_model_relational.pptx` | Univ. Iași, M. Fotache — github.com/marinfotache/Baze-de-date-I |
| `08_proiectare_BD.pptx` | Univ. Iași, M. Fotache — github.com/marinfotache/Baze-de-date-I |

```bash
mkdir -p data/raw/BD-2026
# Download from ELSE UTM (public links):
curl -L -o data/raw/BD-2026/01_BD_si_SGBD.docx \
  "https://else.fcim.utm.md/pluginfile.php/147283/mod_folder/content/0/BD__LIT_1_RO_BD%20SI%20SGBD.docx?forcedownload=1"
curl -L -o data/raw/BD-2026/02_BD_curs_complet.doc \
  "https://else.fcim.utm.md/pluginfile.php/35315/mod_folder/content/0/BD__LIT_2_RO_BD__CURS.doc?forcedownload=1"
libreoffice --headless --convert-to docx data/raw/BD-2026/02_BD_curs_complet.doc --outdir data/raw/BD-2026/
python scripts/ingestion/add_course.py --course-id BD-2026
```

---

## IA-2026 — Inteligenta Artificiala

Open-access materials from FMI Unibuc (GitHub Pages):
- Repository: https://fmi-unibuc-ia.github.io/ia/

| File | Source |
|---|---|
| `curs1_IA.pptx` … `curs6_IA.pptx` | https://fmi-unibuc-ia.github.io/ia/Cursuri/CursN.pptx |
| `lab1_IA.pdf` … `lab7_IA.pdf` | https://fmi-unibuc-ia.github.io/ia/Laboratoare/LaboratorulN.pdf |

```bash
mkdir -p data/raw/IA-2026
base="https://fmi-unibuc-ia.github.io/ia"
for i in 1 2 3 4 5 6; do
  curl -L -o "data/raw/IA-2026/curs${i}_IA.pptx" "${base}/Cursuri/Curs${i}.pptx"
done
for i in 1 2 3 4 5 6 7; do
  curl -L -o "data/raw/IA-2026/lab${i}_IA.pdf" "${base}/Laboratoare/Laboratorul%20${i}.pdf"
done
python scripts/ingestion/add_course.py --course-id IA-2026
```
