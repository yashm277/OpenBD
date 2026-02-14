import os
import pandas as pd
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse

app = FastAPI()

MASTER_FILE = "master_db.csv"
DELETE_OUTPUT_FILE = "delete_list.csv"
UPLOAD_FOLDER = "uploads"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def process_dump(file_path):
    if os.path.exists(MASTER_FILE):
        master = pd.read_csv(MASTER_FILE)
    else:
        master = pd.DataFrame(columns=["email", "total_open", "dump_count", "status"])

    new_dump = pd.read_csv(file_path)

    # Normalize column names
    new_dump.columns = [col.strip().lower() for col in new_dump.columns]

    if "email" not in new_dump.columns or "opens" not in new_dump.columns:
        raise Exception("CSV must contain Email and Opens columns.")

    new_dump = new_dump[["email", "opens"]]
    new_dump.columns = ["email", "open"]

    new_dump["open"] = pd.to_numeric(new_dump["open"], errors="coerce").fillna(0)

    for _, row in new_dump.iterrows():
        email = row["email"]
        open_val = row["open"]

        if email in master["email"].values:
            master.loc[master["email"] == email, "dump_count"] += 1
            master.loc[master["email"] == email, "total_open"] += open_val
        else:
            master = pd.concat([
                master,
                pd.DataFrame([{
                    "email": email,
                    "total_open": open_val,
                    "dump_count": 1,
                    "status": "active"
                }])
            ])

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
async def upload_csv(file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)

    with open(file_path, "wb") as f:
        f.write(await file.read())

    # Check if this is a delete_list.csv upload (for soft-deleting records)
    if "delete_list" in file.filename.lower():
        deleted_count = apply_soft_delete(file_path)
        return {
            "message": "Soft delete applied successfully",
            "deleted_count": deleted_count,
            "download_url": "/download"
        }
    else:
        # Regular data dump
        deleted_count = process_dump(file_path)
        return {
            "message": "Processed successfully",
            "deleted_count": deleted_count,
            "download_url": "/download"
        }

@app.get("/download")
def download_file():
    return FileResponse(
        DELETE_OUTPUT_FILE,
        media_type='text/csv',
        filename="delete_list.csv"
    )