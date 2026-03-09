
import os
import pandas as pd
from typing import List
from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()

DELETE_OUTPUT_FILE = "delete_list.csv"
DUPLICATE_OUTPUT_FILE = "duplicate_emails.csv"
UPLOAD_FOLDER = "uploads"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
# Serve static frontend files from /static
if not os.path.exists("static"):
    os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Clear uploads folder utility
def clear_uploads_folder():
    try:
        for fname in os.listdir(UPLOAD_FOLDER):
            path = os.path.join(UPLOAD_FOLDER, fname)
            if os.path.isfile(path):
                os.remove(path)
    except Exception:
        pass

# Clear uploads on server shutdown
@app.on_event("shutdown")
def shutdown_event():
    clear_uploads_folder()

# Endpoint to clear uploads on demand (for frontend navigation)
@app.post("/clear-uploads")
def clear_uploads():
    clear_uploads_folder()
    return JSONResponse({"result": "uploads_cleared"})

def find_duplicate_emails(file_paths: List[str], output_file: str = "duplicate_emails.csv", duplicate_type: str = "email"):
    """
    Combine multiple CSVs, find duplicates by email/company/full name (case-insensitive, stripped),
    and output a CSV with all associated names, companies, emails, and count.
    """
    all_rows = []
    for fp in file_paths:
        try:
            df = pd.read_csv(fp)
        except Exception:
            continue
        df.columns = [str(col).strip().lower() for col in df.columns]
        # Clean up columns
        for col in ["email", "first_name", "last_name", "company"]:
            if col not in df.columns:
                df[col] = ""
        df["email"] = df["email"].astype(str).str.strip().str.lower()
        df["first_name"] = df["first_name"].astype(str).str.strip()
        df["last_name"] = df["last_name"].astype(str).str.strip()
        df["company"] = df["company"].astype(str).str.strip()
        df = df[df["email"] != ""]
        all_rows.append(df)
    if not all_rows:
        return 0
    combined = pd.concat(all_rows, ignore_index=True)

    if duplicate_type == "email":
        group_key = "email"
        out_cols = ["Full Name", "Company Name", "Count", "Emails"]
    elif duplicate_type == "company":
        group_key = "company"
        out_cols = ["Company Name", "Full Name(s)", "Count", "Emails"]
    elif duplicate_type == "fullname":
        group_key = "fullname"
        combined["fullname"] = (combined["first_name"] + " " + combined["last_name"]).str.strip()
        out_cols = ["Full Name", "Company Name(s)", "Count", "Emails"]
    else:
        group_key = "email"
        out_cols = ["Full Name", "Company Name", "Count", "Emails"]

    # Group and aggregate
    if group_key == "email":
        count_df = combined.groupby("email").size().reset_index(name="Count")
        dup_emails = count_df[count_df["Count"] > 1]["email"]
        if dup_emails.empty:
            out_df = pd.DataFrame(columns=out_cols)
        else:
            filtered = combined[combined["email"].isin(dup_emails)]
            grouped = filtered.groupby("email").agg({
                "first_name": lambda x: ", ".join(sorted(set(x))),
                "last_name": lambda x: ", ".join(sorted(set(x))),
                "company": lambda x: ", ".join(sorted(set(x))),
            }).reset_index()
            grouped["Full Name"] = (grouped["first_name"] + " " + grouped["last_name"]).str.strip()
            grouped["Company Name"] = grouped["company"]
            grouped["Emails"] = grouped["email"]
            grouped["Count"] = grouped["Emails"].apply(lambda x: len(filtered[filtered["email"] == x]["email"]))
            out_df = grouped[out_cols]
    elif group_key == "company":
        grouped = combined.groupby("company", as_index=False).agg({
            "first_name": lambda x: ", ".join(sorted(set(x))),
            "last_name": lambda x: ", ".join(sorted(set(x))),
            "email": lambda x: ", ".join(sorted(set(x))),
            "company": "first"
        })
        grouped["Full Name(s)"] = (grouped["first_name"] + " " + grouped["last_name"]).str.strip()
        grouped["Company Name"] = grouped["company"]
        grouped["Emails"] = grouped["email"]
        grouped["Count"] = grouped["Emails"].apply(lambda x: len(x.split(", ")))
        out_df = grouped[grouped["Count"] > 1][out_cols]
    elif group_key == "fullname":
        grouped = combined.groupby("fullname", as_index=False).agg({
            "company": lambda x: ", ".join(sorted(set(x))),
            "email": lambda x: ", ".join(sorted(set(x))),
            "fullname": "first"
        })
        grouped["Full Name"] = grouped["fullname"]
        grouped["Company Name(s)"] = grouped["company"]
        grouped["Emails"] = grouped["email"]
        grouped["Count"] = grouped["Emails"].apply(lambda x: len(x.split(", ")))
        out_df = grouped[grouped["Count"] > 1][out_cols]
    else:
        return 0

    # Always write to the project root, not uploads
    out_df.to_csv(os.path.join(os.getcwd(), output_file), index=False)
    return len(out_df)

# ...existing code...

