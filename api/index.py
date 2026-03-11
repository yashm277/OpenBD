import csv
import io
import logging
import os
import pandas as pd
from typing import List
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

logger = logging.getLogger(__name__)

app = FastAPI(title="RISE Research API")

ALLOWED_UPLOAD_EXTS = {".csv", ".xlsx", ".xls"}


def _join_unique_nonempty(s: pd.Series) -> str:
    """Join unique non-empty values from a Series, sorted alphabetically."""
    return ", ".join(sorted(x for x in s.unique() if x))


def _join_unique(s: pd.Series) -> str:
    """Join all unique values from a Series, sorted alphabetically."""
    return ", ".join(sorted(s.unique()))


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


def _validate_extension(filename: str) -> str | None:
    """Return a human-readable error message if the file extension is not allowed."""
    ext = os.path.splitext(filename or "")[1].lower()
    if ext not in ALLOWED_UPLOAD_EXTS:
        allowed_str = ", ".join(sorted(ALLOWED_UPLOAD_EXTS))
        return f"Invalid file type: '{filename}'. Only {allowed_str} files are allowed."
    return None


async def parse_upload(file: UploadFile) -> pd.DataFrame:
    """Read an uploaded CSV or XLSX file into a DataFrame."""
    content = await file.read()
    if not content:
        raise ValueError(f"'{file.filename}' is empty.")
    ext = os.path.splitext(file.filename or "")[1].lower()
    try:
        if ext in (".xlsx", ".xls"):
            df = await run_in_threadpool(pd.read_excel, io.BytesIO(content))
        else:
            df = await run_in_threadpool(_read_csv_smart, content)
        if df.empty:
            raise ValueError(f"'{file.filename}' contains no data rows.")
        # Replace NaN with empty string so JSON never contains bare `NaN`
        return df.where(df.notna(), other="")
    except ValueError:
        raise
    except Exception:
        logger.exception("Failed to parse uploaded file '%s'", file.filename)
        raise ValueError(
            f"Could not read '{file.filename}'. "
            "Ensure the file is a valid CSV or XLSX and is not password-protected."
        )


