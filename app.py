import os
import pandas as pd
from typing import List
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()

DELETE_OUTPUT_FILE = "delete_list.csv"
UPLOAD_FOLDER = "uploads"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
# Serve static frontend files from /static
if not os.path.exists("static"):
    os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

def process_multiple_dumps(file_paths: List[str]):
    """
    Process one or more dump CSV files. Each file counts as one "dump" per email
    (presence in a file increments dump_count by 1). Opens are summed across files.
    Returns emails that appear in 3+ dumps with 0 total opens.
    """
    # Accumulate data across files: total_open and per-file presence (as dump_count)
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

    new_grouped = new_grouped.rename(columns={"total_open": "total_open", "presence": "dump_count"})

    # Ensure numeric types
    new_grouped["total_open"] = pd.to_numeric(new_grouped["total_open"], errors="coerce").fillna(0)
    new_grouped["dump_count"] = pd.to_numeric(new_grouped["dump_count"], errors="coerce").fillna(0)

    # Identify emails to delete: appeared in 3+ dumps with 0 opens
    delete_condition = (new_grouped["dump_count"] >= 3) & (new_grouped["total_open"] == 0)
    delete_list = new_grouped[delete_condition][["email"]]

    delete_list.to_csv(DELETE_OUTPUT_FILE, index=False)

    return len(delete_list)


@app.post("/upload")
async def upload_csv(files: List[UploadFile] = File(...)):
    """
    Accept one or more CSV files, process them as data dumps and generate delete list.
    Each file counts as one dump. Emails appearing in 3+ dumps with 0 opens are flagged for deletion.
    """
    saved_paths = []
    for file in files:
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        with open(file_path, "wb") as f:
            f.write(await file.read())
        saved_paths.append(file_path)

    # Process all uploaded files
    deleted_count = process_multiple_dumps(saved_paths)
    return {
        "message": "Processed successfully",
        "deleted_count": deleted_count,
        "download_url": "/download"
    }


@app.get("/")
def homepage():
    # Serve the homepage
    return FileResponse("static/homepage.html", media_type="text/html")


@app.get("/app")
def app_page():
    # Serve the main app page
    return FileResponse("static/app.html", media_type="text/html")


@app.get("/status")
def status_preview(limit: int = 100):
    """Return a preview of delete_list.csv and uploaded files as JSON."""
    delete_list = []
    
    if os.path.exists(DELETE_OUTPUT_FILE):
        try:
            dl = pd.read_csv(DELETE_OUTPUT_FILE)
            delete_list = dl["email"].astype(str).tolist()
        except Exception:
            delete_list = []

    # list uploaded files
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


@app.post('/reset')
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
        # remove files in uploads folder
        for fname in os.listdir(UPLOAD_FOLDER):
            path = os.path.join(UPLOAD_FOLDER, fname)
            if os.path.isfile(path):
                os.remove(path)
        results["uploads_cleared"] = True
    except Exception:
        pass

    return JSONResponse({"result": results})


@app.post('/delete/delete_list')
def delete_delete_list():
    """Delete the delete_list.csv file."""
    if os.path.exists(DELETE_OUTPUT_FILE):
        os.remove(DELETE_OUTPUT_FILE)
        return JSONResponse({"deleted": True})
    return JSONResponse({"deleted": False, "error": "delete_list.csv not found"}, status_code=404)


@app.get("/download")
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