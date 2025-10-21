import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image

from services import db
from services.face import face_encode_from_image


class EmployeeTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)

        self.configure(padding=10)

        # Danh sách khung
        list_frame = ttk.LabelFrame(self, text="📋 Danh sách nhân viên", padding=10)
        list_frame.pack(side="left", fill="both", expand=True, padx=8, pady=8)

        cols = ("id","code","name","dept")
        self.tree = ttk.Treeview(list_frame, columns=cols, show="headings", height=20)
        self.tree.heading("id", text="ID")
        self.tree.heading("code", text="Mã NV")
        self.tree.heading("name", text="Họ tên")
        self.tree.heading("dept", text="Phòng ban")
        self.tree.column("id", width=50, anchor="center")
        self.tree.column("code", width=100)
        self.tree.column("name", width=180)
        self.tree.column("dept", width=120)
        self.tree.pack(fill="both", expand=True, pady=5)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll = scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        btns = ttk.Frame(list_frame)
        btns.pack(fill="x", pady=6)
        ttk.Button(btns, text="🔄 Tải lại", command=self.refresh_employees).pack(side="left", padx=4)
        ttk.Button(btns, text="❌ Xoá nhân viên", command=self.delete_selected_employee).pack(side="left", padx=4)

        # Khung thêm nhân viên
        form = ttk.LabelFrame(self, text="➕ Thêm nhân viên mới", padding=10)
        form.pack(side="right", fill="y", padx=8, pady=8)

        self.emp_code_var = tk.StringVar()
        self.emp_name_var = tk.StringVar()
        self.emp_dept_var = tk.StringVar()
        self.face_path_var = tk.StringVar()

        fields = [
            (" Mã nhân viên", self.emp_code_var),
            (" Họ tên", self.emp_name_var),
            (" Phòng ban", self.emp_dept_var)
        ]
        for i, (label, var) in enumerate(fields):
            ttk.Label(form, text=label).grid(row=i, column=0, sticky="w", padx=6, pady=4)
            ttk.Entry(form, textvariable=var, width=28).grid(row=i, column=1, padx=6, pady=4)

        # Ảnh khuôn mặt
        ttk.Label(form, text=" Ảnh khuôn mặt").grid(row=3, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(form, textvariable=self.face_path_var, width=28).grid(row=3, column=1, padx=6, pady=4)
        ttk.Button(form, text="Chọn ảnh...", command=self.browse_face_image).grid(row=3, column=2, padx=4, pady=4)

        ttk.Button(form, text="💾 Lưu nhân viên", command=self.save_employee_from_file).grid(
            row=4, column=1, columnspan=2, pady=10
        )


        form.grid_columnconfigure(1, weight=1)
        self.refresh_employees()

    # Các chức năng  
    def refresh_employees(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        df = db.load_all_embeddings()
        if df.empty:
            return
        for _, r in df.iterrows():
            self.tree.insert("", "end", values=(int(r["id"]), r["emp_code"], r["name"], r["department"]))

    def browse_face_image(self):
        fpath = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.jpeg *.png")])
        if fpath:
            self.face_path_var.set(fpath)

    def save_employee_from_file(self):
        code = self.emp_code_var.get().strip()
        name = self.emp_name_var.get().strip()
        dept = self.emp_dept_var.get().strip()
        fpath = self.face_path_var.get().strip()
        if not code or not name or not fpath:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng nhập đủ Mã NV, Họ tên và chọn ảnh.")
            return
        try:
            img = Image.open(fpath).convert("RGB")
            enc = face_encode_from_image(img)
            if enc is None:
                messagebox.showerror("Lỗi", "Không phát hiện được khuôn mặt trong ảnh.")
                return
            ok, msg = db.add_employee(code, name, dept, enc)
            if ok:
                messagebox.showinfo("Thành công", msg)
                self.refresh_employees()
                self.emp_code_var.set("")
                self.emp_name_var.set("")
                self.emp_dept_var.set("")
                self.face_path_var.set("")
            else:
                messagebox.showerror("Lỗi", msg)
        except Exception as e:
            messagebox.showerror("Lỗi", f"Lỗi xử lý: {e}")

    def delete_selected_employee(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Thông báo", "Chọn nhân viên cần xoá.")
            return
        vals = self.tree.item(sel[0], "values")
        emp_id = int(vals[0])
        if messagebox.askyesno("Xác nhận", f"Xoá nhân viên ID {emp_id}?"):
            db.delete_employee(emp_id)
            self.refresh_employees()