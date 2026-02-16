# OpenBD - Dashboard

A central dashboard for data management tools, starting with a FastAPI-powered Delete List Generator. Deploy to Vercel and add more tools as you build them.

## **Quick Start - Deploy to Vercel**

### **Option 1: Deploy via Vercel CLI**
```powershell
# Install Vercel CLI
npm install -g vercel

# Login to Vercel
vercel login

# Deploy
vercel
```

### **Option 2: Deploy via GitHub**
1. Push this repo to GitHub
2. Go to [vercel.com](https://vercel.com)
3. Import your GitHub repository
4. Click Deploy - Vercel auto-detects the Python + FastAPI setup

---

## **Local Development**

### **1. Install Required Packages**
```powershell
pip install -r requirements.txt
```

### **2. Start the Server**
```powershell
uvicorn api.index:app --reload
```

### **3. Open in Browser**
- **Dashboard**: http://localhost:8000/
- **Delete List Tool**: http://localhost:8000/tools/delete-list
- **API docs**: http://localhost:8000/docs

---

## Project Structure

```
OpenBD/
├── api/
│   └── index.py          # Main FastAPI app (Vercel entry point)
├── static/               # Static files (optional, for local dev)
├── vercel.json           # Vercel configuration
├── requirements.txt      # Python dependencies
└── README.md
```

---

## Adding New Tools

1. Create a new HTML template in `api/index.py` (as an embedded string or separate file)
2. Add a new route in `api/index.py`:
   ```python
   @app.get("/tools/your-new-tool")
   def your_new_tool():
       return HTMLResponse(content=YOUR_TOOL_HTML, status_code=200)
   ```
3. Add a card to the dashboard HTML in `DASHBOARD_HTML`
4. Push to GitHub → Vercel auto-deploys

---

## Delete List Generator

**What it does:** Identifies emails to delete based on engagement metrics.

**Quick Summary:** Upload multiple CSV files. Each file counts as one "dump" per email; an email appearing in three separate dumps with zero opens will be identified for deletion and added to `delete_list.csv`.

### Input Format

CSV files must contain these columns:
- `Email` - email address
- `Opens` - number of opens (numeric)

### Output

**delete_list.csv**
- Single column: `email`
- Contains all emails that appeared in 3+ dumps with 0 opens

### Quick Test Example

1. Create three CSV files, each containing:
```
email,opens
test@example.com,0
```

2. Upload all three files at once

3. Download the delete list - it will contain `test@example.com`

---

## API Endpoints

### Dashboard
- `GET /` - Main dashboard

### Delete List Tool
- `GET /tools/delete-list` - Delete List Generator UI
- `POST /api/upload` - Upload and process CSV files
- `GET /api/download` - Download delete_list.csv
- `GET /api/status` - Get current status
- `POST /api/reset` - Clear all uploaded files and delete list

### Legacy Routes (backwards compatible)
- `GET /app` - Redirects to delete list tool
- `POST /upload` - Same as `/api/upload`
- `GET /download` - Same as `/api/download`

---

## Troubleshooting

- **Vercel build fails:** Ensure `requirements.txt` includes all dependencies
- **Uploads fail locally:** Ensure `python-multipart` is installed
- **Check errors:** Look at Vercel deployment logs or local terminal

---

## Next Steps

- Add more tools to the dashboard
- Use the generated `delete_list.csv` in your master database deletion program
- Customize the dashboard styling