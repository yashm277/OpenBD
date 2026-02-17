
# RISE - Email Data Tools

A FastAPI application for processing email data dumps. Now includes two features:
- **Delete List Generator**: Identify emails to delete based on engagement metrics.
- **Duplicate Email Finder**: Find duplicate emails across multiple CSVs.

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
move duplicate.html static\
```


### **3. Start the Server**
```powershell
uvicorn app:app --reload
```


**Quick Summary:**
- The app now supports two tools from the homepage:
   - **Delete List Generator**: Upload CSVs with Email/Opens columns to generate `delete_list.csv` (emails in 3+ dumps with 0 opens).
   - **Duplicate Email Finder**: Upload CSVs with email/name/company columns to generate `duplicate_emails.csv` (all duplicate emails, grouped).

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
   - Homepage: http://localhost:8000/ (choose a tool)
   - Delete List Generator: http://localhost:8000/app
   - Duplicate Email Finder: http://localhost:8000/static/duplicate.html
   - API docs (optional): http://localhost:8000/docs

---


## How to Use the App

1. Open http://localhost:8000/ and choose a tool:
   - **Open App**: Delete List Generator (for deletion list)
   - **Duplicate Email Finder**: Find duplicate emails

### Delete List Generator
1. Upload one or more CSV files (must have `Email` and `Opens` columns)
2. Processing happens automatically
3. Download your results: `delete_list.csv` (emails flagged for deletion)

### Duplicate Email Finder
1. Upload one or more CSV files (must have `email` column; `first_name`, `last_name`, `company` optional)
2. Processing happens automatically
3. Download your results: `duplicate_emails.csv` (all duplicate emails, grouped by email)

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

**delete_list.csv** (Delete List Generator)
- Single column: `email`
- Contains all emails that appeared in 3+ dumps with 0 opens
- Ready to be used by your separate deletion program

**duplicate_emails.csv** (Duplicate Email Finder)
- Columns: `Full Name`, `Company Name`, `Count`, `Emails`
- Each row is a duplicate email (appeared more than once across all uploads)
- `Full Name` and `Company Name` are from the first occurrence
- `Count` is the number of times the email appeared
- `Emails` is a comma-separated list of all duplicate emails (should be the same email repeated)

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
- **Duplicate emails report:** `duplicate_emails.csv`

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
- `GET /app` - Main application interface (Delete List Generator)
- `POST /upload` - Upload and process CSV files for delete list
- `GET /download` - Download delete_list.csv
- `GET /status` - Get current status (delete list preview, uploaded files)
- `POST /reset` - Clear all uploaded files and delete list
- `POST /delete/delete_list` - Delete the delete_list.csv file
- `POST /duplicate-email-finder` - Upload and process CSV files for duplicate email finder
- `GET /download-duplicates` - Download duplicate_emails.csv

---


## Troubleshooting

- **Uploads fail:** Ensure `python-multipart` is installed (`pip install -r requirements.txt`).
- **Changes not appearing:** Restart the server with `uvicorn app:app --reload`.
- **Check errors:** Look at the terminal running `uvicorn` for detailed error messages.
- **File not found:** Make sure all HTML files (app.html, homepage.html, duplicate.html) are in the `static/` folder.

---

## Next Steps

Use the generated `delete_list.csv` in your separate master database deletion program. The delete list contains only the email addresses that need to be removed based on your criteria (3+ dumps, 0 opens).