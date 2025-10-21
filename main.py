import tkinter as tk
from tkinter import ttk, messagebox
from ttkthemes import ThemedStyle

from config import APP_TITLE
from services import db
from services.face import ensure_face_lib
from ui.attendance_tab import AttendanceTab
from ui.employee_tab import EmployeeTab
from ui.report_tab import ReportTab


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("980x680")
        self.resizable(True, True)

        # Áp dụng theme sáng
        style = ThemedStyle(self)
        style.set_theme("arc")

        s = ttk.Style()
        s.configure("TLabel", font=("Segoe UI", 11))
        s.configure("TButton", font=("Segoe UI", 10), padding = 5)
        s.configure("TEntry", font=("Segoe UI", 10))
        s.configure("Treeview", font = ("Consolas", 10), rowheight=26)
        s.map("Treeview", background=[('selected', '#cdeaf7')])

        # Check libs and init DB
        try:
            ensure_face_lib()
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không tải được face_recognition: {e}")
            self.destroy()
            return

        db.init_db()

        nb = ttk.Notebook(self)
        self.tab_att = AttendanceTab(nb)
        self.tab_emp = EmployeeTab(nb)
        self.tab_rep = ReportTab(nb)

        nb.add(self.tab_att, text="📸 Chấm công")
        nb.add(self.tab_emp, text="👥 Nhân viên")
        nb.add(self.tab_rep, text="📊 Báo cáo")
        nb.pack(fill="both", expand=True, padx=5, pady=5)

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        # ensure camera released if opened
        try:
            self.tab_att.on_close()
        except Exception:
            pass
        self.destroy()


def main():
    app = App()
    if app.winfo_exists():
        app.mainloop()

if __name__ == "__main__":
    main()