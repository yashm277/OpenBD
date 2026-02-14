# RISE - CSV_counter

A FastAPI application for processing email data dumps and identifying emails to soft-delete based on engagement metrics.

## **Quick Start - How to Run**
### **1. Install Required Packages**
```powershell
pip install fastapi uvicorn pandas python-multipart
```
### **2. Start the Server**
```powershell
# RISE - CSV Counter (frontend-enabled)

This repo runs a FastAPI backend plus a small single-page frontend (served from `/static`) for uploading multiple CSV dumps, viewing a preview of the master DB and the generated delete list, and downloading results.

Quick summary for your manager: the app accepts multiple CSV files in one upload (or multiple uploads). Each file counts as one "dump" per email; an email appearing in three separate dumps with zero opens will be marked `soft_delete` and added to `delete_list.csv`.

---

## How to run (quick)

1. Install required packages:
```powershell
pip install -r requirements.txt
```
2. Start the server:
```powershell
uvicorn app:app --reload
```
3. Open the frontend in a browser:

- Frontend SPA: http://localhost:8000/  (upload files here, see progress and results)
- API docs (optional): http://localhost:8000/docs

---

## How your manager should test the new frontend

1. Open http://localhost:8000/ in the browser.
2. Use the upload area (or click the file picker) to select multiple CSVs at once. The UI supports many files (30+), but large files may take longer.
3. Click "Upload Files". A progress bar shows upload progress. When complete the server will process the files and update the page.
4. Observe:
   - "Delete List" card shows the emails currently marked `soft_delete`.
   - "Master Database Preview" shows the top rows of `master_db.csv` (email, total_open, dump_count, status).
5. To download files:
   - Click "Download Delete List" → downloads `delete_list.csv`
   - Click "Download Master DB" → downloads `master_db.csv`

Controls for mistakes / cleanup:
- "Clear Selection" — clears the file chooser before uploading.
- "Delete delete_list.csv" — removes the delete list on the server (useful if you want to re-run tests).
- "Reset Server" — deletes `master_db.csv`, `delete_list.csv`, and clears the `uploads/` folder (destructive; confirm before use).

Notes about how `dump_count` works:
- Each CSV file counts as one dump for any email it contains (duplicates inside the same file count as a single presence for that file).
- `dump_count` increases when an email appears in multiple different files or in multiple upload operations.
- To force an email into the delete list during testing, upload that email (with 0 opens) in three separate CSV files, or upload three separate files that each contain the email.

Example quick test (local):
1. Create three small CSVs named `dump1.csv`, `dump2.csv`, `dump3.csv` each with:
```
email,opens
test@example.com,0
```
2. Upload all three files at once via the frontend or upload them one after another.
3. After processing, `master_db.csv` should show `test@example.com` with `dump_count >= 3` and `total_open == 0`, and `delete_list.csv` should contain `test@example.com`.

---

## Where files are stored

- Uploaded files: `uploads/`
- Master DB: `master_db.csv`
- Delete list: `delete_list.csv`

If you need to remove these files manually (instead of using the UI):
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

- If uploads fail, ensure `python-multipart` is installed (included in `requirements.txt`).
- Restart the server after installing new packages.
- Check server logs in the terminal running `uvicorn` for errors.

---

If you want, I can add a tiny modal confirmation UI, an undo-last-upload feature, or convert this SPA into a React app for a richer experience. Tell me which and I'll implement it.