# Duplicate Email Finder endpoint
from fastapi import Form
@app.post("/duplicate-email-finder")
async def duplicate_email_finder(
    files: List[UploadFile] = File(...),
    duplicate_type: str = Form("email")
):
    """
    Accept one or more CSV files, find duplicates by selected type, and generate a report.
    """
    allowed_ext = {'.csv', '.xlsx'}
    saved_paths = []
    for file in files:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in allowed_ext:
            return JSONResponse({"error": f"Invalid file type: {file.filename}. Only .csv and .xlsx are allowed."}, status_code=400)
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        with open(file_path, "wb") as f:
            f.write(await file.read())
        saved_paths.append(file_path)
    # Set output file and download URL based on duplicate_type
    if duplicate_type == "email":
        output_file = "duplicate_emails.csv"
        download_url = "/download-duplicates"
    elif duplicate_type == "company":
        output_file = "common_company.csv"
        download_url = "/download-company"
    elif duplicate_type == "fullname":
        output_file = "common_fullname.csv"
        download_url = "/download-fullname"
    else:
        output_file = "duplicate_emails.csv"
        download_url = "/download-duplicates"
    try:
        duplicate_count = find_duplicate_emails(saved_paths, output_file, duplicate_type)
    except Exception as e:
        return JSONResponse({"error": f"Processing failed: {str(e)}"}, status_code=400)
    if duplicate_count == 0:
        return JSONResponse({"message": "No duplicates found.", "download_url": None, "duplicate_count": 0})
    return JSONResponse({
        "message": "Processed successfully",
        "duplicate_count": duplicate_count,
        "download_url": download_url
    })


# Download endpoint for duplicate_emails.csv
@app.get("/download-duplicates")
def download_duplicates():
    file_path = os.path.join(os.getcwd(), "duplicate_emails.csv")
    if not os.path.exists(file_path):
        return JSONResponse({"error": "duplicate_emails.csv not found"}, status_code=404)
    return FileResponse(
        file_path,
        media_type="text/csv",
        filename="duplicate_emails.csv"
    )

# Download endpoint for common_company.csv
@app.get("/download-company")
def download_company():
    file_path = os.path.join(os.getcwd(), "common_company.csv")
    if not os.path.exists(file_path):
        return JSONResponse({"error": "common_company.csv not found"}, status_code=404)
    return FileResponse(
        file_path,
        media_type="text/csv",
        filename="common_company.csv"
    )

# Download endpoint for common_fullname.csv
@app.get("/download-fullname")
def download_fullname():
    file_path = os.path.join(os.getcwd(), "common_fullname.csv")
    if not os.path.exists(file_path):
        return JSONResponse({"error": "common_fullname.csv not found"}, status_code=404)
    return FileResponse(
        file_path,
        media_type="text/csv",
        filename="common_fullname.csv"
    )




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

    allowed_ext = {'.csv', '.xlsx'}
    saved_paths = []
    for file in files:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in allowed_ext:
            return JSONResponse({"error": f"Invalid file type: {file.filename}. Only .csv and .xlsx are allowed."}, status_code=400)
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



# Serve the dashboard as the main entry point
@app.get("/")
def dashboard():
    return FileResponse("static/dashboard.html", media_type="text/html")



@app.get("/app")
def app_page():
    # Serve the Delete List Generator page
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
OVERLAP_OUTPUT_FILE = "overlap_filtered.csv"

def process_overlap(csv1_path: str, csv2_path: str):
    """
    Remove emails in CSV2 from CSV1 and output remaining emails.
    """

    df1 = pd.read_csv(csv1_path)
    df2 = pd.read_csv(csv2_path)

    df1.columns = [c.strip().lower() for c in df1.columns]
    df2.columns = [c.strip().lower() for c in df2.columns]

    if "email" not in df1.columns or "email" not in df2.columns:
        raise ValueError("Both CSV files must contain an 'email' column")

    df1["email"] = df1["email"].astype(str).str.strip().str.lower()
    df2["email"] = df2["email"].astype(str).str.strip().str.lower()

    emails1 = set(df1["email"])
    emails2 = set(df2["email"])

    remaining_emails = emails1 - emails2

    result_df = pd.DataFrame({"email": list(remaining_emails)})
    result_df.to_csv(OVERLAP_OUTPUT_FILE, index=False)

    overlap_count = len(emails1 & emails2)

    return {
        "csv1_total": len(emails1),
        "csv2_total": len(emails2),
        "overlap_count": overlap_count,
        "remaining_count": len(remaining_emails)
    }
@app.post("/overlap-checker")
async def overlap_checker(
    file1: UploadFile = File(...),
    file2: UploadFile = File(...)
):

    allowed_ext = {".csv", ".xlsx"}

    ext1 = os.path.splitext(file1.filename)[1].lower()
    ext2 = os.path.splitext(file2.filename)[1].lower()

    if ext1 not in allowed_ext or ext2 not in allowed_ext:
        return JSONResponse(
            {"error": "Only CSV or XLSX files allowed"},
            status_code=400
        )

    path1 = os.path.join(UPLOAD_FOLDER, file1.filename)
    path2 = os.path.join(UPLOAD_FOLDER, file2.filename)

    with open(path1, "wb") as f:
        f.write(await file1.read())

    with open(path2, "wb") as f:
        f.write(await file2.read())

    try:
        stats = process_overlap(path1, path2)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)

    return {
        "message": "Overlap processed successfully",
        **stats,
        "download_url": "/download-overlap"
    }
@app.get("/download-overlap")
def download_overlap():
    if not os.path.exists(OVERLAP_OUTPUT_FILE):
        return JSONResponse({"error": "overlap_filtered.csv not found"}, status_code=404)

    return FileResponse(
        OVERLAP_OUTPUT_FILE,
        media_type="text/csv",
        filename="overlap_filtered.csv"
    )

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