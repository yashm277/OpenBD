# RISE - Delete List Generator

A FastAPI application for processing email data dumps and identifying emails to delete based on engagement metrics.

## **Quick Start - How to Run**
### **1. Install Required Packages**
```powershell
pip install -r requirements.txt
```
### **2. Setup Static Files**
```powershell
mkdir static
move app.html static\
move homepage.html static\
```

### **3. Start the Server**
```powershell
uvicorn main:app --reload
```

**Quick Summary:** The app accepts multiple CSV files in one upload (or multiple uploads). Each file counts as one "dump" per email; an email appearing in three separate dumps with zero opens will be identified for deletion and added to `delete_list.csv`.

---

## How to Run

1. Install required packages:
```powershell
pip install -r requirements.txt
```

2. Setup static files folder:
```powershell
mkdir static
move app.html static\
move homepage.html static\
```

3. Start the server:
```powershell
uvicorn main:app --reload
```

4. Open in your browser:
   - Homepage: http://localhost:8000/ (click "Open App" to launch)
   - Main App: http://localhost:8000/app
   - API docs (optional): http://localhost:8000/docs

---

## How to Use the App

1. Open http://localhost:8000/ and click the **"Open App"** button.
2. You'll see 3 sections:
   - **How It Works** — explanation of the deletion criteria
   - **Upload CSV Files** — drag and drop or click to select multiple CSVs
   - **Download Delete List** — download the list of emails to delete

3. Workflow:
   - Upload one or more CSV files (with Email and Opens columns)
   - Processing happens automatically on upload
   - Download your results:
     - **Delete List** → `delete_list.csv` (emails flagged for deletion)

---

## What Changed from Previous Version

**Removed:**
- Master database (`master_db.csv`) - no longer maintained
- All master DB download/delete endpoints
- Status tracking beyond the current session
- Soft delete status management in a persistent database

**Why?** 
- You don't yet know the structure of your actual master database
- You'll write a separate program to handle deletions in the real master DB
- This tool should focus on one task: identifying emails to delete

---

## How dump_count Works

- Each CSV file counts as one dump for any email it contains (duplicates inside a single file count as one presence).
- `dump_count` tracks how many different files an email appeared in.
- Emails with `dump_count >= 3` AND `total_open == 0` are flagged for deletion.

---

## Input Format

CSV files must contain these columns:
- `Email` - email address
- `Opens` - number of opens (numeric)

Column names are case-insensitive and whitespace is trimmed.

---

## Output

**delete_list.csv**
- Single column: `email`
- Contains all emails that appeared in 3+ dumps with 0 opens
- Ready to be used by your separate deletion program

---

## Quick Test Example

1. Create three CSV files, each containing:
```
email,opens
test@example.com,0
```

2. Upload all three files at once (or upload them separately across multiple uploads).

3. After processing:
   - The app will show: "Processing complete! 1 emails flagged for deletion"
   - `delete_list.csv` will contain `test@example.com`

---

## File Storage

- **Uploaded files:** `uploads/`
- **Delete list:** `delete_list.csv`

To reset manually:
```powershell
del delete_list.csv
rd /s /q uploads
mkdir uploads
```

Or use the reset endpoint:
```powershell
curl -X POST http://localhost:8000/reset
```

---

## API Endpoints

- `GET /` - Homepage
- `GET /app` - Main application interface
- `POST /upload` - Upload and process CSV files
- `GET /download` - Download delete_list.csv
- `GET /status` - Get current status (delete list preview, uploaded files)
- `POST /reset` - Clear all uploaded files and delete list
- `POST /delete/delete_list` - Delete the delete_list.csv file

---

## Troubleshooting

- **Uploads fail:** Ensure `python-multipart` is installed (`pip install -r requirements.txt`).
- **Changes not appearing:** Restart the server with `uvicorn main:app --reload`.
- **Check errors:** Look at the terminal running `uvicorn` for detailed error messages.
- **File not found:** Make sure HTML files are in the `static/` folder.

---

## Next Steps

Use the generated `delete_list.csv` in your separate master database deletion program. The delete list contains only the email addresses that need to be removed based on your criteria (3+ dumps, 0 opens).