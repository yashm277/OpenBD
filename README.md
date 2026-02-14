# RISE - CSV_counter

A FastAPI application for processing email data dumps and identifying emails to soft-delete based on engagement metrics.

## **Quick Start - How to Run**
### **1. Install Required Packages**
```powershell
pip install fastapi uvicorn pandas python-multipart
```
### **2. Start the Server**
```powershell
uvicorn app:app --reload
```
The app will run at: **http://localhost:8000**
---
## **How to Use the App**
### **Step 1: Open the API Interface**
- Go to **http://localhost:8000/docs** (Swagger UI - interactive documentation)
- Or use **http://localhost:8000/redoc** (ReDoc)

- Click the `POST /upload` endpoint
- Click **"Try it out"** button
- Use **"Choose File"** to select one or more CSV files (you can select multiple files)
- The CSV must contain these columns:
  - **Email** - email addresses
  - **Opens** - number of times email was opened
- Click **"Execute"**
### **Step 3: View Results**
The response will show:
- **message**: "Processed successfully" or "Soft delete applied successfully"
- **deleted_count**: Number of emails marked for deletion
- **download_url**: Link to download the delete list

You can also open the simple web form at the site root (`/`) and upload multiple files using the browser.
---

## **What Gets Generated**
### **Files Created:**
1. **master_db.csv** - Main database with all emails and their stats
   - Columns: email, total_open, dump_count, status
   
2. **delete_list.csv** - List of emails to soft-delete
   - Columns: email
### **Soft-Delete Criteria**
Emails are marked as "soft_delete" when:
- Received **3 or more times** (dump_count ≥ 3) AND
- **ZERO total opens** (total_open = 0)
---
## **Workflow Example**

1. Upload `data_dump_1.csv` and `data_dump_2.csv` and `data_dump_3.csv` (you can upload them together) → Each file counts as one dump for any email it contains
2. Totals are accumulated across files and previous uploads; if an email appears in 3 separate dumps (files), `dump_count` will reach 3
3. Emails with `dump_count >= 3` and `total_open == 0` are marked `soft_delete` and listed in `delete_list.csv`
4. Click **GET /download** → Get the delete_list.csv file
---
## **Download Results**
- Go to **http://localhost:8000/download**
- Or click the download link from the upload response
- This downloads the current **delete_list.csv** file

---

If the server crashed earlier with a message about `python-multipart`, that package is required for file uploads. Install it with the command above.