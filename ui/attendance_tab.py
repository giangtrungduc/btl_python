import threading
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk

from config import DEFAULT_TOL
from services import db
from services.face import face_encode_from_image, match_employee

try:
    import cv2
except Exception:
    cv2 = None


class AttendanceTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)

        # Controls
        top = ttk.Frame(self)
        top.pack(fill="x", padx=10, pady=8)

        ttk.Label(top, text="Ngưỡng nhận diện (nhỏ = chặt):").pack(side="left")
        self.scale_tol = ttk.Scale(top, from_=0.30, to=0.70, value=DEFAULT_TOL,
                                   orient="horizontal", length=200)
        self.scale_tol.pack(side="left", padx=6)

        ttk.Button(top, text="Bật camera", command=self.start_camera).pack(side="left", padx=4)
        ttk.Button(top, text="Tắt camera", command=self.stop_camera).pack(side="left", padx=4)
        ttk.Button(top, text="Chấm công (chụp)", command=self.scan_and_mark).pack(side="left", padx=4)

        self.video_panel = ttk.Label(self, relief="sunken", anchor="center")
        self.video_panel.pack(fill="both", expand=True, padx=10, pady=10)

        self.att_status = tk.StringVar(value="Chưa có thao tác.")
        ttk.Label(self, textvariable=self.att_status).pack(pady=6)

        # Webcam state
        self.cap = None
        self._video_loop = False
        self._frame_imgtk = None

    # ---------- Camera ----------
    def start_camera(self):
        if cv2 is None:
            messagebox.showerror("Lỗi", "OpenCV (cv2) chưa được cài đặt.")
            return
        if self.cap is not None:
            return
        
        # Tối ưu truy cập camera
        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)

        if not self.cap.isOpened():
            self.cap = None
            messagebox.showerror("Lỗi", "Không mở được webcam.")
            return
        
        self._video_loop = True
        self.att_status.set("Camera đã bật.")
        self.after(50, self._update_video)

    def stop_camera(self):
        self._video_loop = False
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None
        self.video_panel.config(image="", text="")
        self.att_status.set("Camera đã tắt.")

    def _update_video(self):
        if not self._video_loop or self.cap is None:
            return

        ret, frame = self.cap.read()
        if ret:
            frame = cv2.flip(frame, 1)  # Lật gương
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb).resize((640, 480))
            imgtk = ImageTk.PhotoImage(image=img)
            self._frame_imgtk = imgtk
            self.video_panel.config(image=imgtk)

        # Lặp lại ~30fps
        if self._video_loop:
            self.after(33, self._update_video)

    def scan_and_mark(self):
        tol = float(self.scale_tol.get())
        if self.cap is None:
            messagebox.showwarning("Chú ý", "Hãy bật camera trước.")
            return
        ret, frame = self.cap.read()
        if not ret:
            messagebox.showerror("Lỗi", "Không đọc được frame từ camera.")
            return
        img = Image.fromarray(frame[:, :, ::-1])  # to RGB
        try:
            enc = face_encode_from_image(img)
        except Exception as e:
            messagebox.showerror("Lỗi", f"Lỗi xử lý ảnh: {e}")
            return
        if enc is None:
            self.att_status.set("Không phát hiện được khuôn mặt. Thử lại.")
            return
        m = match_employee(enc, tol)
        if m is None:
            self.att_status.set("❌ Không khớp với nhân viên nào (Unknown). Vào tab Nhân viên để thêm.")
        else:
            db.mark_attendance(int(m["id"]))
            self.att_status.set(f"✅ Đã chấm công cho {m['name']} (khoảng cách={m['distance']:.3f}).")
            
    # ---------- Lifecycle ----------
    def on_close(self):
        self._video_loop = False
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass