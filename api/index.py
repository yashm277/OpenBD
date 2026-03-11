import io
import os
import pandas as pd
from typing import List
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse

app = FastAPI(title="RISE Research API")


def _check_columns(filename: str, df: pd.DataFrame, required: list[str]) -> str | None:
    """Return a human-readable error if any required columns are missing."""
    found = [str(c).strip().lower() for c in df.columns]
    missing = [c for c in required if c not in found]
    if not missing:
        return None
    found_display = ", ".join(f"'{c}'" for c in found[:10]) or "(none detected)"
    missing_display = ", ".join(f"'{c}'" for c in missing)
    return (
        f"'{filename}' is missing required column(s): {missing_display}. "
        f"Columns detected in your file: {found_display}."
    )


async def parse_upload(file: UploadFile) -> pd.DataFrame:
    """Read an uploaded CSV or XLSX file into a DataFrame."""
    content = await file.read()
    if not content:
        raise ValueError(f"'{file.filename}' is empty.")
    ext = os.path.splitext(file.filename or "")[1].lower()
    try:
        if ext in (".xlsx", ".xls"):
            df = pd.read_excel(io.BytesIO(content))
        else:
            df = _read_csv_smart(content)
        if df.empty:
            raise ValueError(f"'{file.filename}' contains no data rows.")
        # Replace NaN with empty string so JSON never contains bare `NaN`
        return df.where(df.notna(), other="")
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Could not read '{file.filename}': {e}")


def _read_csv_smart(content: bytes) -> pd.DataFrame:
    """
    Parse a CSV that may have metadata/title rows before the real header
    (e.g. Google Ads, Search Console exports). Tries multiple encodings and
    auto-detects the first row that looks like a proper header.
    """
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            text = content.decode(encoding)
        except UnicodeDecodeError:
            continue

        lines = text.splitlines()
        if not lines:
            raise ValueError("File is empty.")

        # Detect delimiter by examining the first 20 lines
        # Pick the delimiter that produces the most consistent column count
        best_skiprows = 0
        best_sep = ","
        best_ncols = 0

        for sep in (",", "\t", ";"):
            col_counts = [len(line.split(sep)) for line in lines[:20] if line.strip()]
            if not col_counts:
                continue
            max_cols = max(col_counts)
            if max_cols <= best_ncols:
                continue
            # Find the first row that has that max column count — that's the header
            for i, line in enumerate(lines[:20]):
                if len(line.split(sep)) == max_cols:
                    best_skiprows = i
                    best_sep = sep
                    best_ncols = max_cols
                    break

        if best_ncols == 0:
            raise ValueError("Could not detect columns in file.")

        try:
            df = pd.read_csv(
                io.BytesIO(content),
                sep=best_sep,
                skiprows=best_skiprows,
                encoding=encoding,
            )
            if len(df.columns) > 0:
                return df
        except Exception:
            continue

    raise ValueError("Could not parse the CSV file. Please check the format.")


# ---------------------------------------------------------------------------
# Delete List Generator
# ---------------------------------------------------------------------------

