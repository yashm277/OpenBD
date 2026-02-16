import os
import json
import tempfile
import pandas as pd
from typing import List
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from mangum import Mangum

app = FastAPI()

# For Vercel serverless, we use /tmp for file storage
TEMP_DIR = tempfile.gettempdir()
DELETE_OUTPUT_FILE = os.path.join(TEMP_DIR, "delete_list.csv")
UPLOAD_FOLDER = os.path.join(TEMP_DIR, "uploads")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Serve static files if directory exists (local development)
static_path = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")


def process_multiple_dumps(file_paths: List[str]):
    """
    Process one or more dump CSV files. Each file counts as one "dump" per email
    (presence in a file increments dump_count by 1). Opens are summed across files.
    Returns emails that appear in 3+ dumps with 0 total opens.
    """
    new_grouped = None

    for fp in file_paths:
        new_dump = pd.read_csv(fp)
        new_dump.columns = [col.strip().lower() for col in new_dump.columns]

        if "email" not in new_dump.columns or "opens" not in new_dump.columns:
            raise ValueError("CSV must contain Email and Opens columns.")

        new_dump = new_dump[["email", "opens"]]
        new_dump.columns = ["email", "open"]
        new_dump["open"] = pd.to_numeric(new_dump["open"], errors="coerce").fillna(0)

        per_file = new_dump.groupby("email", as_index=False).agg(
            total_open=("open", "sum")
        )
        per_file["presence"] = 1

        if new_grouped is None:
            new_grouped = per_file
        else:
            new_grouped = new_grouped.merge(per_file, on="email", how="outer", suffixes=("", "_r"))
            new_grouped["total_open"] = new_grouped["total_open"].fillna(0) + new_grouped.get("total_open_r", 0).fillna(0)
            new_grouped["presence"] = new_grouped["presence"].fillna(0) + new_grouped.get("presence_r", 0).fillna(0)
            if "total_open_r" in new_grouped.columns:
                new_grouped = new_grouped.drop(columns=[c for c in ["total_open_r", "presence_r"] if c in new_grouped.columns])

    if new_grouped is None:
        return 0

    new_grouped = new_grouped.rename(columns={"total_open": "total_open", "presence": "dump_count"})
    new_grouped["total_open"] = pd.to_numeric(new_grouped["total_open"], errors="coerce").fillna(0)
    new_grouped["dump_count"] = pd.to_numeric(new_grouped["dump_count"], errors="coerce").fillna(0)

    delete_condition = (new_grouped["dump_count"] >= 3) & (new_grouped["total_open"] == 0)
    delete_list = new_grouped[delete_condition][["email"]]

    delete_list.to_csv(DELETE_OUTPUT_FILE, index=False)

    return len(delete_list)


@app.post("/api/upload")
async def upload_csv(files: List[UploadFile] = File(...)):
    """
    Accept one or more CSV files, process them as data dumps and generate delete list.
    """
    saved_paths = []
    for file in files:
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        with open(file_path, "wb") as f:
            f.write(await file.read())
        saved_paths.append(file_path)

    deleted_count = process_multiple_dumps(saved_paths)
    return {
        "message": "Processed successfully",
        "deleted_count": deleted_count,
        "download_url": "/api/download"
    }


# Keep old endpoint for backwards compatibility
@app.post("/upload")
async def upload_csv_legacy(files: List[UploadFile] = File(...)):
    return await upload_csv(files)


@app.get("/")
def homepage():
    """Serve the main dashboard"""
    return HTMLResponse(content=DASHBOARD_HTML, status_code=200)


@app.get("/tools/delete-list")
def delete_list_tool():
    """Serve the Delete List Generator tool"""
    return HTMLResponse(content=DELETE_LIST_TOOL_HTML, status_code=200)


# Legacy routes for backwards compatibility
@app.get("/app")
def app_page():
    return HTMLResponse(content=DELETE_LIST_TOOL_HTML, status_code=200)


