
import difflib
import os
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

@router.post("/compare")
async def compare_files(body: dict):
    """Compare two config file paths OR direct text content."""
    f1_path = body.get("file1", "")
    f2_path = body.get("file2", "")
    t1_content = body.get("text1", "")
    t2_content = body.get("text2", "")
    
    label1 = f1_path or "Référence"
    label2 = f2_path or "Actuel"
    
    try:
        # Resolve lines for source 1
        if os.path.exists(f1_path) and os.path.isfile(f1_path):
            with open(f1_path, "r", encoding="utf-8") as a:
                lines1 = a.readlines()
        else:
            lines1 = [l + "\n" for l in t1_content.splitlines()]

        # Resolve lines for source 2
        if os.path.exists(f2_path) and os.path.isfile(f2_path):
            with open(f2_path, "r", encoding="utf-8") as b:
                lines2 = b.readlines()
        else:
            lines2 = [l + "\n" for l in t2_content.splitlines()]
            
        if not lines1 and not lines2 and not f1_path and not f2_path:
            return {"status": "error", "message": "Aucune source de données fournie."}
        
        html_diff = difflib.HtmlDiff(wrapcolumn=90)
        raw_table = html_diff.make_table(lines1, lines2, label1, label2, context=True, numlines=5)
        
        clean_html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Diff — {os.path.basename(label1)} vs {os.path.basename(label2)}</title>
<style>
  body {{ font-family:'Segoe UI',sans-serif; font-size:13px; background:#0f1117; color:#e0e0e0; margin:20px; }}
  h2 {{ color:#60a0ff; }}
  table.diff {{ border-collapse:collapse; width:100%; background:#1a1e2a; border:1px solid #2a3050; }}
  .diff th {{ background:#1e2436; border:1px solid #2a3050; padding:8px; color:#8899bb; font-weight:600; }}
  .diff td {{ padding:4px 8px; border:1px solid #1e2436; font-family:'Consolas',monospace; white-space:pre-wrap; }}
  .diff_add {{ background:#1a3a1a; color:#4dff4d; }}
  .diff_chg {{ background:#3a3a1a; color:#ffdd44; }}
  .diff_sub {{ background:#3a1a1a; color:#ff4d4d; }}
  .diff_header {{ background:#1a1e30; color:#667; width:30px; text-align:right; }}
</style></head>
<body><h2>Rapport de Comparaison</h2>
<p><b>Source 1:</b> {label1} &nbsp;|&nbsp; <b>Source 2:</b> {label2}</p>
{raw_table}</body></html>"""
        
        report_file = "diff_report.html"
        with open(report_file, "w", encoding="utf-8") as out:
            out.write(clean_html)
        
        text_diff = list(difflib.unified_diff(lines1, lines2, fromfile=label1, tofile=label2, lineterm=""))
        return {
            "status": "success",
            "diff_lines": text_diff,
            "html_file": report_file,
            "added": sum(1 for l in text_diff if l.startswith("+") and not l.startswith("+++")),
            "removed": sum(1 for l in text_diff if l.startswith("-") and not l.startswith("---")),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