@app.post("/api/upload")
async def upload_csv(files: List[UploadFile] = File(...)):
    """
    Accept one or more CSV dump files (email + opens columns).
    Flags emails appearing in 3+ dumps with 0 total opens.
    Returns a JSON list — frontend generates the download.
    """
    allowed = {".csv", ".xlsx", ".xls"}
    grouped: pd.DataFrame | None = None

    for file in files:
        ext = os.path.splitext(file.filename or "")[1].lower()
        if ext not in allowed:
            return JSONResponse(
                {"error": f"Invalid file type: {file.filename}. Only .csv, .xlsx and .xls are allowed."},
                status_code=400,
            )

        try:
            df = await parse_upload(file)
        except ValueError as e:
            return JSONResponse({"error": str(e)}, status_code=400)

        df.columns = [str(c).strip().lower() for c in df.columns]
        col_err = _check_columns(file.filename or "", df, ["email", "opens"])
        if col_err:
            return JSONResponse({"error": col_err}, status_code=400)

        df = df[["email", "opens"]].copy()
        df.columns = ["email", "open"]
        df["open"] = pd.to_numeric(df["open"], errors="coerce").fillna(0)
        df["email"] = df["email"].astype(str).str.strip().str.lower()
        df = df[df["email"].str.len() > 0]

        per_file = df.groupby("email", as_index=False).agg(total_open=("open", "sum"))
        per_file["presence"] = 1

        if grouped is None:
            grouped = per_file
        else:
            grouped = grouped.merge(per_file, on="email", how="outer", suffixes=("", "_r"))
            grouped["total_open"] = (
                grouped["total_open"].fillna(0) + grouped["total_open_r"].fillna(0)
            )
            grouped["presence"] = (
                grouped["presence"].fillna(0) + grouped["presence_r"].fillna(0)
            )
            grouped = grouped.drop(
                columns=[c for c in ["total_open_r", "presence_r"] if c in grouped.columns]
            )

    if grouped is None:
        return JSONResponse({"deleted_count": 0, "emails": []})

    grouped["total_open"] = pd.to_numeric(grouped["total_open"], errors="coerce").fillna(0)
    grouped["presence"] = pd.to_numeric(grouped["presence"], errors="coerce").fillna(0)

    mask = (grouped["presence"] >= 3) & (grouped["total_open"] == 0)
    emails = grouped.loc[mask, "email"].tolist()

    return JSONResponse({"deleted_count": len(emails), "emails": emails})


# ---------------------------------------------------------------------------
# Duplicate Finder
# ---------------------------------------------------------------------------

@app.post("/api/duplicate-email-finder")
async def duplicate_email_finder(
    files: List[UploadFile] = File(...),
    duplicate_type: str = Form("email"),
):
    """
    Find duplicates by email, company name, or full name.
    Returns rows as JSON — frontend generates the download.
    """
    allowed = {".csv", ".xlsx", ".xls"}
    all_dfs: list[pd.DataFrame] = []

    for file in files:
        ext = os.path.splitext(file.filename or "")[1].lower()
        if ext not in allowed:
            return JSONResponse(
                {"error": f"Invalid file type: {file.filename}. Only .csv, .xlsx and .xls are allowed."},
                status_code=400,
            )

        try:
            df = await parse_upload(file)
        except ValueError as e:
            return JSONResponse({"error": str(e)}, status_code=400)

        df.columns = [str(c).strip().lower() for c in df.columns]

        col_err = _check_columns(file.filename or "", df, ["email"])
        if col_err:
            return JSONResponse({"error": col_err}, status_code=400)

        for col in ("first_name", "last_name", "company"):
            if col not in df.columns:
                df[col] = ""
        for col in ("email", "first_name", "last_name", "company"):
            df[col] = df[col].astype(str).str.strip()
        df["email"] = df["email"].str.lower()
        df = df[df["email"].str.len() > 0]
        all_dfs.append(df)

    if not all_dfs:
        return JSONResponse({"duplicate_count": 0, "rows": []})

    combined = pd.concat(all_dfs, ignore_index=True)

    if duplicate_type == "email":
        counts = combined.groupby("email").size()
        dup_keys = counts[counts > 1].index
        if dup_keys.empty:
            return JSONResponse({"duplicate_count": 0, "rows": []})

        filtered = combined[combined["email"].isin(dup_keys)]

        def agg_email(g: pd.DataFrame) -> pd.Series:
            names = sorted(
                {n for n in (g["first_name"] + " " + g["last_name"]).str.strip() if n}
            )
            companies = sorted({c for c in g["company"] if c})
            return pd.Series({
                "Full Name": ", ".join(names),
                "Company Name": ", ".join(companies),
                "Count": len(g),
                "Emails": g.name,
            })

        out = filtered.groupby("email").apply(agg_email, include_groups=False).reset_index(drop=True)
        rows = out[["Full Name", "Company Name", "Count", "Emails"]].to_dict(orient="records")

    elif duplicate_type == "company":
        combined = combined[combined["company"].str.len() > 0]
        counts = combined.groupby("company").size()
        dup_keys = counts[counts > 1].index
        if dup_keys.empty:
            return JSONResponse({"duplicate_count": 0, "rows": []})

        filtered = combined[combined["company"].isin(dup_keys)]

        def agg_company(g: pd.DataFrame) -> pd.Series:
            names = sorted(
                {n for n in (g["first_name"] + " " + g["last_name"]).str.strip() if n}
            )
            emails = sorted(set(g["email"]))
            return pd.Series({
                "Company Name": g.name,
                "Full Name(s)": ", ".join(names),
                "Count": len(g),
                "Emails": ", ".join(emails),
            })

        out = filtered.groupby("company").apply(agg_company, include_groups=False).reset_index(drop=True)
        rows = out[["Company Name", "Full Name(s)", "Count", "Emails"]].to_dict(orient="records")

    elif duplicate_type == "fullname":
        combined["fullname"] = (combined["first_name"] + " " + combined["last_name"]).str.strip()
        combined = combined[combined["fullname"].str.len() > 0]
        counts = combined.groupby("fullname").size()
        dup_keys = counts[counts > 1].index
        if dup_keys.empty:
            return JSONResponse({"duplicate_count": 0, "rows": []})

        filtered = combined[combined["fullname"].isin(dup_keys)]

        def agg_fullname(g: pd.DataFrame) -> pd.Series:
            companies = sorted({c for c in g["company"] if c})
            emails = sorted(set(g["email"]))
            return pd.Series({
                "Full Name": g.name,
                "Company Name(s)": ", ".join(companies),
                "Count": len(g),
                "Emails": ", ".join(emails),
            })

        out = filtered.groupby("fullname").apply(agg_fullname, include_groups=False).reset_index(drop=True)
        rows = out[["Full Name", "Company Name(s)", "Count", "Emails"]].to_dict(orient="records")

    else:
        return JSONResponse({"error": "Invalid duplicate_type."}, status_code=400)

    return JSONResponse({"duplicate_count": len(rows), "rows": rows})


# ---------------------------------------------------------------------------
# Overlap Checker
# ---------------------------------------------------------------------------

@app.post("/api/overlap-checker")
async def overlap_checker(
    file1: UploadFile = File(...),
    file2: UploadFile = File(...),
):
    """
    Remove emails in file2 from file1.
    Returns remaining emails as JSON — frontend generates the download.
    """
    allowed = {".csv", ".xlsx", ".xls"}
    for f in (file1, file2):
        ext = os.path.splitext(f.filename or "")[1].lower()
        if ext not in allowed:
            return JSONResponse(
                {"error": f"Invalid file type: {f.filename}. Only .csv, .xlsx and .xls are allowed."},
                status_code=400,
            )

    try:
        df1 = await parse_upload(file1)
        df2 = await parse_upload(file2)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)

    df1.columns = [str(c).strip().lower() for c in df1.columns]
    df2.columns = [str(c).strip().lower() for c in df2.columns]

    col_err1 = _check_columns(file1.filename or "CSV 1", df1, ["email"])
    if col_err1:
        return JSONResponse({"error": col_err1}, status_code=400)
    col_err2 = _check_columns(file2.filename or "CSV 2", df2, ["email"])
    if col_err2:
        return JSONResponse({"error": col_err2}, status_code=400)

    emails1 = set(df1["email"].astype(str).str.strip().str.lower())
    emails2 = set(df2["email"].astype(str).str.strip().str.lower())

    remaining = sorted(emails1 - emails2)
    overlap_count = len(emails1 & emails2)

    return JSONResponse({
        "csv1_total": len(emails1),
        "csv2_total": len(emails2),
        "overlap_count": overlap_count,
        "remaining_count": len(remaining),
        "emails": remaining,
    })
