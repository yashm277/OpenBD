# RISE - CSV_counter

A FastAPI application for processing email data dumps and identifying emails to soft-delete based on engagement metrics.

## **Quick Start - How to Run**
### **1. Install Required Packages**
```powershell
pip install fastapi uvicorn pandas
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

### **Step 2: Upload CSV File**
- Click the `POST /upload` endpoint
- Click **"Try it out"** button
- Click **"Choose File"** and select your CSV file
- The CSV must contain these columns:
  - **Email** - email addresses
  - **Opens** - number of times email was opened
- Click **"Execute"**
### **Step 3: View Results**
The response will show:
- **message**: "Processed successfully" or "Soft delete applied successfully"
- **deleted_count**: Number of emails marked for deletion
- **download_url**: Link to download the delete list
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

1. Upload `data_dump_1.csv` → Emails added to master_db.csv
2. Upload `data_dump_2.csv` → Totals are accumulated
3. Upload `data_dump_3.csv` → Emails meeting delete criteria are added to delete_list.csv
4. Click **GET /download** → Get the delete_list.csv file
---
## **Download Results**
- Go to **http://localhost:8000/download**
- Or click the download link from the upload response
- This downloads the current **delete_list.csv** file