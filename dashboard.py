"""
SMART CLOUD FILE MANAGER
Professional Streamlit Dashboard

Architecture:
Streamlit Dashboard
        |
        v
S3 raw/
        |
        v
Lambda
        |
        +----> category folders
        |
        +----> DynamoDB metadata
        |
        +----> analytics JSON
                    |
                    v
                 Athena

Main features:
- Professional dashboard
- Native Streamlit UI
- S3 upload
- DynamoDB metadata
- Athena analytics
- Overview
- Files & Analytics
- Settings
- Search and filters
- Refresh
- Download
- Safe delete confirmation
- Old / large / normal file health
- No fake statistics
"""

import os
import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

import boto3
import pandas as pd
import streamlit as st

from botocore.exceptions import ClientError


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Smart Cloud File Manager",
    page_icon="☁️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# CONFIGURATION
# ============================================================

AWS_REGION = os.getenv("AWS_REGION", "eu-north-1")

S3_BUCKET = os.getenv("S3_BUCKET", "suhani--s3")
RAW_PREFIX = os.getenv("RAW_PREFIX", "raw/")

ATHENA_DATABASE = os.getenv(
    "ATHENA_DATABASE",
    "smart_file_manager",
)

ATHENA_TABLE = os.getenv(
    "ATHENA_TABLE",
    "file_metadata",
)

ATHENA_OUTPUT = os.getenv(
    "ATHENA_OUTPUT",
    f"s3://{S3_BUCKET}/athena-results/",
)

DYNAMODB_TABLE = os.getenv(
    "DYNAMODB_TABLE",
    "FileMetadata",
)

MAX_UPLOAD_MB = 200

# Existing project thresholds should be preserved.
# These are used only if the metadata does not already contain
# the calculated status.
OLD_FILE_DAYS = 30
LARGE_FILE_MB = 100


# ============================================================
# AWS CLIENTS
# ============================================================

@st.cache_resource
def get_aws_clients():
    """
    Create AWS clients once per Streamlit process.
    """

    session = boto3.Session(region_name=AWS_REGION)

    s3 = session.client("s3")
    dynamodb = session.resource("dynamodb")
    athena = session.client("athena")

    return s3, dynamodb, athena


s3_client, dynamodb_resource, athena_client = get_aws_clients()


# ============================================================
# CUSTOM CSS — SMART CLOUD FILE MANAGER
# ============================================================

