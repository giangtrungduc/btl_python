import io
import sqlite3
import datetime as dt
from typing import Optional, Tuple, List

import numpy as np
import pandas as pd

from config import DB_PATH

# ---------- Low-level DB ----------
def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    con = get_conn()
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            emp_code TEXT UNIQUE,
            name TEXT NOT NULL,
            department TEXT,
            embedding BLOB NOT NULL,
            created_at TEXT NOT NULL
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            emp_id INTEGER NOT NULL,
            ts TEXT NOT NULL,
            device TEXT,
            FOREIGN KEY(emp_id) REFERENCES employees(id)
        );
    """)
    con.commit()
    con.close()

# ---------- Numpy <-> Blob ----------
def np_to_blob(vec: np.ndarray) -> bytes:
    buf = io.BytesIO()
    np.save(buf, vec.astype(np.float32))
    return buf.getvalue()

def blob_to_np(blob: bytes) -> np.ndarray:
    buf = io.BytesIO(blob)
    buf.seek(0)
    return np.load(buf, allow_pickle=False)

# ---------- Queries ----------
def load_all_embeddings() -> pd.DataFrame:
    con = get_conn()
    df = pd.read_sql_query(
        "SELECT id, emp_code, name, department, embedding FROM employees", con
    )
    con.close()
    if not df.empty:
        df["embedding_vec"] = df["embedding"].apply(blob_to_np)
    else:
        df["embedding_vec"] = []
    return df

def add_employee(emp_code: str, name: str, department: str, embedding: np.ndarray) -> Tuple[bool, str]:
    con = get_conn()
    cur = con.cursor()
    try:
        cur.execute(
            "INSERT INTO employees(emp_code, name, department, embedding, created_at) VALUES(?,?,?,?,?)",
            (emp_code, name, department, np_to_blob(embedding), dt.datetime.now().isoformat()),
        )
        con.commit()
        return True, "Đã thêm nhân viên."
    except sqlite3.IntegrityError:
        return False, "Mã nhân viên đã tồn tại."
    except Exception as e:
        return False, f"Lỗi: {e}"
    finally:
        con.close()

def delete_employee(emp_id: int) -> None:
    con = get_conn()
    cur = con.cursor()
    cur.execute("DELETE FROM employees WHERE id=?", (emp_id,))
    con.commit()
    con.close()

def mark_attendance(emp_id: int, device: str = "desktop") -> None:
    con = get_conn()
    cur = con.cursor()
    cur.execute(
        "INSERT INTO attendance(emp_id, ts, device) VALUES(?,?,?)",
        (emp_id, dt.datetime.now().isoformat(), device),
    )
    con.commit()
    con.close()

def get_attendance(start: Optional[dt.date] = None, end: Optional[dt.date] = None) -> pd.DataFrame:
    con = get_conn()
    q = "SELECT emp_id, ts, device FROM attendance"
    params: List[str] = []
    if start and end:
        q += " WHERE date(ts) BETWEEN ? AND ?"
        params.extend([start.isoformat(), end.isoformat()])
    elif start:
        q += " WHERE date(ts) >= ?"
        params.append(start.isoformat())
    elif end:
        q += " WHERE date(ts) <= ?"
        params.append(end.isoformat())
    df = pd.read_sql_query(q, con, params=params)
    con.close()
    if df.empty:
        return df

    df_emp = load_all_embeddings()
    id2name = df_emp.set_index("id")["name"].to_dict()
    id2dept = df_emp.set_index("id")["department"].to_dict()
    df["name"] = df["emp_id"].map(id2name)
    df["department"] = df["emp_id"].map(id2dept)
    df["ts"] = pd.to_datetime(df["ts"])
    return df

def compute_work_hours(att_df: pd.DataFrame) -> pd.DataFrame:
    if att_df.empty:
        return att_df
    df = att_df.copy()
    df["date"] = df["ts"].dt.date
    agg = (
        df.sort_values(["emp_id", "ts"])
        .groupby(["emp_id", "name", "department", "date"])
        .agg(first_in=("ts", "min"), last_out=("ts", "max"), scans=("ts", "count"))
        .reset_index()
    )
    agg["hours"] = (agg["last_out"] - agg["first_in"]).dt.total_seconds() / 3600.0
    agg.loc[agg["scans"] <= 1, "hours"] = 0.0
    return agg