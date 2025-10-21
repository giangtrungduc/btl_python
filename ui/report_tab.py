import datetime as dt
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from services import db


class ReportTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.configure(padding=10)

        # ===== Bộ lọc ngày =====
        filter_frame = ttk.LabelFrame(self, text="🗓 Bộ lọc thời gian", padding=8)
        filter_frame.pack(fill="x", padx=5, pady=8)

        ttk.Label(filter_frame, text="Từ ngày (YYYY-MM-DD):").pack(side="left")
        self.start_var = tk.StringVar(value=str(dt.date.today().replace(day=1)))
        ttk.Entry(filter_frame, textvariable=self.start_var, width=12).pack(side="left", padx=6)

        ttk.Label(filter_frame, text="Đến ngày (YYYY-MM-DD):").pack(side="left")
        self.end_var = tk.StringVar(value=str(dt.date.today()))
        ttk.Entry(filter_frame, textvariable=self.end_var, width=12).pack(side="left", padx=6)

        ttk.Button(filter_frame, text="📄 Lấy dữ liệu", command=self.load_reports).pack(side="left", padx=6)
        ttk.Button(filter_frame, text="💾 Xuất CSV (ngày)", command=self.export_daily_csv).pack(side="left", padx=6)
        ttk.Button(filter_frame, text="📊 Xuất CSV (tổng)", command=self.export_total_csv).pack(side="left", padx=6)

        # ===== Bảng công theo ngày =====
        daily_frame = ttk.LabelFrame(self, text="📅 Công theo ngày (mỗi nhân viên mỗi ngày)", padding=8)
        daily_frame.pack(fill="both", expand=True, padx=5, pady=6)

        cols_daily = ("emp_id", "name", "department", "date", "first_in", "last_out", "scans", "hours")
        self.tree_daily = ttk.Treeview(daily_frame, columns=cols_daily, show="headings", height=10)
        for c in cols_daily:
            self.tree_daily.heading(c, text=c)
            self.tree_daily.column(c, width=110, anchor="center")
        self.tree_daily.pack(fill="x", pady=4)

        # ===== Bảng tổng hợp =====
        total_frame = ttk.LabelFrame(self, text="👤 Tổng hợp theo nhân viên", padding=8)
        total_frame.pack(fill="both", expand=True, padx=5, pady=6)

        cols_total = ("emp_id", "name", "department", "days", "total_hours", "scans")
        self.tree_total = ttk.Treeview(total_frame, columns=cols_total, show="headings", height=10)
        for c in cols_total:
            self.tree_total.heading(c, text=c)
            self.tree_total.column(c, width=120, anchor="center")
        self.tree_total.pack(fill="x", pady=4)

        self._daily_df = None
        self._total_df = None

    # ====== Xử lý dữ liệu ======
    def parse_date(self, s: str):
        try:
            return dt.datetime.strptime(s, "%Y-%m-%d").date()
        except Exception:
            return None

    def load_reports(self):
        s = self.parse_date(self.start_var.get().strip())
        e = self.parse_date(self.end_var.get().strip())
        if s is None or e is None:
            messagebox.showwarning("Sai định dạng", "Ngày phải theo định dạng YYYY-MM-DD.")
            return
        att = db.get_attendance(s, e)
        if att.empty:
            messagebox.showinfo("Thông báo", "Không có dữ liệu trong khoảng ngày đã chọn.")
            self._populate_tree(self.tree_daily, [])
            self._populate_tree(self.tree_total, [])
            return

        daily = db.compute_work_hours(att)
        rows_daily = [
            [int(r["emp_id"]), r["name"], r["department"], str(r["date"]),
             str(r["first_in"]), str(r["last_out"]), int(r["scans"]), round(float(r["hours"]), 2)]
            for _, r in daily.iterrows()
        ]
        self._populate_tree(self.tree_daily, rows_daily)

        total = (
            daily.groupby(["emp_id", "name", "department"]).agg(
                days=("date", "nunique"),
                total_hours=("hours", "sum"),
                scans=("scans", "sum"),
            ).reset_index()
        )
        total["total_hours"] = total["total_hours"].round(2)

        rows_total = [
            [int(r["emp_id"]), r["name"], r["department"],
             int(r["days"]), float(r["total_hours"]), int(r["scans"])]
            for _, r in total.iterrows()
        ]
        self._populate_tree(self.tree_total, rows_total)

        self._daily_df = daily
        self._total_df = total

    def _populate_tree(self, tree: ttk.Treeview, rows):
        for i in tree.get_children():
            tree.delete(i)
        for row in rows:
            tree.insert("", "end", values=row)

    def export_daily_csv(self):
        if self._daily_df is None or self._daily_df.empty:
            messagebox.showwarning("Chú ý", "Không có dữ liệu để xuất.")
            return
        fpath = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not fpath:
            return
        self._daily_df.to_csv(fpath, index=False, encoding="utf-8-sig")
        messagebox.showinfo("OK", f"Đã lưu: {fpath}")

    def export_total_csv(self):
        if self._total_df is None or self._total_df.empty:
            messagebox.showwarning("Chú ý", "Không có dữ liệu để xuất.")
            return
        fpath = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not fpath:
            return
        self._total_df.to_csv(fpath, index=False, encoding="utf-8-sig")
        messagebox.showinfo("OK", f"Đã lưu: {fpath}")
