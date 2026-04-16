# Resume Build Script Reference

## Overview

Resumes are built by:
1. Starting from the unpacked source XML (`unpacked_resume/word/document.xml`)
2. Applying text replacements and structural removals via Python
3. Packing with `scripts/office/pack.py` (docx skills)
4. Converting to PDF with `scripts/office/soffice.py`

Source location: `Resume/auto-apply/applications/` for customised versions  
Master: `Resume/[YourName]_Resume_[Year].docx`  
Unpacked source: `unpacked_resume/` (session-level, rebuilt each session from master)

---

## Core Helper Functions

```python
import subprocess, shutil, os, re

SKILLS_DIR = "/path/to/.claude/skills/docx"
SOFFICE    = f"{SKILLS_DIR}/scripts/office/soffice.py"

def remove_para(xml, text):
    """Remove the complete <w:p>...</w:p> containing text."""
    idx = xml.find(text)
    if idx == -1: return xml
    ps = xml.rfind('    <w:p>', 0, idx)
    pe = xml.find('    </w:p>', idx) + len('    </w:p>') + 1
    return xml[:ps] + xml[pe:]

def remove_block(xml, start_text, end_text):
    """Remove all paragraphs from start_text's <w:p> up to (not including) end_text's <w:p>."""
    si = xml.find(start_text)
    ei = xml.find(end_text)
    if si == -1 or ei == -1: return xml
    ps = xml.rfind('    <w:p>', 0, si)
    pe = xml.rfind('    <w:p>', 0, ei)
    return xml[:ps] + xml[pe:]

def validate_xml(xml):
    """Assert no Chinese, no bare &. Raise AssertionError if invalid."""
    assert not re.search(r'[\u4e00-\u9fff]', xml), "Chinese characters found!"
    bad = re.findall(r'&(?!amp;|lt;|gt;|apos;|quot;|#)', xml)
    assert not bad, f"Bare & found: {bad[:3]}"

def pack_and_pdf(xml, docx_path, src_unpack, original_docx, label):
    """Pack XML to .docx and convert to .pdf. Returns (ok, msg)."""
    wd = f"/tmp/work_{label}"
    if os.path.exists(wd): shutil.rmtree(wd)
    shutil.copytree(src_unpack, wd)
    open(f"{wd}/word/document.xml", 'w', encoding='utf-8').write(xml)
    r = subprocess.run(
        ["python", f"{SKILLS_DIR}/scripts/office/pack.py",
         wd, docx_path, "--original", original_docx],
        capture_output=True, text=True)
    shutil.rmtree(wd)
    if "Successfully packed" not in r.stdout:
        return False, r.stdout[-120:]
    r2 = subprocess.run(
        ["python", SOFFICE, "--headless", "--convert-to", "pdf",
         "--outdir", os.path.dirname(docx_path), docx_path],
        capture_output=True, text=True, timeout=60)
    pdf = docx_path.replace('.docx', '.pdf')
    return True, "pdf ok" if os.path.exists(pdf) else "pdf fail"
```

---

## Building the Compact Base XML

Apply these transformations to the source XML (in order). Adapt the string literals to match
the candidate's actual resume content — these are illustrative examples.

```python
def make_base_xml(source_xml):
    xml = source_xml

    # 1. Text replacements (summary, bullets, skills)
    xml = xml.replace(OLD_SUMMARY, NEW_SUMMARY)   # shorten or reframe the summary
    xml = xml.replace(OLD_BULLET_1, NEW_BULLET_1) # add/adjust current-role bullet
    xml = xml.replace(OLD_BULLET_2, NEW_BULLET_2) # add/adjust analytics/tool bullet
    xml = xml.replace(OLD_DEV_ROW,  NEW_DEV_ROW)  # update development skills row
    xml = xml.replace(OLD_MKT_ROW,  NEW_MKT_ROW)  # update marketing/SEO skills row
    xml = xml.replace(OLD_TOOL_ROW, NEW_TOOL_ROW) # update tools row

    # 2. Structural removals — remove roles or bullets not relevant to target job category
    # Example: remove a specific bullet that is too long or not relevant
    xml = remove_para(xml, 'Exact bullet text to remove')
    # Example: remove an entire job block (e.g. a short unrelated stint)
    xml = remove_block(xml, '<w:t>Job Title To Start Removing</w:t>',
                            '<w:t>Job Title To Stop Before</w:t>')

    validate_xml(xml)
    return xml
```

