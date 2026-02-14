import os
import pandas as pd
from typing import List
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse, HTMLResponse

app = FastAPI()

MASTER_FILE = "master_db.csv"
DELETE_OUTPUT_FILE = "delete_list.csv"
UPLOAD_FOLDER = "uploads"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def process_multiple_dumps(file_paths: List[str]):
    """
    Process one or more dump CSV files. Each file counts as one "dump" per email
    (presence in a file increments dump_count by 1). Opens are summed across files.
    """
    if os.path.exists(MASTER_FILE):
        master = pd.read_csv(MASTER_FILE)
    else:
        master = pd.DataFrame(columns=["email", "total_open", "dump_count", "status"])

    # Accumulate new data across files: total_open and per-file presence (as dump_count)
    new_grouped = None

    for fp in file_paths:
        new_dump = pd.read_csv(fp)
        new_dump.columns = [col.strip().lower() for col in new_dump.columns]

        if "email" not in new_dump.columns or "opens" not in new_dump.columns:
            raise ValueError("CSV must contain Email and Opens columns.")

        new_dump = new_dump[["email", "opens"]]
        new_dump.columns = ["email", "open"]
        new_dump["open"] = pd.to_numeric(new_dump["open"], errors="coerce").fillna(0)

        # For each file, count presence once per email and sum opens
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
            # drop helper cols if present
            if "total_open_r" in new_grouped.columns:
                new_grouped = new_grouped.drop(columns=[c for c in ["total_open_r", "presence_r"] if c in new_grouped.columns])

    if new_grouped is None:
        # nothing uploaded
        return 0

    new_grouped = new_grouped.rename(columns={"total_open": "total_open_new", "presence": "dump_count_new"})

    # Merge with master
    if not master.empty:
        master = master.merge(
            new_grouped,
            on="email",
            how="outer",
            suffixes=("_old", "_new")
        )

        master["total_open"] = master.get("total_open_old", 0).fillna(0) + master.get("total_open_new", 0).fillna(0)
        master["dump_count"] = master.get("dump_count_old", 0).fillna(0) + master.get("dump_count_new", 0).fillna(0)

        master["status"] = master["status"].fillna("active")

        master = master[["email", "total_open", "dump_count", "status"]]
    else:
        master = new_grouped.rename(columns={"total_open_new": "total_open", "dump_count_new": "dump_count"})
        master["status"] = "active"

    # Ensure numeric types
    master["total_open"] = pd.to_numeric(master["total_open"], errors="coerce").fillna(0)
    master["dump_count"] = pd.to_numeric(master["dump_count"], errors="coerce").fillna(0)

    # Soft delete logic
    delete_condition = (master["dump_count"] >= 3) & (master["total_open"] == 0)
    master.loc[delete_condition, "status"] = "soft_delete"

    delete_list = master[master["status"] == "soft_delete"][["email"]]

    delete_list.to_csv(DELETE_OUTPUT_FILE, index=False)
    master.to_csv(MASTER_FILE, index=False)

    return len(delete_list)
def apply_soft_delete(file_path):
    """Apply soft_delete status to emails from uploaded delete_list.csv"""
    if not os.path.exists(MASTER_FILE):
        raise Exception("Master database not found. Upload data dumps first.")
    
    master = pd.read_csv(MASTER_FILE)
    delete_emails = pd.read_csv(file_path)
    
    # Normalize column names
    delete_emails.columns = [col.strip().lower() for col in delete_emails.columns]
    
    if "email" not in delete_emails.columns:
        raise Exception("Delete list must contain Email column.")
    
    delete_emails = delete_emails["email"].unique()
    
    # Mark emails as soft_delete
    master.loc[master["email"].isin(delete_emails), "status"] = "soft_delete"
    master.to_csv(MASTER_FILE, index=False)
    
    return len(delete_emails)

@app.post("/upload")
async def upload_csv(files: List[UploadFile] = File(...)):
    """
    Accept one or more CSV files. If a single file named `delete_list` is uploaded,
    it will be applied as a soft-delete list. Otherwise, all uploaded CSVs are
    treated as data dumps and processed together (each file counts as one dump).
    """
    saved_paths = []
    for file in files:
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        with open(file_path, "wb") as f:
            f.write(await file.read())
        saved_paths.append(file_path)

    # If single upload of delete_list.csv -> apply soft deletes
    if len(files) == 1 and "delete_list" in files[0].filename.lower():
        deleted_count = apply_soft_delete(saved_paths[0])
        return {
            "message": "Soft delete applied successfully",
            "deleted_count": deleted_count,
            "download_url": "/download"
        }

    # Otherwise treat as one or more data dumps
    deleted_count = process_multiple_dumps(saved_paths)
    return {
        "message": "Processed successfully",
        "deleted_count": deleted_count,
        "download_url": "/download"
    }


@app.get("/")
def homepage():
    html = """
    <html>
      <head>
        <title>Upload CSV Dumps</title>
      </head>
      <body>
        <h2>Upload one or more CSV files</h2>
        <form action="/upload" enctype="multipart/form-data" method="post">
          <input name="files" type="file" multiple />
          <button type="submit">Upload</button>
        </form>
        <p>Visit <a href="/docs">/docs</a> for the API UI.</p>
      </body>
    </html>
    """
    return HTMLResponse(content=html)

@app.get("/download")
def download_file():
    return FileResponse(
        DELETE_OUTPUT_FILE,
        media_type='text/csv',
        filename="delete_list.csv"
    )