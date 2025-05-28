import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import gpxpy
import gpxpy.gpx
import os
from datetime import datetime
import pytz
import tzlocal
import webbrowser
import folium
from zoneinfo import ZoneInfo

class GPXEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("GPX Tools")

        self.selected_files = []
        self.gpx_data = None

        self.create_widgets()

    def create_widgets(self):
        self.file_frame = ttk.Frame(self.root, padding=10)
        self.file_frame.grid(row=0, column=0, sticky="ew")

        self.load_button = ttk.Button(self.file_frame, text="Chọn GPX", command=self.load_gpx)
        self.load_button.grid(row=0, column=0, padx=5)

        self.merge_button = ttk.Button(self.file_frame, text="Gộp GPX", command=self.merge_gpx_files)
        self.merge_button.grid(row=0, column=1, padx=5)

        self.preview_button = ttk.Button(self.file_frame, text="Preview Map", command=self.preview_map)
        self.preview_button.grid(row=0, column=2, padx=5)

        self.time_frame = ttk.Frame(self.root, padding=10)
        self.time_frame.grid(row=1, column=0, sticky="ew")

        ttk.Label(self.time_frame, text="Nhập thời gian bắt đầu mới (local):").grid(row=0, column=0, sticky="w")
        self.time_entry = ttk.Entry(self.time_frame, width=25)
        self.time_entry.insert(0, "2025-05-28 09:00:00")
        self.time_entry.grid(row=0, column=1, padx=5)

        self.shift_button = ttk.Button(self.time_frame, text="Shift Time và Xuất file", command=self.shift_and_save)
        self.shift_button.grid(row=1, column=0, columnspan=2, pady=5)

        self.status_label = ttk.Label(self.root, text="", foreground="blue")
        self.status_label.grid(row=2, column=0, pady=(0, 10), sticky="w", padx=10)

    def load_gpx(self):
        file_path = filedialog.askopenfilename(filetypes=[("GPX files", "*.gpx")])
        if file_path:
            self.selected_files = [file_path]
            with open(file_path, 'r') as gpx_file:
                self.gpx_data = gpxpy.parse(gpx_file)
            local_tz = tzlocal.get_localzone()
            try:
                start_time = self.gpx_data.tracks[0].segments[0].points[0].time.astimezone(local_tz)
                self.status_label.config(text=f"Thời gian bắt đầu (local): {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            except Exception as e:
                self.status_label.config(text="Không đọc được thời gian bắt đầu từ file GPX")
            messagebox.showinfo("GPX Tools", f"Đã load: {file_path}")

    def merge_gpx_files(self):
        files = filedialog.askopenfilenames(filetypes=[("GPX files", "*.gpx")])
        if files:
            merged_gpx = gpxpy.gpx.GPX()
            for file_path in files:
                with open(file_path, 'r') as gpx_file:
                    gpx = gpxpy.parse(gpx_file)
                    for track in gpx.tracks:
                        merged_gpx.tracks.append(track)
            self.gpx_data = merged_gpx
            self.status_label.config(text="Đã gộp các file GPX")
            messagebox.showinfo("GPX Tools", "Đã gộp các file GPX")

    def shift_and_save(self):
        if not self.gpx_data:
            messagebox.showwarning("GPX Tools", "Vui lòng chọn file GPX trước.")
            return

        input_time_str = self.time_entry.get()
        try:
            local_tz = tzlocal.get_localzone()
            dt_naive = datetime.strptime(input_time_str, "%Y-%m-%d %H:%M:%S")
            new_local_time = dt_naive.replace(tzinfo=ZoneInfo(str(local_tz)))
            new_utc_time = new_local_time.astimezone(pytz.utc)

            for track in self.gpx_data.tracks:
                for segment in track.segments:
                    if segment.points:
                        start_time = segment.points[0].time
                        if start_time.tzinfo is None:
                            raise ValueError("GPX thời gian không có tzinfo")
                        delta = new_utc_time - start_time
                        for point in segment.points:
                            if point.time:
                                point.time += delta

            out_path = filedialog.asksaveasfilename(defaultextension=".gpx", filetypes=[("GPX files", "*.gpx")])
            if out_path:
                with open(out_path, 'w') as out_file:
                    out_file.write(self.gpx_data.to_xml())
                messagebox.showinfo("GPX Tools", f"Đã xuất file: {out_path}")
        except Exception as e:
            messagebox.showerror("GPX Tools", str(e))

    def preview_map(self):
        if not self.gpx_data:
            messagebox.showwarning("GPX Tools", "Vui lòng chọn hoặc gộp file GPX trước.")
            return

        coords = []
        for track in self.gpx_data.tracks:
            for segment in track.segments:
                for point in segment.points:
                    coords.append((point.latitude, point.longitude))

        if not coords:
            messagebox.showinfo("GPX Tools", "Không tìm thấy toạ độ để hiển thị.")
            return

        m = folium.Map(location=coords[0], zoom_start=14)
        folium.PolyLine(coords, color="blue", weight=3).add_to(m)
        temp_file = "preview_map.html"
        m.save(temp_file)
        webbrowser.open('file://' + os.path.realpath(temp_file))

if __name__ == "__main__":
    root = tk.Tk()
    app = GPXEditorApp(root)
    root.mainloop()
