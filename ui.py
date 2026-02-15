import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


class STLGeneratorUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SVG Puzzle STL Generator")
        self.geometry("860x580")
        self.minsize(760, 500)

        self.process = None
        self.log_queue = queue.Queue()

        self.input_var = tk.StringVar()
        self.output_var = tk.StringVar(value="jigsaw_pieces.stl")
        self.thickness_var = tk.StringVar(value="3.0")
        self.tolerance_var = tk.StringVar(value="-0.2")
        self.density_var = tk.StringVar(value="0.5")
        self.status_var = tk.StringVar(value="Ready")

        self._build_layout()
        self.after(100, self._drain_log_queue)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_layout(self):
        container = ttk.Frame(self, padding=16)
        container.pack(fill="both", expand=True)
        container.columnconfigure(1, weight=1)
        container.rowconfigure(6, weight=1)

        ttk.Label(container, text="Input SVG").grid(row=0, column=0, sticky="w", pady=6)
        input_entry = ttk.Entry(container, textvariable=self.input_var)
        input_entry.grid(row=0, column=1, sticky="ew", padx=8)
        ttk.Button(container, text="Browse...", command=self._pick_input).grid(
            row=0, column=2, sticky="ew"
        )

        ttk.Label(container, text="Output STL").grid(row=1, column=0, sticky="w", pady=6)
        output_entry = ttk.Entry(container, textvariable=self.output_var)
        output_entry.grid(row=1, column=1, sticky="ew", padx=8)
        ttk.Button(container, text="Browse...", command=self._pick_output).grid(
            row=1, column=2, sticky="ew"
        )

        ttk.Label(container, text="Thickness (mm)").grid(row=2, column=0, sticky="w", pady=6)
        ttk.Entry(container, textvariable=self.thickness_var).grid(
            row=2, column=1, sticky="w", padx=8
        )

        ttk.Label(container, text="Tolerance (mm)").grid(row=3, column=0, sticky="w", pady=6)
        ttk.Entry(container, textvariable=self.tolerance_var).grid(
            row=3, column=1, sticky="w", padx=8
        )

        ttk.Label(container, text="Density").grid(row=4, column=0, sticky="w", pady=6)
        ttk.Entry(container, textvariable=self.density_var).grid(
            row=4, column=1, sticky="w", padx=8
        )

        action_frame = ttk.Frame(container)
        action_frame.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(8, 12))
        action_frame.columnconfigure(0, weight=1)
        self.generate_btn = ttk.Button(
            action_frame, text="Generate STL", command=self._start_generation
        )
        self.generate_btn.grid(row=0, column=0, sticky="w")
        ttk.Label(action_frame, textvariable=self.status_var).grid(
            row=0, column=1, sticky="e", padx=8
        )

        ttk.Label(container, text="Process Log").grid(row=6, column=0, sticky="nw")
        log_frame = ttk.Frame(container)
        log_frame.grid(row=6, column=1, columnspan=2, sticky="nsew", padx=8)
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)

        self.log_text = tk.Text(log_frame, wrap="word", height=12, state="disabled")
        self.log_text.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=scroll.set)

    def _append_log(self, line):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", line)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _pick_input(self):
        path = filedialog.askopenfilename(
            title="Select SVG file",
            filetypes=[("SVG files", "*.svg"), ("All files", "*.*")],
        )
        if not path:
            return
        self.input_var.set(path)
        if self.output_var.get().strip() == "jigsaw_pieces.stl":
            stem = os.path.splitext(os.path.basename(path))[0]
            suggested = os.path.join(os.path.dirname(path), f"{stem}.stl")
            self.output_var.set(suggested)

    def _pick_output(self):
        path = filedialog.asksaveasfilename(
            title="Save STL as",
            defaultextension=".stl",
            filetypes=[("STL files", "*.stl"), ("All files", "*.*")],
            initialfile=os.path.basename(self.output_var.get().strip() or "jigsaw_pieces.stl"),
        )
        if path:
            self.output_var.set(path)

    def _validate_inputs(self):
        input_file = self.input_var.get().strip()
        if not input_file:
            messagebox.showerror("Missing input", "Please choose an SVG input file.")
            return None
        if not os.path.exists(input_file):
            messagebox.showerror("Invalid input", "Selected SVG file does not exist.")
            return None

        output_file = self.output_var.get().strip()
        if not output_file:
            messagebox.showerror("Missing output", "Please provide an output STL file.")
            return None

        try:
            thickness = float(self.thickness_var.get().strip())
            tolerance = float(self.tolerance_var.get().strip())
            density = float(self.density_var.get().strip())
        except ValueError:
            messagebox.showerror("Invalid values", "Thickness, tolerance, and density must be numbers.")
            return None

        if thickness <= 0:
            messagebox.showerror("Invalid thickness", "Thickness must be greater than 0.")
            return None
        if density <= 0:
            messagebox.showerror("Invalid density", "Density must be greater than 0.")
            return None

        return input_file, output_file, thickness, tolerance, density

    def _start_generation(self):
        values = self._validate_inputs()
        if not values:
            return

        input_file, output_file, thickness, tolerance, density = values
        cmd = [
            sys.executable,
            os.path.join(os.path.dirname(__file__), "generate_stl.py"),
            input_file,
            "-o",
            output_file,
            "--thickness",
            str(thickness),
            "--tolerance",
            str(tolerance),
            "--density",
            str(density),
        ]

        self.generate_btn.configure(state="disabled")
        self.status_var.set("Running...")
        self._append_log("\n=== Starting generation ===\n")
        self._append_log(" ".join(cmd) + "\n\n")

        thread = threading.Thread(target=self._run_process, args=(cmd,), daemon=True)
        thread.start()

    def _run_process(self, cmd):
        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            assert self.process.stdout is not None
            for line in self.process.stdout:
                self.log_queue.put(line)
            return_code = self.process.wait()
            if return_code == 0:
                self.log_queue.put("\nGeneration completed successfully.\n")
            else:
                self.log_queue.put(f"\nGeneration failed with exit code {return_code}.\n")
        except Exception as exc:
            self.log_queue.put(f"\nError while running generator: {exc}\n")
        finally:
            self.log_queue.put("__PROCESS_FINISHED__")
            self.process = None

    def _drain_log_queue(self):
        try:
            while True:
                item = self.log_queue.get_nowait()
                if item == "__PROCESS_FINISHED__":
                    self.generate_btn.configure(state="normal")
                    self.status_var.set("Ready")
                else:
                    self._append_log(item)
        except queue.Empty:
            pass
        self.after(100, self._drain_log_queue)

    def _on_close(self):
        if self.process and self.process.poll() is None:
            if not messagebox.askyesno(
                "Process running", "Generation is still running. Do you want to stop and exit?"
            ):
                return
            self.process.terminate()
        self.destroy()


if __name__ == "__main__":
    app = STLGeneratorUI()
    app.mainloop()