def _read_csv_smart(content: bytes) -> pd.DataFrame:
    """
    Parse a CSV that may have metadata/title rows before the real header
    (e.g. Google Ads, Search Console exports). Tries multiple encodings and
    auto-detects the first row that looks like a proper header, using
    csv.Sniffer for robust delimiter detection.
    """
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            text = content.decode(encoding)
        except UnicodeDecodeError:
            continue

        non_empty_lines = [l for l in text.splitlines() if l.strip()]
        if not non_empty_lines:
            raise ValueError("File is empty.")

        # Detect delimiter with csv.Sniffer (respects quoted fields)
        sample = "\n".join(non_empty_lines[:20])
        try:
            dialect = csv.Sniffer().sniff(sample[:min(len(sample), 4096)])
            sep = dialect.delimiter
        except csv.Error:
            sep = ","

        # Find header row: first row that yields the most non-empty fields
        reader = csv.reader(io.StringIO(sample), delimiter=sep)
        best_skiprows = 0
        best_ncols = 0
        for i, row in enumerate(reader):
            ncols = len([c for c in row if c.strip()])
            if ncols > best_ncols:
                best_ncols = ncols
                best_skiprows = i

        if best_ncols == 0:
            raise ValueError("Could not detect columns in file.")

        try:
            df = pd.read_csv(
                io.BytesIO(content),
                sep=sep,
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
    all_per_file: list[pd.DataFrame] = []

    for file in files:
        ext_err = _validate_extension(file.filename or "")
        if ext_err:
            return JSONResponse({"error": ext_err}, status_code=400)

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
        all_per_file.append(per_file)

    if not all_per_file:
        return JSONResponse({"deleted_count": 0, "emails": []})

    # Concat all per-file frames once, then aggregate — avoids repeated outer-merges
    combined = pd.concat(all_per_file, ignore_index=True)
    grouped = combined.groupby("email", as_index=False).agg(
        total_open=("total_open", "sum"),
        presence=("presence", "sum"),
    )

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
    all_dfs: list[pd.DataFrame] = []

    for file in files:
        ext_err = _validate_extension(file.filename or "")
        if ext_err:
            return JSONResponse({"error": ext_err}, status_code=400)

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

        filtered = combined[combined["email"].isin(dup_keys)].copy()
        filtered["fullname_key"] = (
            filtered["first_name"] + " " + filtered["last_name"]
        ).str.strip()

        out = (
            filtered.groupby("email", as_index=False)
            .agg(
                full_name=("fullname_key", _join_unique_nonempty),
                company_name=("company", _join_unique_nonempty),
            )
            .rename(
                columns={
                    "email": "Emails",
                    "full_name": "Full Name",
                    "company_name": "Company Name",
                }
            )
        )
        out["Count"] = out["Emails"].map(counts)
        rows = out[["Full Name", "Company Name", "Count", "Emails"]].to_dict(
            orient="records"
        )

    elif duplicate_type == "company":
        combined = combined[combined["company"].str.len() > 0]
        counts = combined.groupby("company").size()
        dup_keys = counts[counts > 1].index
        if dup_keys.empty:
            return JSONResponse({"duplicate_count": 0, "rows": []})

        filtered = combined[combined["company"].isin(dup_keys)].copy()
        filtered["fullname_key"] = (
            filtered["first_name"] + " " + filtered["last_name"]
        ).str.strip()

        out = (
            filtered.groupby("company", as_index=False)
            .agg(
                full_names=("fullname_key", _join_unique_nonempty),
                emails=("email", _join_unique),
            )
            .rename(
                columns={
                    "company": "Company Name",
                    "full_names": "Full Name(s)",
                    "emails": "Emails",
                }
            )
        )
        out["Count"] = out["Company Name"].map(counts)
        rows = out[["Company Name", "Full Name(s)", "Count", "Emails"]].to_dict(
            orient="records"
        )

    elif duplicate_type == "fullname":
        combined = combined.copy()
        combined["fullname"] = (
            combined["first_name"] + " " + combined["last_name"]
        ).str.strip()
        combined = combined[combined["fullname"].str.len() > 0]
        counts = combined.groupby("fullname").size()
        dup_keys = counts[counts > 1].index
        if dup_keys.empty:
            return JSONResponse({"duplicate_count": 0, "rows": []})

        filtered = combined[combined["fullname"].isin(dup_keys)]

        out = (
            filtered.groupby("fullname", as_index=False)
            .agg(
                companies=("company", _join_unique_nonempty),
                emails=("email", _join_unique),
            )
            .rename(
                columns={
                    "fullname": "Full Name",
                    "companies": "Company Name(s)",
                    "emails": "Emails",
                }
            )
        )
        out["Count"] = out["Full Name"].map(counts)
        rows = out[["Full Name", "Company Name(s)", "Count", "Emails"]].to_dict(
            orient="records"
        )

    else:
        allowed_duplicate_types = ["email", "company", "fullname"]
        return JSONResponse(
            {
                "error": (
                    f"Invalid duplicate_type '{duplicate_type}'. "
                    f"Allowed values are: {', '.join(allowed_duplicate_types)}."
                )
            },
            status_code=400,
        )

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
    for f in (file1, file2):
        ext_err = _validate_extension(f.filename or "")
        if ext_err:
            return JSONResponse({"error": ext_err}, status_code=400)

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

    emails1_series = df1["email"].astype(str).str.strip().str.lower()
    emails2_series = df2["email"].astype(str).str.strip().str.lower()
    emails1 = set(e for e in emails1_series if e)
    emails2 = set(e for e in emails2_series if e)

    remaining = sorted(emails1 - emails2)
    overlap_count = len(emails1 & emails2)

    return JSONResponse({
        "csv1_total": len(emails1),
        "csv2_total": len(emails2),
        "overlap_count": overlap_count,
        "remaining_count": len(remaining),
        "emails": remaining,
    })
