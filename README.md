# RISE - CSV Counter

A FastAPI application for processing email data dumps and identifying emails to soft-delete based on engagement metrics.

## **Quick Start - How to Run**
### **1. Install Required Packages**
```powershell
pip install -r requirements.txt
```
### **2. Start the Server**
```powershell
uvicorn app:app --reload
```

**Quick Summary:** The app accepts multiple CSV files in one upload (or multiple uploads). Each file counts as one "dump" per email; an email appearing in three separate dumps with zero opens will be marked `soft_delete` and added to `delete_list.csv`.

---

## How to Run

1. Install required packages:
```powershell
pip install -r requirements.txt
```

2. Start the server:
```powershell
uvicorn app:app --reload
```

3. Open in your browser:
   - Homepage: http://localhost:8000/ (click "Open App" to launch)
   - Main App: http://localhost:8000/app
   - API docs (optional): http://localhost:8000/docs

---

## How to Use the App

1. Open http://localhost:8000/ and click the **"Open App"** button.
2. You'll see 3 sections:
   - **Upload CSV Files** — drag and drop or click to select multiple CSVs
   - **Process Data** — triggers processing of uploaded files
   - **Download Results** — download the delete list or master database

3. Workflow:
   - Upload one or more CSV files (with Email and Opens columns)
   - Click "Process" (processing also happens automatically on upload)
   - Download your results:
     - **Delete List** → `delete_list.csv` (emails marked for soft delete)
     - **Master Database** → `master_db.csv` (complete tracking data)

## How dump_count Works

- Each CSV file counts as one dump for any email it contains (duplicates inside a single file count as one presence).
- `dump_count` increases when an email appears in different files or across multiple uploads.
- Emails with `dump_count >= 3` AND `total_open == 0` are marked for soft delete.

## Quick Test Example

1. Create three CSV files, each containing:
```
email,opens
test@example.com,0
```

2. Upload all three files (or upload them separately).

3. After processing:
   - `master_db.csv` will show `test@example.com` with `dump_count = 3` and `total_open = 0`
   - `delete_list.csv` will contain `test@example.com`

---

## File Storage

- **Uploaded files:** `uploads/`
- **Master database:** `master_db.csv`
- **Delete list:** `delete_list.csv`

To reset manually:
```powershell
del master_db.csv
del delete_list.csv
rd /s /q uploads
mkdir uploads
```

---

## Branch & deployment

- This frontend-enabled change is on the branch: `csv_counter`.
- To get it locally:
```powershell
git fetch openbd
git checkout -b csv_counter openbd/csv_counter
```

---

## Troubleshooting

- **Uploads fail:** Ensure `python-multipart` is installed (`pip install -r requirements.txt`).
- **Changes not appearing:** Restart the server.
- **Check errors:** Look at the terminal running `uvicorn` for detailed error messages.