@app.get("/api/status")
def status_preview(limit: int = 100):
    """Return a preview of delete_list.csv and uploaded files as JSON."""
    delete_list = []
    
    if os.path.exists(DELETE_OUTPUT_FILE):
        try:
            dl = pd.read_csv(DELETE_OUTPUT_FILE)
            delete_list = dl["email"].astype(str).tolist()
        except Exception:
            delete_list = []

    uploaded_files = []
    try:
        uploaded_files = [f for f in os.listdir(UPLOAD_FOLDER) if os.path.isfile(os.path.join(UPLOAD_FOLDER, f))]
    except Exception:
        uploaded_files = []

    return JSONResponse({
        "delete_list": delete_list,
        "delete_count": len(delete_list),
        "uploaded_files": uploaded_files
    })


@app.get("/status")
def status_preview_legacy(limit: int = 100):
    return status_preview(limit)


@app.post("/api/reset")
def reset_server():
    """Delete delete_list file and clear uploads folder."""
    results = {"delete_list_deleted": False, "uploads_cleared": False}
    try:
        if os.path.exists(DELETE_OUTPUT_FILE):
            os.remove(DELETE_OUTPUT_FILE)
            results["delete_list_deleted"] = True
    except Exception:
        pass
    try:
        for fname in os.listdir(UPLOAD_FOLDER):
            path = os.path.join(UPLOAD_FOLDER, fname)
            if os.path.isfile(path):
                os.remove(path)
        results["uploads_cleared"] = True
    except Exception:
        pass

    return JSONResponse({"result": results})


@app.post("/reset")
def reset_server_legacy():
    return reset_server()


@app.post("/api/delete/delete_list")
def delete_delete_list():
    """Delete the delete_list.csv file."""
    if os.path.exists(DELETE_OUTPUT_FILE):
        os.remove(DELETE_OUTPUT_FILE)
        return JSONResponse({"deleted": True})
    return JSONResponse({"deleted": False, "error": "delete_list.csv not found"}, status_code=404)


@app.post("/delete/delete_list")
def delete_delete_list_legacy():
    return delete_delete_list()


@app.get("/api/download")
def download_file():
    """Download the delete_list.csv file."""
    if not os.path.exists(DELETE_OUTPUT_FILE):
        return JSONResponse(
            {"error": "delete_list.csv not found"},
            status_code=404
        )

    return FileResponse(
        DELETE_OUTPUT_FILE,
        media_type="text/csv",
        filename="delete_list.csv"
    )


@app.get("/download")
def download_file_legacy():
    return download_file()


# ============================================================================
# EMBEDDED HTML TEMPLATES
# ============================================================================