st.markdown(
    """
    <style>

    /* ========================================================
       GLOBAL APPLICATION
       ======================================================== */

    .stApp {
        background: #071321 !important;
        color: #e8eef7 !important;
    }

    [data-testid="stAppViewContainer"] {
        background: #071321 !important;
    }

    [data-testid="stMain"] {
        background: #071321 !important;
    }

    [data-testid="stMainBlockContainer"] {
        padding-top: 1rem !important;
        padding-bottom: 0.5rem !important;
        max-width: 1600px !important;
    }

    header[data-testid="stHeader"] {
        background: #071321 !important;
    }

    footer {
        visibility: hidden !important;
    }

    [data-testid="stDecoration"] {
        display: none !important;
    }


    /* ========================================================
       MAIN TEXT
       ======================================================== */

    [data-testid="stAppViewContainer"] p {
        color: #cbd5e1 !important;
    }

    [data-testid="stAppViewContainer"] span {
        color: #cbd5e1 !important;
    }

    [data-testid="stAppViewContainer"] label {
        color: #cbd5e1 !important;
    }

    [data-testid="stAppViewContainer"] small {
        color: #94a3b8 !important;
    }

    [data-testid="stMarkdownContainer"] p {
        color: #cbd5e1 !important;
    }

    [data-testid="stMarkdownContainer"] span {
        color: #cbd5e1 !important;
    }


    /* ========================================================
       HEADINGS
       ======================================================== */

    h1 {
        color: #f8fafc !important;
        font-weight: 750 !important;
    }

    h2 {
        color: #f8fafc !important;
        font-weight: 700 !important;
    }

    h3 {
        color: #f1f5f9 !important;
        font-weight: 650 !important;
    }

    [data-testid="stMarkdownContainer"] h1,
    [data-testid="stMarkdownContainer"] h2,
    [data-testid="stMarkdownContainer"] h3 {
        color: #f8fafc !important;
    }


    /* ========================================================
       SIDEBAR
       ======================================================== */

    section[data-testid="stSidebar"] {
        background: #081a2d !important;
        border-right: 1px solid #1d3b5a !important;
    }

    section[data-testid="stSidebar"] > div {
        background: #081a2d !important;
    }

    section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
        background: #081a2d !important;
    }

    /* Sidebar ALL TEXT */

    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] div,
    section[data-testid="stSidebar"] small {
        color: #b9c9da !important;
    }

    /* Sidebar markdown text */

    section[data-testid="stSidebar"]
    [data-testid="stMarkdownContainer"] p {
        color: #b9c9da !important;
    }

    section[data-testid="stSidebar"]
    [data-testid="stMarkdownContainer"] span {
        color: #b9c9da !important;
    }

    /* Sidebar title */

    section[data-testid="stSidebar"]
    [data-testid="stMarkdownContainer"] h1,
    section[data-testid="stSidebar"]
    [data-testid="stMarkdownContainer"] h2,
    section[data-testid="stSidebar"]
    [data-testid="stMarkdownContainer"] h3 {
        color: #f8fafc !important;
    }

    /* Sidebar navigation buttons */

    section[data-testid="stSidebar"] .stButton > button {
        width: 100% !important;
        min-height: 40px !important;

        background: #0c2238 !important;
        color: #dbeafe !important;

        border: 1px solid #245077 !important;
        border-radius: 9px !important;

        font-size: 14px !important;
        font-weight: 600 !important;

        box-shadow: none !important;
    }

    section[data-testid="stSidebar"] .stButton > button p {
        color: #dbeafe !important;
    }

    section[data-testid="stSidebar"] .stButton > button span {
        color: #dbeafe !important;
    }

    /* Sidebar hover */

    section[data-testid="stSidebar"] .stButton > button:hover {
        background: #123553 !important;
        border-color: #3b82c4 !important;
        color: #ffffff !important;
    }

    section[data-testid="stSidebar"] .stButton > button:hover p,
    section[data-testid="stSidebar"] .stButton > button:hover span {
        color: #ffffff !important;
    }


    /* ========================================================
       SIDEBAR PIPELINE TEXT
       ======================================================== */

    section[data-testid="stSidebar"] .small-text {
        color: #8fa9c1 !important;
        font-size: 12px !important;
    }


    /* ========================================================
       NORMAL BUTTONS
       ======================================================== */

    .stButton > button {
        background: #0d243b !important;
        color: #dbeafe !important;

        border: 1px solid #28557d !important;
        border-radius: 9px !important;

        font-weight: 600 !important;
    }

    .stButton > button p,
    .stButton > button span {
        color: #dbeafe !important;
    }

    .stButton > button:hover {
        background: #123654 !important;
        border-color: #3d8dcc !important;
        color: #ffffff !important;
    }

    .stButton > button:hover p,
    .stButton > button:hover span {
        color: #ffffff !important;
    }


    /* ========================================================
       KPI CARDS
       ======================================================== */

    .kpi-card {
        background: #0b2035 !important;

        border: 1px solid #244766 !important;
        border-radius: 12px !important;

        padding: 12px !important;

        min-height: 92px !important;
        height: 92px !important;

        box-sizing: border-box !important;

        overflow: hidden !important;
    }

    /* KPI LABEL */

    .kpi-card .kpi-label {
        color: #8fa8c0 !important;

        font-size: 11px !important;
        font-weight: 600 !important;

        text-transform: uppercase !important;
        letter-spacing: 0.3px !important;

        margin-bottom: 4px !important;
    }

    /* KPI VALUE */

    .kpi-card .kpi-value {
        color: #f1f5f9 !important;

        font-size: 22px !important;
        line-height: 1.05 !important;

        font-weight: 700 !important;

        margin: 0 !important;

        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }

    /* KPI DESCRIPTION */

    .kpi-card .kpi-description {
        color: #7f99b2 !important;

        font-size: 9px !important;
        line-height: 1.1 !important;

        margin-top: 4px !important;
    }


    /* ========================================================
       IF KPI CARDS USE st.metric()
       ======================================================== */

    div[data-testid="stMetric"] {
        background: #0b2035 !important;

        border: 1px solid #244766 !important;
        border-radius: 12px !important;

        padding: 11px !important;

        min-height: 88px !important;
        height: 88px !important;

        box-sizing: border-box !important;
    }

    div[data-testid="stMetricLabel"] {
        color: #8fa8c0 !important;
    }

    div[data-testid="stMetricLabel"] p {
        color: #8fa8c0 !important;

        font-size: 11px !important;
        font-weight: 600 !important;

        text-transform: uppercase !important;
    }

    div[data-testid="stMetricValue"] {
        color: #f1f5f9 !important;

        font-size: 22px !important;
        font-weight: 700 !important;

        line-height: 1.05 !important;
    }

    div[data-testid="stMetricDelta"] {
        font-size: 10px !important;
    }


    /* ========================================================
       UPLOAD CENTER
       ======================================================== */

    [data-testid="stFileUploader"] {
        background: #0a1e32 !important;

        border: 1px dashed #35688f !important;
        border-radius: 12px !important;

        padding: 8px !important;
    }

    [data-testid="stFileUploader"] section {
        background: transparent !important;
    }

    [data-testid="stFileUploader"] label {
        color: #dbeafe !important;
    }

    [data-testid="stFileUploader"] p {
        color: #a9bfd3 !important;
    }

    [data-testid="stFileUploader"] span {
        color: #a9bfd3 !important;
    }

    [data-testid="stFileUploader"] small {
        color: #819bb3 !important;
    }


    /* ========================================================
       FILE UPLOADER BUTTON
       ======================================================== */

    [data-testid="stFileUploader"] button {
        background: #e8eef7 !important;
        color: #13263b !important;

        border: 1px solid #d3dce7 !important;
        border-radius: 7px !important;
    }

    [data-testid="stFileUploader"] button span,
    [data-testid="stFileUploader"] button p {
        color: #13263b !important;
    }


    /* ========================================================
       DATAFRAME
       ======================================================== */

    [data-testid="stDataFrame"] {
        border: 1px solid #244766 !important;
        border-radius: 10px !important;
        overflow: hidden !important;
    }


    /* ========================================================
       ALERTS / SUCCESS / ERROR / INFO
       ======================================================== */

    [data-testid="stAlert"] {
        border-radius: 9px !important;
    }


    /* ========================================================
       CAPTIONS
       ======================================================== */

    [data-testid="stCaptionContainer"] {
        color: #8fa8c0 !important;
    }

    [data-testid="stCaptionContainer"] p {
        color: #8fa8c0 !important;
        font-size: 12px !important;
    }


    /* ========================================================
       SMALL TEXT
       ======================================================== */

    .small-text {
        color: #8fa8c0 !important;
        font-size: 12px !important;
    }


    /* ========================================================
       CODE / SYSTEM INFORMATION
       ======================================================== */

    code {
        background: #0a1b2d !important;
        color: #9ed0ff !important;

        border: 1px solid #1c3b59 !important;
        border-radius: 5px !important;
    }


    /* ========================================================
       SELECTBOX / INPUTS
       ======================================================== */

    div[data-baseweb="select"] > div {
        background: #0b2035 !important;
        border-color: #28557d !important;
        color: #dbeafe !important;
    }

    div[data-baseweb="select"] span {
        color: #dbeafe !important;
    }

    input {
        background: #0b2035 !important;
        color: #e8eef7 !important;

        border-color: #28557d !important;
    }

    textarea {
        background: #0b2035 !important;
        color: #e8eef7 !important;

        border-color: #28557d !important;
    }


    /* ========================================================
       CHECKBOX
       ======================================================== */

    [data-testid="stCheckbox"] label {
        color: #cbd5e1 !important;
    }

    [data-testid="stCheckbox"] label p {
        color: #cbd5e1 !important;
    }


    /* ========================================================
       EXPANDERS
       ======================================================== */

    [data-testid="stExpander"] {
        background: #0a1e32 !important;

        border: 1px solid #244766 !important;
        border-radius: 10px !important;
    }

    [data-testid="stExpander"] p,
    [data-testid="stExpander"] span {
        color: #cbd5e1 !important;
    }


    /* ========================================================
       DIVIDERS
       ======================================================== */

    hr {
        border-color: #1b354f !important;
    }


    /* ========================================================
       RESPONSIVE COMPACT SPACING
       ======================================================== */

    [data-testid="stHorizontalBlock"] {
        gap: 0.7rem !important;
    }


    /* ========================================================
       REMOVE UNWANTED LINK LOOK
       ======================================================== */

    a {
        color: #75b8f0 !important;
    }

    a:hover {
        color: #a9d7ff !important;
    }


    /* ========================================================
       SYSTEM STATUS
       ======================================================== */

    .system-online {
        color: #22c55e !important;
        font-weight: 700 !important;
    }


    /* ========================================================
       MOBILE / SMALL SCREEN
       ======================================================== */

    @media (max-width: 900px) {

        .kpi-card {
            min-height: 82px !important;
            height: 82px !important;
            padding: 9px !important;
        }

        .kpi-card .kpi-value {
            font-size: 19px !important;
        }

        div[data-testid="stMetric"] {
            min-height: 82px !important;
            height: 82px !important;
            padding: 9px !important;
        }

        div[data-testid="stMetricValue"] {
            font-size: 19px !important;
        }

    }
/* ========================================================
   HEADER LAYOUT
   ======================================================== */

div[data-testid="stHorizontalBlock"] {
    align-items: center !important;
}

/* Refresh button specifically */
button[kind="secondary"] {
    white-space: nowrap !important;
}

/* Prevent header columns from becoming too narrow */
div[data-testid="column"] {
    min-width: 0 !important;
}
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def decimal_to_python(value: Any) -> Any:
    """
    Convert DynamoDB Decimal values into normal Python values.
    """

    if isinstance(value, Decimal):
        if value % 1 == 0:
            return int(value)
        return float(value)

    return value


def clean_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert DynamoDB values to Streamlit/Pandas compatible values.
    """

    result = {}

    for key, value in record.items():
        result[key] = decimal_to_python(value)

    return result


def format_size(size_bytes: Any) -> str:
    """
    Format bytes into human-readable size.
    """

    try:
        size = float(size_bytes or 0)
    except (ValueError, TypeError):
        size = 0

    if size < 1024:
        return f"{size:.0f} B"

    if size < 1024 ** 2:
        return f"{size / 1024:.1f} KB"

    if size < 1024 ** 3:
        return f"{size / (1024 ** 2):.1f} MB"

    return f"{size / (1024 ** 3):.2f} GB"


def format_number(value: Any) -> str:
    """
    Format a number with commas.
    """

    try:
        return f"{int(value):,}"
    except (ValueError, TypeError):
        return "0"


def parse_datetime(value: Any) -> Optional[datetime]:
    """
    Parse ISO timestamps safely.
    """

    if not value:
        return None

    if isinstance(value, datetime):
        dt = value

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt

    try:
        text = str(value).strip()

        if text.endswith("Z"):
            text = text[:-1] + "+00:00"

        dt = datetime.fromisoformat(text)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt

    except (ValueError, TypeError):
        return None


def calculate_age_days(upload_time: Any) -> Optional[float]:
    """
    Calculate actual file age from upload_time.

    This avoids relying blindly on an old age_in_days value.
    """

    dt = parse_datetime(upload_time)

    if dt is None:
        return None

    now = datetime.now(timezone.utc)

    seconds = max(
        0,
        (now - dt).total_seconds(),
    )

    return round(seconds / 86400, 2)


def determine_age_status(
    record: Dict[str, Any],
    age_days: Optional[float],
) -> str:
    """
    Use existing metadata status when available.
    Otherwise calculate using the existing 30-day threshold.
    """

    existing = str(
        record.get("age_status", "")
    ).upper().strip()

    if existing in {
        "OLD_FILE",
        "NEW_FILE",
    }:
        return existing

    if age_days is None:
        return "UNKNOWN"

    if age_days >= OLD_FILE_DAYS:
        return "OLD_FILE"

    return "NEW_FILE"


def determine_size_status(
    record: Dict[str, Any],
) -> str:
    """
    Preserve existing size_status when present.
    Otherwise calculate using the existing 100 MB threshold.
    """

    existing = str(
        record.get("size_status", "")
    ).upper().strip()

    if existing in {
        "LARGE_FILE",
        "NORMAL",
    }:
        return existing

    try:
        size_bytes = float(
            record.get("file_size_bytes", 0) or 0
        )

        size_mb = size_bytes / (1024 ** 2)

        if size_mb >= LARGE_FILE_MB:
            return "LARGE_FILE"

        return "NORMAL"

    except (ValueError, TypeError):
        return "UNKNOWN"


def determine_overall_status(
    age_status: str,
    size_status: str,
    record: Dict[str, Any],
) -> str:
    """
    Determine final health status.
    """

    existing = str(
        record.get("status", "")
    ).upper().strip()

    if existing in {
        "OLD_FILE",
        "LARGE_FILE",
        "NORMAL",
    }:
        return existing

    if age_status == "OLD_FILE":
        return "OLD_FILE"

    if size_status == "LARGE_FILE":
        return "LARGE_FILE"

    return "NORMAL"


def normalize_category(category: Any) -> str:
    """
    Normalize category values.
    """

    value = str(category or "").strip().lower()

    if value in {
        "image",
        "images",
    }:
        return "Images"

    if value in {
        "document",
        "documents",
    }:
        return "Documents"

    if value in {
        "video",
        "videos",
    }:
        return "Videos"

    return "Others"


def normalize_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prepare one metadata record for dashboard use.
    """

    record = clean_record(record)

    file_name = str(
        record.get("file_name", "Unknown")
    )

    file_type = str(
        record.get("file_type", "")
    ).lower().strip()

    category = normalize_category(
        record.get("category")
    )

    size_bytes = record.get(
        "file_size_bytes",
        0,
    )

    try:
        size_bytes = int(float(size_bytes or 0))
    except (ValueError, TypeError):
        size_bytes = 0

    upload_time = record.get(
        "upload_time"
    )

    age_days = calculate_age_days(
        upload_time
    )

    if age_days is None:
        existing_age = record.get(
            "age_in_days"
        )

        try:
            age_days = float(
                existing_age
            )
        except (ValueError, TypeError):
            age_days = None

    age_status = determine_age_status(
        record,
        age_days,
    )

    size_status = determine_size_status(
        record
    )

    status = determine_overall_status(
        age_status,
        size_status,
        record,
    )

    result = dict(record)

    result.update(
        {
            "file_name": file_name,
            "file_type": file_type,
            "category": category,
            "file_size_bytes": size_bytes,
            "file_size_mb": round(
                size_bytes / (1024 ** 2),
                2,
            ),
            "age_in_days": (
                round(age_days, 2)
                if age_days is not None
                else None
            ),
            "age_status": age_status,
            "size_status": size_status,
            "status": status,
        }
    )

    return result


# ============================================================
# DYNAMODB
# ============================================================

def get_dynamodb_table():
    """
    Get metadata table.
    """

    return dynamodb_resource.Table(
        DYNAMODB_TABLE
    )


@st.cache_data(ttl=30, show_spinner=False)
def load_dynamodb_metadata() -> List[Dict[str, Any]]:
    """
    Load all metadata from DynamoDB.

    Handles pagination.
    """

    table = get_dynamodb_table()

    records: List[Dict[str, Any]] = []

    scan_kwargs: Dict[str, Any] = {}

    while True:

        response = table.scan(
            **scan_kwargs
        )

        items = response.get(
            "Items",
            [],
        )

        for item in items:
            records.append(
                normalize_record(item)
            )

        last_key = response.get(
            "LastEvaluatedKey"
        )

        if not last_key:
            break

        scan_kwargs[
            "ExclusiveStartKey"
        ] = last_key

    return records


# ============================================================
# S3
# ============================================================

def upload_file_to_s3(
    uploaded_file,
) -> Dict[str, Any]:
    """
    Upload file directly to raw/ in S3.

    Lambda will process the raw object.
    """

    file_name = uploaded_file.name

    safe_name = os.path.basename(
        file_name
    )

    s3_key = (
        RAW_PREFIX + safe_name
    )

    file_size = uploaded_file.size

    if file_size > MAX_UPLOAD_MB * 1024 * 1024:
        raise ValueError(
            f"File exceeds the {MAX_UPLOAD_MB} MB limit."
        )

    uploaded_file.seek(0)

    s3_client.upload_fileobj(
        uploaded_file,
        S3_BUCKET,
        s3_key,
        ExtraArgs={
            "ContentType": (
                uploaded_file.type
                or "application/octet-stream"
            )
        },
    )

    return {
        "file_name": safe_name,
        "s3_key": s3_key,
        "size": file_size,
    }


def download_s3_object(
    s3_key: str,
) -> bytes:
    """
    Download actual object from S3.
    """

    response = s3_client.get_object(
        Bucket=S3_BUCKET,
        Key=s3_key,
    )

    return response["Body"].read()


def delete_s3_object(
    s3_key: str,
) -> None:
    """
    Delete actual S3 object.

    Metadata is intentionally NOT deleted automatically.
    """

    s3_client.delete_object(
        Bucket=S3_BUCKET,
        Key=s3_key,
    )


def object_exists(
    s3_key: str,
) -> bool:
    """
    Check whether an S3 object exists.
    """

    try:
        s3_client.head_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
        )

        return True

    except ClientError:
        return False


# ============================================================
# ATHENA
# ============================================================

def run_athena_query(
    query: str,
    timeout_seconds: int = 30,
) -> List[Dict[str, Any]]:
    """
    Execute an Athena query.

    Used for analytics/verification.
    Dashboard does not depend exclusively on Athena.
    """

    response = athena_client.start_query_execution(
        QueryString=query,
        QueryExecutionContext={
            "Database": ATHENA_DATABASE,
        },
        ResultConfiguration={
            "OutputLocation": ATHENA_OUTPUT,
        },
    )

    execution_id = response[
        "QueryExecutionId"
    ]

    start = time.time()

    while True:

        execution = (
            athena_client.get_query_execution(
                QueryExecutionId=execution_id
            )
        )

        state = execution[
            "QueryExecution"
        ][
            "Status"
        ][
            "State"
        ]

        if state == "SUCCEEDED":
            break

        if state in {
            "FAILED",
            "CANCELLED",
        }:
            reason = (
                execution[
                    "QueryExecution"
                ][
                    "Status"
                ].get(
                    "StateChangeReason",
                    "Unknown Athena error",
                )
            )

            raise RuntimeError(
                reason
            )

        if (
            time.time() - start
            > timeout_seconds
        ):
            raise TimeoutError(
                "Athena query timed out."
            )

        time.sleep(0.5)

    result = athena_client.get_query_results(
        QueryExecutionId=execution_id
    )

    rows = result.get(
        "ResultSet",
        {}
    ).get(
        "Rows",
        []
    )

    if not rows:
        return []

    header = [
        col.get("VarCharValue", "")
        for col in rows[0].get(
            "Data",
            []
        )
    ]

    data: List[Dict[str, Any]] = []

    for row in rows[1:]:

        values = [
            col.get(
                "VarCharValue",
                "",
            )
            for col in row.get(
                "Data",
                []
            )
        ]

        while len(values) < len(header):
            values.append("")

        data.append(
            dict(
                zip(
                    header,
                    values,
                )
            )
        )

    return data


@st.cache_data(ttl=60, show_spinner=False)
def get_athena_summary() -> Dict[str, Any]:
    """
    Lightweight Athena verification query.

    If Athena has a problem, dashboard continues using DynamoDB.
    """

    query = f"""
    SELECT
        COUNT(*) AS total_files,
        COALESCE(SUM(file_size_bytes), 0) AS total_bytes
    FROM "{ATHENA_DATABASE}"."{ATHENA_TABLE}"
    """

    try:
        rows = run_athena_query(
            query
        )

        if not rows:
            return {
                "available": False
            }

        row = rows[0]

        return {
            "available": True,
            "total_files": row.get(
                "total_files",
                "0",
            ),
            "total_bytes": row.get(
                "total_bytes",
                "0",
            ),
        }

    except Exception:
        return {
            "available": False
        }


# ============================================================
# DATAFRAME
# ============================================================

def records_to_dataframe(
    records: List[Dict[str, Any]],
) -> pd.DataFrame:

    if not records:
        return pd.DataFrame()

    rows = []

    for record in records:

        rows.append(
            {
                "File Name": record.get(
                    "file_name",
                    "Unknown",
                ),
                "Type": record.get(
                    "file_type",
                    "",
                ),
                "Category": record.get(
                    "category",
                    "Others",
                ),
                "Size": format_size(
                    record.get(
                        "file_size_bytes",
                        0,
                    )
                ),
                "Uploaded": format_upload_time(
                    record.get(
                        "upload_time"
                    )
                ),
                "Age": (
                    f"{record['age_in_days']:.2f} days"
                    if record.get(
                        "age_in_days"
                    ) is not None
                    else "—"
                ),
                "Age Status": record.get(
                    "age_status",
                    "UNKNOWN",
                ),
                "Size Status": record.get(
                    "size_status",
                    "UNKNOWN",
                ),
                "Status": record.get(
                    "status",
                    "UNKNOWN",
                ),
            }
        )

    return pd.DataFrame(rows)


def format_upload_time(
    value: Any,
) -> str:

    dt = parse_datetime(value)

    if dt is None:
        return "—"

    return dt.astimezone().strftime(
        "%d %b %Y, %H:%M"
    )


# ============================================================
# DASHBOARD CALCULATIONS
# ============================================================

def calculate_dashboard_stats(
    records: List[Dict[str, Any]],
) -> Dict[str, Any]:

    total_files = len(records)

    documents = sum(
        1
        for r in records
        if r.get("category") == "Documents"
    )

    images = sum(
        1
        for r in records
        if r.get("category") == "Images"
    )

    videos = sum(
        1
        for r in records
        if r.get("category") == "Videos"
    )

    old_files = sum(
        1
        for r in records
        if r.get("age_status")
        == "OLD_FILE"
    )

    large_files = sum(
        1
        for r in records
        if r.get("size_status")
        == "LARGE_FILE"
    )

    normal_files = sum(
        1
        for r in records
        if r.get("status")
        == "NORMAL"
    )

    total_bytes = sum(
        int(
            r.get(
                "file_size_bytes",
                0,
            )
            or 0
        )
        for r in records
    )

    last_file = None

    if records:

        sorted_records = sorted(
            records,
            key=lambda r: (
                parse_datetime(
                    r.get("upload_time")
                )
                or datetime.min.replace(
                    tzinfo=timezone.utc
                )
            ),
            reverse=True,
        )

        last_file = sorted_records[0]

    return {
        "total_files": total_files,
        "documents": documents,
        "images": images,
        "videos": videos,
        "old_files": old_files,
        "large_files": large_files,
        "normal_files": normal_files,
        "total_bytes": total_bytes,
        "last_file": last_file,
    }


# ============================================================
# SIDEBAR
# ============================================================

if "page" not in st.session_state:
    st.session_state.page = "Overview"


with st.sidebar:

    st.markdown(
        "## ☁️ Smart Cloud"
    )

    st.caption(
        "File Management Platform"
    )

    st.divider()

    st.caption("NAVIGATION")

    if st.button(
        "▣  Overview",
        use_container_width=True,
    ):
        st.session_state.page = "Overview"
        st.rerun()

    if st.button(
        "▤  Files & Analytics",
        use_container_width=True,
    ):
        st.session_state.page = (
            "Files & Analytics"
        )
        st.rerun()

    if st.button(
        "⚙  Settings",
        use_container_width=True,
    ):
        st.session_state.page = "Settings"
        st.rerun()

    st.divider()

    st.caption("PIPELINE")

    st.write(
        "☁️ S3"
    )

    st.write(
        "⚡ Lambda"
    )

    st.write(
        "🗄 DynamoDB"
    )

    st.write(
        "🔎 Athena"
    )

    st.write(
        "📊 Streamlit"
    )

    st.divider()

    st.caption(
        f"Region: {AWS_REGION}"
    )

    st.caption(
        f"Bucket: {S3_BUCKET}"
    )


# ============================================================
# LOAD DATA
# ============================================================

try:

    records = load_dynamodb_metadata()

except Exception as exc:

    records = []

    st.error(
        "Unable to load metadata from DynamoDB."
    )

    st.code(
        str(exc)
    )


stats = calculate_dashboard_stats(
    records
)


# ============================================================
# TOP HEADER
# ============================================================

header_left, header_right = st.columns(
    [5, 2]
)

with header_left:

    st.title(
        "☁️ Smart Cloud File Manager"
    )

    st.caption(
        "S3 → Lambda → DynamoDB → Athena → Streamlit"
    )

with header_right:

    refresh_col, status_col = st.columns(
        [1, 1]
    )

    with refresh_col:

        if st.button(
            "↻ Refresh Data",
            use_container_width=True,
        ):

            load_dynamodb_metadata.clear()
            get_athena_summary.clear()

            st.session_state[
                "refresh_message"
            ] = True

            st.rerun()

    with status_col:

        st.success(
            "● SYSTEM ONLINE"
        )


if st.session_state.pop(
    "refresh_message",
    False,
):

    st.success(
        "Data refreshed successfully."
    )


st.caption(
    "Last updated: "
    + datetime.now().astimezone().strftime(
        "%d %b %Y, %H:%M:%S %Z"
    )
)


# ============================================================
# OVERVIEW PAGE
# ============================================================

if st.session_state.page == "Overview":

    # --------------------------------------------------------
    # UPLOAD + QUICK SUMMARY
    # --------------------------------------------------------

    upload_col, summary_col = st.columns(
        [1.15, 1.85],
        gap="medium",
    )

    with upload_col:

        st.subheader(
            "☁️ Cloud Upload Center"
        )

        st.caption(
            "Upload files directly to S3 raw/"
        )

        uploaded_files = st.file_uploader(
            "Drag & drop files here or choose files",
            accept_multiple_files=True,
            key="cloud_uploader",
        )

        st.caption(
            f"Maximum file size: "
            f"{MAX_UPLOAD_MB} MB per file"
        )

        if uploaded_files:

            st.write(
                f"Selected files: "
                f"**{len(uploaded_files)}**"
            )

            for uploaded in uploaded_files:

                st.caption(
                    f"• {uploaded.name} "
                    f"({format_size(uploaded.size)})"
                )

        if st.button(
            "☁️ Upload to S3",
            use_container_width=True,
            disabled=not uploaded_files,
        ):

            successful = []
            failed = []

            progress = st.progress(
                0
            )

            for index, uploaded in enumerate(
                uploaded_files
            ):

                try:

                    result = upload_file_to_s3(
                        uploaded
                    )

                    successful.append(
                        result
                    )

                except Exception as exc:

                    failed.append(
                        (
                            uploaded.name,
                            str(exc),
                        )
                    )

                progress.progress(
                    (index + 1)
                    / len(uploaded_files)
                )

            if successful:

                st.success(
                    f"{len(successful)} file(s) "
                    "uploaded successfully."
                )

                for item in successful:

                    st.caption(
                        f"Uploaded: "
                        f"{item['file_name']} → "
                        f"{item['s3_key']}"
                    )

                st.info(
                    "Lambda will now process the uploaded "
                    "file(s). Click Refresh Data after "
                    "processing completes."
                )

            if failed:

                for file_name, error in failed:

                    st.error(
                        f"{file_name}: {error}"
                    )

    with summary_col:

        st.subheader(
            "Quick Summary"
        )

        summary_1, summary_2, summary_3 = st.columns(
            3
        )

        with summary_1:

            st.metric(
                "Total Files",
                format_number(
                    stats["total_files"]
                ),
            )

        with summary_2:

            st.metric(
                "Total Storage",
                format_size(
                    stats["total_bytes"]
                ),
            )

        with summary_3:

            last_file = stats[
                "last_file"
            ]

            st.metric(
                "Last File",
                (
                    last_file.get(
                        "file_name",
                        "—",
                    )
                    if last_file
                    else "—"
                ),
            )

        summary_4, summary_5, summary_6 = st.columns(
            3
        )

        with summary_4:

            st.metric(
                "Old Files",
                format_number(
                    stats["old_files"]
                ),
            )

        with summary_5:

            st.metric(
                "Large Files",
                format_number(
                    stats["large_files"]
                ),
            )

        with summary_6:

            st.metric(
                "System Status",
                "ONLINE",
            )

    st.divider()

    # --------------------------------------------------------
    # KPI CARDS
    # --------------------------------------------------------

    st.subheader(
        "Cloud File Overview"
    )

    k1, k2, k3, k4, k5, k6 = st.columns(
        6,
        gap="small",
    )

    with k1:

        st.metric(
            "☁️ Total Files",
            format_number(
                stats["total_files"]
            ),
            "—",
        )

    with k2:

        st.metric(
            "📄 Documents",
            format_number(
                stats["documents"]
            ),
            "—",
        )

    with k3:

        st.metric(
            "🖼 Images",
            format_number(
                stats["images"]
            ),
            "—",
        )

    with k4:

        st.metric(
            "🎬 Videos",
            format_number(
                stats["videos"]
            ),
            "—",
        )

    with k5:

        st.metric(
            "⚠️ Old Files",
            format_number(
                stats["old_files"]
            ),
            "—",
        )

    with k6:

        st.metric(
            "💾 Storage",
            format_size(
                stats["total_bytes"]
            ),
            "—",
        )

    st.divider()

    # --------------------------------------------------------
    # CATEGORY + TYPE
    # --------------------------------------------------------

    chart_left, chart_right = st.columns(
        2,
        gap="medium",
    )

    with chart_left:

        st.subheader(
            "Files by Category"
        )

        category_data = pd.DataFrame(
            {
                "Category": [
                    "Documents",
                    "Images",
                    "Videos",
                    "Others",
                ],
                "Count": [
                    stats["documents"],
                    stats["images"],
                    stats["videos"],
                    stats["total_files"]
                    - stats["documents"]
                    - stats["images"]
                    - stats["videos"],
                ],
            }
        )

        category_data = category_data[
            category_data["Count"] > 0
        ]

        if category_data.empty:

            st.info(
                "No category data available."
            )

        else:

            st.bar_chart(
                category_data.set_index(
                    "Category"
                )
            )

            total = stats[
                "total_files"
            ]

            if total > 0:

                display_category = (
                    category_data.copy()
                )

                display_category[
                    "Percentage"
                ] = (
                    display_category["Count"]
                    / total
                    * 100
                ).round(1).astype(str) + "%"

                st.dataframe(
                    display_category,
                    use_container_width=True,
                    hide_index=True,
                )

    with chart_right:

        st.subheader(
            "Top File Types"
        )

        if records:

            type_series = (
                pd.Series(
                    [
                        r.get(
                            "file_type",
                            "unknown",
                        )
                        or "unknown"
                        for r in records
                    ]
                )
                .str.lower()
                .value_counts()
                .head(5)
            )

            type_data = (
                type_series
                .rename_axis("Type")
                .reset_index(
                    name="Count"
                )
            )

            st.bar_chart(
                type_data.set_index(
                    "Type"
                )
            )

            st.dataframe(
                type_data,
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.info(
                "No file type data available."
            )

    st.divider()

    # --------------------------------------------------------
    # FILE HEALTH
    # --------------------------------------------------------

    st.subheader(
        "File Health"
    )

    h1, h2, h3 = st.columns(
        3,
        gap="medium",
    )

    with h1:

        st.metric(
            "✓ Normal",
            format_number(
                stats["normal_files"]
            ),
        )

    with h2:

        st.metric(
            "⚠ Old Files",
            format_number(
                stats["old_files"]
            ),
        )

    with h3:

        st.metric(
            "⬆ Large Files",
            format_number(
                stats["large_files"]
            ),
        )

    st.divider()

    # --------------------------------------------------------
    # RECENT FILES
    # --------------------------------------------------------

    st.subheader(
        "Recent Cloud Files"
    )

    if records:

        recent_records = sorted(
            records,
            key=lambda r: (
                parse_datetime(
                    r.get("upload_time")
                )
                or datetime.min.replace(
                    tzinfo=timezone.utc
                )
            ),
            reverse=True,
        )[:10]

        recent_df = records_to_dataframe(
            recent_records
        )

        st.dataframe(
            recent_df,
            use_container_width=True,
            hide_index=True,
            height=330,
        )

    else:

        st.info(
            "No cloud files found yet."
        )

    st.divider()

    # --------------------------------------------------------
    # SYSTEM INFORMATION
    # --------------------------------------------------------

    st.subheader(
        "System Information"
    )

    s1, s2, s3, s4 = st.columns(
        4
    )

    with s1:

        st.caption(
            "S3 Bucket"
        )

        st.code(
            S3_BUCKET
        )

    with s2:

        st.caption(
            "Upload Path"
        )

        st.code(
            RAW_PREFIX
        )

    with s3:

        st.caption(
            "Database"
        )

        st.code(
            ATHENA_DATABASE
        )

    with s4:

        st.caption(
            "Pipeline"
        )

        st.code(
            "S3 → Lambda → DynamoDB → Athena"
        )


# ============================================================
# FILES & ANALYTICS PAGE
# ============================================================

elif st.session_state.page == "Files & Analytics":

    st.subheader(
        "Files & Analytics"
    )

    st.caption(
        "Search, filter and manage actual cloud file metadata."
    )

    # --------------------------------------------------------
    # FILTERS
    # --------------------------------------------------------

    filter_1, filter_2, filter_3, filter_4 = st.columns(
        4
    )

    with filter_1:

        search_text = st.text_input(
            "Search filename",
            placeholder="Type filename...",
        )

    with filter_2:

        category_filter = st.selectbox(
            "Category",
            [
                "All",
                "Documents",
                "Images",
                "Videos",
                "Others",
            ],
        )

    with filter_3:

        type_values = sorted(
            {
                str(
                    r.get(
                        "file_type",
                        "",
                    )
                ).lower()
                for r in records
                if r.get(
                    "file_type"
                )
            }
        )

        type_filter = st.selectbox(
            "Type",
            ["All"] + type_values,
        )

    with filter_4:

        status_filter = st.selectbox(
            "Status",
            [
                "All",
                "NORMAL",
                "OLD_FILE",
                "LARGE_FILE",
            ],
        )

    age_filter = st.selectbox(
        "Age",
        [
            "All",
            "New files",
            "Old files",
        ],
    )

    size_filter = st.selectbox(
        "Size",
        [
            "All",
            "Normal size",
            "Large files",
        ],
    )

    # --------------------------------------------------------
    # APPLY FILTERS
    # --------------------------------------------------------

    filtered_records = list(
        records
    )

    if search_text:

        search_lower = (
            search_text.lower()
        )

        filtered_records = [
            r
            for r in filtered_records
            if search_lower
            in str(
                r.get(
                    "file_name",
                    "",
                )
            ).lower()
        ]

    if category_filter != "All":

        filtered_records = [
            r
            for r in filtered_records
            if r.get(
                "category"
            ) == category_filter
        ]

    if type_filter != "All":

        filtered_records = [
            r
            for r in filtered_records
            if str(
                r.get(
                    "file_type",
                    "",
                )
            ).lower()
            == type_filter
        ]

    if status_filter != "All":

        filtered_records = [
            r
            for r in filtered_records
            if r.get(
                "status"
            ) == status_filter
        ]

    if age_filter == "New files":

        filtered_records = [
            r
            for r in filtered_records
            if r.get(
                "age_status"
            ) == "NEW_FILE"
        ]

    elif age_filter == "Old files":

        filtered_records = [
            r
            for r in filtered_records
            if r.get(
                "age_status"
            ) == "OLD_FILE"
        ]

    if size_filter == "Normal size":

        filtered_records = [
            r
            for r in filtered_records
            if r.get(
                "size_status"
            ) == "NORMAL"
        ]

    elif size_filter == "Large files":

        filtered_records = [
            r
            for r in filtered_records
            if r.get(
                "size_status"
            ) == "LARGE_FILE"
        ]

    # --------------------------------------------------------
    # FILTERED SUMMARY
    # --------------------------------------------------------

    filtered_stats = calculate_dashboard_stats(
        filtered_records
    )

    a1, a2, a3, a4 = st.columns(
        4
    )

    with a1:

        st.metric(
            "Matching Files",
            format_number(
                len(filtered_records)
            ),
        )

    with a2:

        st.metric(
            "Storage",
            format_size(
                filtered_stats[
                    "total_bytes"
                ]
            ),
        )

    with a3:

        st.metric(
            "Old",
            format_number(
                filtered_stats[
                    "old_files"
                ]
            ),
        )

    with a4:

        st.metric(
            "Large",
            format_number(
                filtered_stats[
                    "large_files"
                ]
            ),
        )

    st.divider()

    # --------------------------------------------------------
    # FILE TABLE
    # --------------------------------------------------------

    if not filtered_records:

        st.info(
            "No files match the selected filters."
        )

    else:

        display_records = sorted(
            filtered_records,
            key=lambda r: (
                parse_datetime(
                    r.get("upload_time")
                )
                or datetime.min.replace(
                    tzinfo=timezone.utc
                )
            ),
            reverse=True,
        )

        files_df = records_to_dataframe(
            display_records
        )

        st.dataframe(
            files_df,
            use_container_width=True,
            hide_index=True,
            height=450,
        )

        st.caption(
            f"Showing {len(display_records)} file(s)."
        )

    st.divider()

    # --------------------------------------------------------
    # FILE ACTIONS
    # --------------------------------------------------------

    st.subheader(
        "File Actions"
    )

    if filtered_records:

        action_options = []

        for record in filtered_records:

            file_name = record.get(
                "file_name",
                "Unknown",
            )

            file_id = record.get(
                "file_id",
                "",
            )

            label = (
                f"{file_name} "
                f"— {file_id}"
            )

            action_options.append(
                (
                    label,
                    record,
                )
            )

        selected_label = st.selectbox(
            "Select a file",
            [
                item[0]
                for item in action_options
            ],
        )

        selected_record = next(
            (
                item[1]
                for item in action_options
                if item[0]
                == selected_label
            ),
            None,
        )

        if selected_record:

            action_left, action_right = st.columns(
                2
            )

            with action_left:

                file_s3_key = selected_record.get(
                    "s3_key"
                )

                if not file_s3_key:

                    original_key = selected_record.get(
                        "original_s3_key"
                    )

                    file_s3_key = original_key

                if file_s3_key:

                    try:

                        file_bytes = (
                            download_s3_object(
                                file_s3_key
                            )
                        )

                        st.download_button(
                            "⬇ Download File",
                            data=file_bytes,
                            file_name=selected_record.get(
                                "file_name",
                                "download",
                            ),
                            mime=(
                                "application/octet-stream"
                            ),
                            use_container_width=True,
                        )

                    except Exception as exc:

                        st.warning(
                            "Unable to download this "
                            "S3 object."
                        )

                        st.caption(
                            str(exc)
                        )

            with action_right:

                st.warning(
                    "Delete removes the actual S3 object. "
                    "DynamoDB metadata is not automatically "
                    "deleted."
                )

                confirm_delete = st.checkbox(
                    "I confirm that I want to delete this S3 object.",
                    key=(
                        "confirm_delete_"
                        + str(
                            selected_record.get(
                                "file_id",
                                "",
                            )
                        )
                    ),
                )

                if st.button(
                    "🗑 Delete S3 Object",
                    use_container_width=True,
                    disabled=not confirm_delete,
                ):

                    delete_key = (
                        selected_record.get(
                            "s3_key"
                        )
                        or selected_record.get(
                            "original_s3_key"
                        )
                    )

                    if delete_key:

                        try:

                            delete_s3_object(
                                delete_key
                            )

                            st.success(
                                "S3 object deleted successfully."
                            )

                            load_dynamodb_metadata.clear()

                            st.rerun()

                        except Exception as exc:

                            st.error(
                                "Delete failed."
                            )

                            st.caption(
                                str(exc)
                            )

    st.divider()

    # --------------------------------------------------------
    # ANALYTICS
    # --------------------------------------------------------

    st.subheader(
        "Analytics"
    )

    analytics_left, analytics_right = st.columns(
        2
    )

    with analytics_left:

        st.write(
            "Files by Category"
        )

        if filtered_records:

            category_counts = (
                pd.Series(
                    [
                        r.get(
                            "category",
                            "Others",
                        )
                        for r in filtered_records
                    ]
                )
                .value_counts()
            )

            category_df = (
                category_counts
                .rename_axis("Category")
                .reset_index(
                    name="Count"
                )
            )

            st.bar_chart(
                category_df.set_index(
                    "Category"
                )
            )

        else:

            st.info(
                "No data available."
            )

    with analytics_right:

        st.write(
            "Files by Type"
        )

        if filtered_records:

            type_counts = (
                pd.Series(
                    [
                        r.get(
                            "file_type",
                            "unknown",
                        )
                        for r in filtered_records
                    ]
                )
                .value_counts()
                .head(10)
            )

            type_df = (
                type_counts
                .rename_axis("Type")
                .reset_index(
                    name="Count"
                )
            )

            st.bar_chart(
                type_df.set_index(
                    "Type"
                )
            )

        else:

            st.info(
                "No data available."
            )


# ============================================================
# SETTINGS PAGE
# ============================================================

elif st.session_state.page == "Settings":

    st.subheader(
        "⚙️ System Settings & Configuration"
    )

    st.caption(
        "Current application configuration. "
        "These values are informational unless explicitly "
        "changed in the environment/project configuration."
    )

    # --------------------------------------------------------
    # AWS CONFIGURATION
    # --------------------------------------------------------

    st.subheader(
        "AWS Configuration"
    )

    config_data = pd.DataFrame(
        [
            {
                "Configuration": "AWS Region",
                "Value": AWS_REGION,
            },
            {
                "Configuration": "S3 Bucket",
                "Value": S3_BUCKET,
            },
            {
                "Configuration": "Upload Prefix",
                "Value": RAW_PREFIX,
            },
            {
                "Configuration": "Maximum Upload Size",
                "Value": f"{MAX_UPLOAD_MB} MB",
            },
            {
                "Configuration": "DynamoDB Table",
                "Value": DYNAMODB_TABLE,
            },
            {
                "Configuration": "Athena Database",
                "Value": ATHENA_DATABASE,
            },
            {
                "Configuration": "Athena Table",
                "Value": ATHENA_TABLE,
            },
            {
                "Configuration": "Athena Results",
                "Value": ATHENA_OUTPUT,
            },
        ]
    )

    st.dataframe(
        config_data,
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    # --------------------------------------------------------
    # PIPELINE
    # --------------------------------------------------------

    st.subheader(
        "Cloud Pipeline"
    )

    p1, p2, p3, p4, p5 = st.columns(
        5
    )

    with p1:

        st.success(
            "☁️ S3\n\nConnected"
        )

    with p2:

        st.success(
            "⚡ Lambda\n\nConfigured"
        )

    with p3:

        st.success(
            "🗄 DynamoDB\n\nConnected"
        )

    with p4:

        athena_status = get_athena_summary()

        if athena_status.get(
            "available"
        ):

            st.success(
                "🔎 Athena\n\nAvailable"
            )

        else:

            st.warning(
                "🔎 Athena\n\nCheck required"
            )

    with p5:

        st.success(
            "📊 Streamlit\n\nRunning"
        )

    st.divider()

    # --------------------------------------------------------
    # ATHENA TEST
    # --------------------------------------------------------

    st.subheader(
        "Athena Status"
    )

    if st.button(
        "🔎 Test Athena Connection",
        use_container_width=False,
    ):

        with st.spinner(
            "Testing Athena..."
        ):

            result = get_athena_summary()

        if result.get(
            "available"
        ):

            st.success(
                "Athena connection is working."
            )

        else:

            st.warning(
                "Athena query could not be completed. "
                "The dashboard can continue using DynamoDB "
                "metadata."
            )

    st.divider()

    # --------------------------------------------------------
    # APPLICATION INFORMATION
    # --------------------------------------------------------

    st.subheader(
        "Application Information"
    )

    info_left, info_right = st.columns(
        2
    )

    with info_left:

        st.write(
            "**Smart Cloud File Manager**"
        )

        st.caption(
            "Enterprise-style cloud file analytics dashboard."
        )

        st.caption(
            "Data source: actual AWS resources."
        )

    with info_right:

        st.write(
            "**Current Metadata**"
        )

        st.metric(
            "Files in Dashboard",
            format_number(
                len(records)
            ),
        )

        st.metric(
            "Storage Used",
            format_size(
                stats["total_bytes"]
            ),
        )

    st.divider()

    # --------------------------------------------------------
    # COST NOTE
    # --------------------------------------------------------

    # st.info(
    #     "This dashboard uses the AWS resources already "
    #     "configured for the project. No additional paid "
    #     "dashboard service is required."
    # )