
import difflib

class DiffManager:
    def compare_files(self, file1_path, file2_path):
        try:
            with open(file1_path, 'r', encoding='utf-8') as f1:
                lines1 = f1.readlines()
            with open(file2_path, 'r', encoding='utf-8') as f2:
                lines2 = f2.readlines()
            
            html_diff = difflib.HtmlDiff(wrapcolumn=90)
            raw_html_table = html_diff.make_table(lines1, lines2, file1_path, file2_path, context=True, numlines=5)
            
            # Inject a cleaner CSS template instead of difflib's ugly default
            clean_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Comparaison de configuration</title>
                <style type="text/css">
                    body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; font-size: 13px; background-color: #f8f9fa; margin: 20px; }}
                    table.diff {{ border-collapse: collapse; width: 100%; border: 1px solid #dee2e6; background-color: white; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
                    .diff th {{ background-color: #e9ecef; border: 1px solid #dee2e6; padding: 8px; text-align: left; font-weight: 600; color: #495057; }}
                    .diff td {{ padding: 4px 8px; border: 1px solid #dee2e6; font-family: 'Consolas', monospace; white-space: pre-wrap; }}
                    .diff_add {{ background-color: #d4edda; color: #155724; }}
                    .diff_chg {{ background-color: #fff3cd; color: #856404; }}
                    .diff_sub {{ background-color: #f8d7da; color: #721c24; }}
                    .diff_header {{ background-color: #e9ecef; color: #adb5bd; width: 30px; text-align: right; }}
                </style>
            </head>
            <body>
                <h2 style="color: #343a40;">Rapport de Comparaison (Diff)</h2>
                {raw_html_table}
            </body>
            </html>
            """
            
            # Simple line-by-line diff for text display
            diff = list(difflib.unified_diff(lines1, lines2, fromfile=file1_path, tofile=file2_path, lineterm=''))
            
            return {'status': 'success', 'html': clean_html, 'text': diff}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