DASHBOARD_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OpenBD - Dashboard</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #6366f1;
            --primary-dark: #4f46e5;
            --primary-light: #a5b4fc;
            --bg: #0f172a;
            --bg-card: #1e293b;
            --bg-card-hover: #334155;
            --border: #334155;
            --text: #f1f5f9;
            --text-secondary: #94a3b8;
            --success: #22c55e;
            --accent: #14b8a6;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
            line-height: 1.6;
            -webkit-font-smoothing: antialiased;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 48px 24px;
        }
        
        header {
            text-align: center;
            margin-bottom: 64px;
        }
        
        .logo {
            font-size: 3rem;
            font-weight: 800;
            background: linear-gradient(135deg, var(--primary) 0%, var(--accent) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 12px;
        }
        
        .tagline {
            color: var(--text-secondary);
            font-size: 1.125rem;
            max-width: 600px;
            margin: 0 auto;
        }
        
        .section-title {
            font-size: 1.25rem;
            font-weight: 600;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 24px;
        }
        
        .tools-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 24px;
            margin-bottom: 64px;
        }
        
        .tool-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 32px;
            text-decoration: none;
            color: inherit;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }
        
        .tool-card:hover {
            background: var(--bg-card-hover);
            transform: translateY(-4px);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
        }
        
        .tool-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, var(--primary) 0%, var(--accent) 100%);
            opacity: 0;
            transition: opacity 0.3s ease;
        }
        
        .tool-card:hover::before {
            opacity: 1;
        }
        
        .tool-icon {
            width: 56px;
            height: 56px;
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.75rem;
            margin-bottom: 20px;
        }
        
        .tool-title {
            font-size: 1.25rem;
            font-weight: 700;
            margin-bottom: 8px;
        }
        
        .tool-description {
            color: var(--text-secondary);
            font-size: 0.95rem;
            line-height: 1.6;
        }
        
        .tool-status {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            margin-top: 16px;
            padding: 6px 12px;
            background: rgba(34, 197, 94, 0.15);
            color: var(--success);
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 500;
        }
        
        .tool-status.coming-soon {
            background: rgba(99, 102, 241, 0.15);
            color: var(--primary-light);
        }
        
        .coming-soon-card {
            opacity: 0.6;
            cursor: default;
        }
        
        .coming-soon-card:hover {
            transform: none;
            background: var(--bg-card);
            box-shadow: none;
        }
        
        .add-tool-card {
            background: transparent;
            border: 2px dashed var(--border);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 200px;
            cursor: pointer;
        }
        
        .add-tool-card:hover {
            border-color: var(--primary);
            background: rgba(99, 102, 241, 0.05);
        }
        
        .add-icon {
            font-size: 2.5rem;
            color: var(--text-secondary);
            margin-bottom: 12px;
        }
        
        .add-text {
            color: var(--text-secondary);
            font-weight: 500;
        }
        
        footer {
            text-align: center;
            padding: 24px;
            color: var(--text-secondary);
            font-size: 0.875rem;
            border-top: 1px solid var(--border);
            margin-top: 48px;
        }
        
        @media (max-width: 768px) {
            .container {
                padding: 32px 16px;
            }
            
            .logo {
                font-size: 2.25rem;
            }
            
            .tools-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1 class="logo">OpenBD</h1>
            <p class="tagline">Your central hub for data management tools. All your utilities in one place.</p>
        </header>
        
        <section>
            <h2 class="section-title">Available Tools</h2>
            <div class="tools-grid">
                <a href="/tools/delete-list" class="tool-card">
                    <div class="tool-icon">📧</div>
                    <h3 class="tool-title">Delete List Generator</h3>
                    <p class="tool-description">Process email data dumps and identify emails to delete based on engagement metrics. Finds emails with 3+ appearances and 0 opens.</p>
                    <span class="tool-status">
                        <span>●</span> Active
                    </span>
                </a>
                
                <div class="tool-card coming-soon-card">
                    <div class="tool-icon">📊</div>
                    <h3 class="tool-title">Data Analyzer</h3>
                    <p class="tool-description">Analyze large datasets with visual insights, statistics, and exportable reports.</p>
                    <span class="tool-status coming-soon">
                        Coming Soon
                    </span>
                </div>
                
                <div class="tool-card coming-soon-card">
                    <div class="tool-icon">🔄</div>
                    <h3 class="tool-title">CSV Transformer</h3>
                    <p class="tool-description">Transform, merge, and clean CSV files with powerful batch operations.</p>
                    <span class="tool-status coming-soon">
                        Coming Soon
                    </span>
                </div>
                
                <div class="tool-card add-tool-card" onclick="alert('Add your next tool by pushing code to this repository!')">
                    <span class="add-icon">+</span>
                    <span class="add-text">Add New Tool</span>
                </div>
            </div>
        </section>
    </div>
    
    <footer>
        <p>OpenBD Dashboard &copy; 2026 &mdash; Push new features to expand your toolkit</p>
    </footer>
</body>
</html>'''

DELETE_LIST_TOOL_HTML = '''<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=5,user-scalable=yes" />
    <meta http-equiv="X-UA-Compatible" content="IE=edge" />
    <title>Delete List Generator - OpenBD</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
      :root {
        --primary: #6366f1;
        --primary-dark: #4f46e5;
        --primary-light: #a5b4fc;
        --secondary: #14b8a6;
        --bg: #0f172a;
        --bg-card: #1e293b;
        --border: #334155;
        --text: #f1f5f9;
        --text-secondary: #94a3b8;
        --success: #22c55e;
        --warning: #f59e0b;
        --error: #ef4444;
      }
      
      * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
      }
      
      body { 
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        background: var(--bg);
        color: var(--text);
        min-height: 100vh;
        padding: 0;
        line-height: 1.6;
        -webkit-font-smoothing: antialiased;
      }
      
      .nav {
        background: var(--bg-card);
        border-bottom: 1px solid var(--border);
        padding: 16px 24px;
        display: flex;
        align-items: center;
        gap: 16px;
      }
      
      .back-link {
        color: var(--text-secondary);
        text-decoration: none;
        font-size: 0.9rem;
        display: flex;
        align-items: center;
        gap: 6px;
        transition: color 0.2s;
      }
      
      .back-link:hover {
        color: var(--text);
      }
      
      .nav-title {
        font-weight: 600;
        color: var(--text);
      }
      
      .container {
        max-width: 800px;
        margin: 0 auto;
        padding: 40px 24px;
      }
      
      h1 { 
        font-size: 2.25rem;
        font-weight: 800;
        color: var(--text);
        margin-bottom: 8px;
      }
      
      .subtitle {
        color: var(--text-secondary);
        font-size: 1.125rem;
        margin-bottom: 40px;
      }
      
      .card { 
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 32px;
        margin-bottom: 24px;
      }
      
      h2 {
        font-size: 1.25rem;
        margin-bottom: 20px;
        color: var(--text);
        font-weight: 700;
      }
      
      .upload-zone {
        border: 2px dashed var(--border);
        border-radius: 12px;
        padding: 48px 24px;
        text-align: center;
        background: rgba(99, 102, 241, 0.05);
        cursor: pointer;
        position: relative;
        margin-bottom: 24px;
        min-height: 180px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        transition: all 0.2s ease;
      }
      
      .upload-zone:hover {
        border-color: var(--primary);
        background: rgba(99, 102, 241, 0.1);
      }
      
      .upload-icon {
        font-size: 3rem;
        margin-bottom: 16px;
        display: block;
      }
      
      .upload-text {
        font-size: 1rem;
        font-weight: 600;
        color: var(--text);
        margin-bottom: 8px;
      }
      
      .file-info {
        color: var(--text-secondary);
        font-size: 0.9rem;
      }
      
      input[type=file] { 
        opacity: 0;
        position: absolute;
        width: 100%;
        height: 100%;
        top: 0;
        left: 0;
        cursor: pointer;
      }
      
      .button-group {
        display: flex;
        gap: 12px;
        flex-wrap: wrap;
        margin-top: 24px;
      }
      
      button, .btn { 
        padding: 14px 28px;
        cursor: pointer;
        background: var(--primary);
        color: white;
        border: none;
        border-radius: 8px;
        font-family: inherit;
        font-size: 0.95rem;
        font-weight: 600;
        transition: all 0.2s ease;
        text-decoration: none;
        display: inline-flex;
        align-items: center;
        gap: 8px;
      }
      
      button:hover, .btn:hover {
        background: var(--primary-dark);
        transform: translateY(-2px);
      }
      
      #progress { 
        width: 100%;
        height: 8px;
        background: var(--border);
        border-radius: 8px;
        overflow: hidden;
        margin-top: 16px;
        display: none;
      }
      
      #progress > div { 
        height: 100%;
        width: 0;
        background: linear-gradient(90deg, var(--primary) 0%, var(--secondary) 100%);
        transition: width 0.3s ease;
        border-radius: 8px;
      }
      
      #statusText {
        margin-top: 16px;
        color: var(--text-secondary);
        font-weight: 600;
        font-size: 0.95rem;
        text-align: center;
        display: none;
      }
      
      #statusText.show { display: block; }
      #statusText.success { color: var(--success); }
      #statusText.warning { color: var(--warning); }
      #statusText.error { color: var(--error); }
      
      .file-selected {
        background: rgba(34, 197, 94, 0.15);
        padding: 12px 16px;
        border-radius: 8px;
        margin-top: 16px;
        color: var(--success);
        font-weight: 600;
        display: inline-block;
      }

      .info-box {
        background: rgba(20, 184, 166, 0.1);
        border-left: 4px solid var(--secondary);
        padding: 16px;
        border-radius: 8px;
        margin-bottom: 24px;
      }

      .info-box p {
        margin: 0;
        color: var(--text-secondary);
        font-size: 0.9rem;
        line-height: 1.6;
      }
      
      .info-box strong {
        color: var(--text);
      }
      
      @media (max-width: 768px) {
        h1 { font-size: 1.75rem; }
        .card { padding: 24px; }
        .button-group { flex-direction: column; }
        button, .btn { width: 100%; justify-content: center; }
      }
    </style>
  </head>
  <body>
    <nav class="nav">
      <a href="/" class="back-link">← Dashboard</a>
      <span class="nav-title">Delete List Generator</span>
    </nav>
    
    <div class="container">
      <h1>Delete List Generator</h1>
      <p class="subtitle">Upload data dumps to identify emails for deletion</p>
      
      <div class="card">
        <h2>How It Works</h2>
        <div class="info-box">
          <p>Upload your CSV data dumps (must contain "Email" and "Opens" columns). The tool will identify emails that appear in <strong>3 or more dumps with 0 total opens</strong> and generate a delete list.</p>
        </div>
      </div>

      <div class="card">
        <h2>Upload CSV Files</h2>
        <div class="upload-zone" id="uploadZone">
          <span class="upload-icon">📂</span>
          <input id="files" type="file" multiple accept=".csv" />
          <div class="upload-text">Drag and drop CSV files here</div>
          <div class="file-info">or click to browse your computer</div>
          <div id="fileNames"></div>
        </div>
        
        <div class="button-group">
          <button id="uploadBtn">📤 Upload & Process</button>
        </div>
        
        <div id="progress"><div></div></div>
        <div id="statusText"></div>
      </div>

      <div class="card">
        <h2>Download Delete List</h2>
        <p style="color: var(--text-secondary); margin-bottom: 24px;">Download the list of emails to delete</p>
        <div class="button-group">
          <a href="/api/download" download style="text-decoration: none;">
            <button class="btn">📥 Download Delete List</button>
          </a>
        </div>
      </div>
    </div>

    <script>
      const filesInput = document.getElementById('files')
      const uploadBtn = document.getElementById('uploadBtn')
      const progressBar = document.querySelector('#progress > div')
      const progress = document.getElementById('progress')
      const statusText = document.getElementById('statusText')
      const uploadZone = document.getElementById('uploadZone')
      const fileNamesEl = document.getElementById('fileNames')

      filesInput.onchange = () => {
        const files = filesInput.files
        if (files.length > 0) {
          const names = Array.from(files).map(f => f.name).join(', ')
          fileNamesEl.innerHTML = `<div class="file-selected">✓ ${files.length} file(s) selected: ${names}</div>`
        } else {
          fileNamesEl.innerHTML = ''
        }
      }

      uploadZone.ondragover = (e) => {
        e.preventDefault()
        uploadZone.style.borderColor = 'var(--primary)'
      }
      
      uploadZone.ondragleave = () => {
        uploadZone.style.borderColor = 'var(--border)'
      }
      
      uploadZone.ondrop = (e) => {
        e.preventDefault()
        uploadZone.style.borderColor = 'var(--border)'
        filesInput.files = e.dataTransfer.files
        filesInput.onchange()
      }

      uploadBtn.onclick = () => {
        const files = filesInput.files
        if (!files || files.length === 0) {
          showStatus('Please select at least one CSV file', 'warning')
          return
        }

        const form = new FormData()
        for (let i=0; i<files.length; i++) form.append('files', files[i])

        progress.style.display = 'block'
        statusText.classList.add('show')
        
        const xhr = new XMLHttpRequest()
        xhr.open('POST', '/api/upload')
        xhr.upload.onprogress = (e) => {
          if (e.lengthComputable) {
            const pct = Math.round((e.loaded / e.total) * 100)
            progressBar.style.width = pct + '%'
            statusText.className = 'show'
            statusText.innerText = `Uploading... ${pct}%` 
          }
        }
        xhr.onload = () => {
          progressBar.style.width = '100%'
          if (xhr.status === 200) {
            const response = JSON.parse(xhr.responseText)
            showStatus(`✓ Processing complete! ${response.deleted_count} emails flagged for deletion`, 'success')
          } else {
            showStatus('✗ Processing failed', 'error')
          }
          
          setTimeout(() => {
            progress.style.display = 'none'
            progressBar.style.width = '0'
          }, 2000)
        }
        xhr.onerror = () => { 
          showStatus('✗ Upload failed', 'error')
        }
        xhr.send(form)
      }

      function showStatus(message, className) {
        statusText.className = 'show ' + className
        statusText.innerText = message
      }
    </script>
  </body>
</html>'''


# Handler for Vercel serverless
handler = Mangum(app)
