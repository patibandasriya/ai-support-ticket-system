import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


# --------------------------------------------------
# FastAPI application
# --------------------------------------------------

app = FastAPI(
    title="AI Support Ticket Analyst",
    description="Natural-language support ticket analytics API",
    version="1.0.0",
)


# --------------------------------------------------
# Paths
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"


# --------------------------------------------------
# Request model
# --------------------------------------------------

class QueryRequest(BaseModel):
    question: str


# --------------------------------------------------
# Load ticket data
# --------------------------------------------------

def load_ticket_data() -> pd.DataFrame:
    """
    Load the first CSV file from the data folder.
    """

    csv_files = list(DATA_DIR.glob("*.csv"))

    if not csv_files:
        raise FileNotFoundError(
            f"No CSV file found inside: {DATA_DIR}"
        )

    data = pd.read_csv(csv_files[0])

    # Normalize column names
    data.columns = [
    str(col).strip().lower().replace(" ", "_")
    for col in data.columns
]

    return data


try:
    tickets = load_ticket_data()
except Exception as error:
    print("Data loading error:", error)
    tickets = pd.DataFrame()


# --------------------------------------------------
# Helper functions
# --------------------------------------------------

def clean_value(value: Any) -> Any:
    """
    Convert pandas values into JSON-safe values.
    """

    if pd.isna(value):
        return None

    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass

    return value


def find_column(
    data: pd.DataFrame,
    possible_names: List[str]
) -> Optional[str]:
    """
    Find the first matching column.
    """

    for name in possible_names:
        if name in data.columns:
            return name

    return None


def normalize_text(value: Any) -> str:
    """
    Convert a value into lowercase text.
    """

    if value is None:
        return ""

    return str(value).strip().lower()


def get_status_column(data: pd.DataFrame) -> Optional[str]:
    return find_column(
        data,
        [
            "status",
            "ticket_status",
            "state",
        ],
    )


def get_priority_column(data: pd.DataFrame) -> Optional[str]:
    return find_column(
        data,
        [
            "priority",
            "ticket_priority",
            "severity",
        ],
    )


def get_category_column(data: pd.DataFrame) -> Optional[str]:
    return find_column(
        data,
        [
            "category",
            "ticket_category",
            "type",
            "issue_type",
        ],
    )


def get_resolution_time_column(data: pd.DataFrame) -> Optional[str]:
    return find_column(
        data,
        [
            "resolution_time",
            "resolution_time_hours",
            "resolution_hours",
            "time_to_resolution",
            "hours_to_resolve",
        ],
    )


def get_id_column(data: pd.DataFrame) -> Optional[str]:
    return find_column(
        data,
        [
            "ticket_id",
            "id",
            "case_id",
        ],
    )