**How to identify the correct string literals:**

1. Unpack the master `.docx` with `scripts/office/unpack.py`
2. Open `word/document.xml` in any text editor
3. Search for the text you want to replace — copy the exact surrounding XML run text
4. Use that as your `OLD_*` constant

---

## Generating Per-Job Customised XML

```python
BASE_SUM  = "..."  # the compact base summary (2 sentences)
BASE_DEV  = "..."  # base development skills string (exact text from XML)
BASE_MKT  = "..."  # base SEO & marketing skills string
BASE_TOOL = "..."  # base tools string

def make_job_xml(base_xml, job_summary, job_dev, job_mkt, job_tool):
    xml = base_xml
    xml = xml.replace(BASE_SUM,  job_summary)
    xml = xml.replace(BASE_DEV,  job_dev)
    xml = xml.replace(BASE_MKT,  job_mkt)
    xml = xml.replace(BASE_TOOL, job_tool)
    validate_xml(xml)
    return xml
```

Call this once per job, passing in the per-JD customised strings for each section.

---

## XML Writing Rules

### Text content
- All `&` must be `&amp;` — including in summaries, company names, skill lists
- Em dash `—` = `\u2014`, En-dash in dates `–` = `\u2013`, bullet `•` = `\u2022`
- Middle dot separator `·` = `\u00b7`
- Arrow `→` = `\u2192`, multiplication `×` = `\u00d7`

### Paragraph XML template (for new bullets)
```python
def bullet_para(text):
    return (
        '    <w:p>\n      <w:pPr>\n        <w:spacing w:before="0" w:after="20"/>\n'
        '        <w:ind w:left="260" w:hanging="180"/>\n      </w:pPr>\n'
        '      <w:r>\n        <w:rPr>\n          <w:rFonts w:ascii="Arial" w:hAnsi="Arial"/>\n'
        '          <w:b w:val="0"/>\n          <w:i w:val="0"/>\n          <w:color w:val="555555"/>\n'
        '          <w:sz w:val="18"/>\n        </w:rPr>\n'
        '        <w:t xml:space="preserve">\u2022 </w:t>\n      </w:r>\n'
        '      <w:r>\n        <w:rPr>\n          <w:rFonts w:ascii="Arial" w:hAnsi="Arial"/>\n'
        '          <w:b w:val="0"/>\n          <w:i w:val="0"/>\n          <w:color w:val="0D0D0D"/>\n'
        '          <w:sz w:val="18"/>\n        </w:rPr>\n'
        f'        <w:t>{text}</w:t>\n      </w:r>\n    </w:p>\n')
```

### Section header template (for PROJECTS, EDUCATION, SKILLS headings)
```python
def section_header(title):
    return (
        '    <w:p>\n      <w:pPr>\n        <w:spacing w:before="100" w:after="20"/>\n'
        '        <w:pBdr>\n          <w:bottom w:val="single" w:sz="4" w:space="1" w:color="000000"/>\n'
        '        </w:pBdr>\n      </w:pPr>\n      <w:r>\n        <w:rPr>\n'
        '          <w:rFonts w:ascii="Arial" w:hAnsi="Arial"/>\n          <w:b/>\n'
        '          <w:i w:val="0"/>\n          <w:color w:val="000000"/>\n          <w:sz w:val="18"/>\n'
        f'        </w:rPr>\n        <w:t>{title}</w:t>\n      </w:r>\n    </w:p>\n')
```

---

## File Naming Convention

```
APP[NNN]_[CompanySlug]_[RoleSlug]_[YYYY-MM-DD].docx
APP[NNN]_[CompanySlug]_[RoleSlug]_[YYYY-MM-DD].pdf
```

Examples:
- `APP005_AcmeCorp_DigitalMarketingManager_2026-01-15.docx`
- `APP012_TechStartup_FrontEndDeveloper_2026-02-03.pdf`

The `NNN` counter should be sequential across all applications in the tracking document.

---

## Validation Checklist Before Delivering

- [ ] `validate_xml(xml)` passes (no Chinese, no bare &)
- [ ] Pack script reports "All validations PASSED"
- [ ] PDF file exists at expected path
- [ ] No visible overflow beyond 1 page (check via LibreOffice conversion)
- [ ] Paragraph count is balanced (`<w:p>` == `</w:p>`)