def dataframe_to_records(data: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Convert DataFrame rows into JSON-safe dictionaries.
    """

    records = data.to_dict(orient="records")

    cleaned_records = []

    for record in records:
        cleaned_record = {
            str(key): clean_value(value)
            for key, value in record.items()
        }
        cleaned_records.append(cleaned_record)

    return cleaned_records


# --------------------------------------------------
# Natural-language question interpreter
# --------------------------------------------------

def interpret_question(question: str) -> Dict[str, Any]:
    """
    Convert a natural-language question into a simple operation.
    """

    text = question.lower().strip()

    specification: Dict[str, Any] = {
        "operation": "count",
        "status": None,
        "priority": None,
        "category": None,
        "limit": 10,
        "group_by": None,
        "sort_order": "descending",
    }

    # Detect status
    if "unresolved" in text:
        specification["status"] = "open"
    elif "open" in text:
        specification["status"] = "open"
    elif "resolved" in text or "closed" in text:
        specification["status"] = "resolved"
    elif "escalated" in text:
        specification["status"] = "escalated"
    elif "pending" in text:
        specification["status"] = "pending"

    # Detect priority
    for priority in ["critical", "high", "medium", "low"]:
        if priority in text:
            specification["priority"] = priority
            break

    # Detect category
    for category in ["billing", "technical", "general", "account", "login"]:
        if category in text:
            specification["category"] = category
            break

    # Detect limit
    number_match = re.search(
        r"(?:top|first|show|list|give me)\s+(\d+)",
        text
    )

    if number_match:
        specification["limit"] = int(number_match.group(1))

    # Detect grouping
    if "by category" in text or "per category" in text:
        specification["group_by"] = "category"
        specification["operation"] = "group"
    elif "by priority" in text or "per priority" in text:
        specification["group_by"] = "priority"
        specification["operation"] = "group"
    elif "by status" in text or "per status" in text:
        specification["group_by"] = "status"
        specification["operation"] = "group"

    # Detect list questions
    if any(word in text for word in [
        "show",
        "list",
        "display",
        "give me",
    ]):
        specification["operation"] = "list"

    # Detect average questions
    if any(word in text for word in [
        "average",
        "mean",
        "avg",
    ]):
        specification["operation"] = "average"

    # Detect lowest/highest
    if "lowest" in text or "smallest" in text:
        specification["sort_order"] = "ascending"

    if "highest" in text or "largest" in text:
        specification["sort_order"] = "descending"

    # Detect explicit count questions
    if any(word in text for word in [
        "how many",
        "count",
        "number of",
    ]):
        specification["operation"] = "count"

    return specification


# --------------------------------------------------
# Apply filters
# --------------------------------------------------

def apply_filters(
    data: pd.DataFrame,
    specification: Dict[str, Any]
) -> pd.DataFrame:
    """
    Apply status, priority, and category filters.
    """

    filtered = data.copy()

    status_column = get_status_column(filtered)
    priority_column = get_priority_column(filtered)
    category_column = get_category_column(filtered)

    status_value = specification.get("status")
    priority_value = specification.get("priority")
    category_value = specification.get("category")

    if status_column and status_value:
        status_series = filtered[status_column].astype(str).str.lower()

        if status_value == "open":
            filtered = filtered[
                status_series.isin([
                    "open",
                    "opened",
                    "unresolved",
                    "pending",
                ])
            ]
        else:
            filtered = filtered[
                status_series == status_value.lower()
            ]

    if priority_column and priority_value:
        filtered = filtered[
            filtered[priority_column]
            .astype(str)
            .str.lower()
            == priority_value.lower()
        ]

    if category_column and category_value:
        filtered = filtered[
            filtered[category_column]
            .astype(str)
            .str.lower()
            == category_value.lower()
        ]

    return filtered


# --------------------------------------------------
# Count operation
# --------------------------------------------------

def count_tickets(
    data: pd.DataFrame,
    specification: Dict[str, Any]
) -> Dict[str, Any]:
    filtered = apply_filters(data, specification)

    return {
        "operation": "count",
        "count": int(len(filtered)),
        "filters": {
            "status": specification.get("status"),
            "priority": specification.get("priority"),
            "category": specification.get("category"),
        },
    }


# --------------------------------------------------
# List operation
# --------------------------------------------------

def list_tickets(
    data: pd.DataFrame,
    specification: Dict[str, Any]
) -> Dict[str, Any]:
    filtered = apply_filters(data, specification)

    limit = int(specification.get("limit", 10))
    result = filtered.head(limit)

    return {
        "operation": "list",
        "count": int(len(filtered)),
        "returned": int(len(result)),
        "tickets": dataframe_to_records(result),
        "filters": {
            "status": specification.get("status"),
            "priority": specification.get("priority"),
            "category": specification.get("category"),
        },
    }


# --------------------------------------------------
# Group operation
# --------------------------------------------------

def group_tickets(
    data: pd.DataFrame,
    specification: Dict[str, Any]
) -> Dict[str, Any]:
    filtered = apply_filters(data, specification)

    group_name = specification.get("group_by")

    column_map = {
        "status": get_status_column(filtered),
        "priority": get_priority_column(filtered),
        "category": get_category_column(filtered),
    }

    group_column = column_map.get(group_name)

    if not group_column:
        return {
            "operation": "group",
            "message": f"Column for grouping by '{group_name}' was not found.",
            "groups": [],
        }

    grouped = (
        filtered[group_column]
        .fillna("Unknown")
        .astype(str)
        .value_counts()
        .reset_index()
    )

    grouped.columns = ["group", "count"]

    return {
        "operation": "group",
        "group_by": group_name,
        "groups": dataframe_to_records(grouped),
    }


# --------------------------------------------------
# Average operation
# --------------------------------------------------

def average_tickets(
    data: pd.DataFrame,
    specification: Dict[str, Any]
) -> Dict[str, Any]:
    filtered = apply_filters(data, specification)

    resolution_column = get_resolution_time_column(filtered)

    if not resolution_column:
        numeric_columns = filtered.select_dtypes(
            include="number"
        ).columns.tolist()

        if not numeric_columns:
            return {
                "operation": "average",
                "message": "No numeric resolution-time column was found.",
            }

        resolution_column = numeric_columns[0]

    values = pd.to_numeric(
        filtered[resolution_column],
        errors="coerce"
    ).dropna()

    if len(values) == 0:
        return {
            "operation": "average",
            "message": "No numeric values available for calculating average.",
        }

    return {
        "operation": "average",
        "column": resolution_column,
        "average": round(float(values.mean()), 2),
        "minimum": round(float(values.min()), 2),
        "maximum": round(float(values.max()), 2),
        "count": int(len(values)),
    }


# --------------------------------------------------
# Anomaly detection
# --------------------------------------------------

def detect_anomalies(data: pd.DataFrame) -> Dict[str, Any]:
    """
    Detect simple support-ticket anomalies.
    """

    if data.empty:
        return {
            "total_anomalies": 0,
            "anomalies": [],
        }

    anomalies = []

    status_column = get_status_column(data)
    priority_column = get_priority_column(data)
    resolution_column = get_resolution_time_column(data)

    # High or critical unresolved tickets
    if status_column and priority_column:
        status_values = data[status_column].astype(str).str.lower()
        priority_values = data[priority_column].astype(str).str.lower()

        high_priority_open = data[
            status_values.isin([
                "open",
                "unresolved",
                "pending",
            ])
            & priority_values.isin([
                "high",
                "critical",
            ])
        ]

        if not high_priority_open.empty:
            anomalies.append({
                "type": "high_priority_unresolved",
                "description": (
                    "High or critical priority tickets are still unresolved."
                ),
                "count": int(len(high_priority_open)),
                "tickets": dataframe_to_records(
                    high_priority_open.head(20)
                ),
            })

    # Very large resolution times
    if resolution_column:
        numeric_values = pd.to_numeric(
            data[resolution_column],
            errors="coerce"
        )

        valid_values = numeric_values.dropna()

        if len(valid_values) >= 3:
            threshold = valid_values.mean() + (
                2 * valid_values.std()
            )

            slow_tickets = data[
                numeric_values > threshold
            ]

            if not slow_tickets.empty:
                anomalies.append({
                    "type": "unusually_long_resolution",
                    "description": (
                        "Some tickets have unusually long resolution times."
                    ),
                    "count": int(len(slow_tickets)),
                    "threshold": round(float(threshold), 2),
                    "tickets": dataframe_to_records(
                        slow_tickets.head(20)
                    ),
                })

    return {
        "total_anomalies": len(anomalies),
        "anomalies": anomalies,
    }


# --------------------------------------------------
# API routes
# --------------------------------------------------

@app.get("/")
def root() -> Dict[str, Any]:
    return {
        "message": "AI Support Ticket Analyst API is running.",
        "docs": "/docs",
        "health": "/health",
        "query": "/query",
        "anomalies": "/anomalies",
    }


@app.get("/health")
def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "rows_loaded": int(len(tickets)),
        "columns": list(tickets.columns),
    }


@app.post("/query")
def query_support_tickets(
    request: QueryRequest
) -> Dict[str, Any]:
    if tickets.empty:
        raise HTTPException(
            status_code=500,
            detail="Ticket data could not be loaded."
        )

    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty."
        )

    specification = interpret_question(question)

    if specification["operation"] == "count":
        result = count_tickets(tickets, specification)

    elif specification["operation"] == "list":
        result = list_tickets(tickets, specification)

    elif specification["operation"] == "group":
        result = group_tickets(tickets, specification)

    elif specification["operation"] == "average":
        result = average_tickets(tickets, specification)

    else:
        result = count_tickets(tickets, specification)

    return {
        "question": question,
        "interpretation": specification,
        "result": result,
        "llm_used": False,
    }


@app.get("/anomalies")
def anomalies() -> Dict[str, Any]:
    if tickets.empty:
        raise HTTPException(
            status_code=500,
            detail="Ticket data could not be loaded."
        )

    return detect_anomalies(tickets)