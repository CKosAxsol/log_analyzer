#!/usr/bin/env python3
"""Interactive CSV plotter with column selection and zoomable charts."""

from __future__ import annotations

import csv
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from functions.csv_parser import TIMESTAMP_COLUMN, open_csv_with_fallbacks, parse_csv
from functions.dependencies import ensure_dependencies

ensure_dependencies()

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
except ImportError as exc:
    raise SystemExit(
        "Missing dependency: tkinter. Install Python with Tcl/Tk support to run csv_plotter.py."
    ) from exc

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk  # noqa: E402
from matplotlib import dates as mdates  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402


THEMES = {
    "dark": {
        "bg": "#1e1e1e",
        "panel": "#252526",
        "input": "#2d2d30",
        "text": "#f3f3f3",
        "muted_text": "#c8c8c8",
        "accent": "#0e639c",
        "grid": "#4a4a4a",
        "plot_bg": "#202124",
        "axis": "#d6d6d6",
        "button_active": "#1177bb",
        "button_pressed": "#0b4f79",
    },
    "light": {
        "bg": "#f3f3f3",
        "panel": "#e8e8e8",
        "input": "#ffffff",
        "text": "#1f1f1f",
        "muted_text": "#555555",
        "accent": "#d9e8f5",
        "grid": "#c7c7c7",
        "plot_bg": "#ffffff",
        "axis": "#222222",
        "button_active": "#c8def1",
        "button_pressed": "#b2d0ea",
    },
}


class CsvPlotterApp:
    """Desktop UI for selecting CSV columns and plotting them interactively."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("CSV Plotter")
        self.root.geometry("1400x900")

        self.csv_path: Path | None = None
        self.record_columns: dict[str, list[str]] = {}
        self.record_systems: dict[str, list[str]] = {}
        self.numeric_columns: dict[tuple[str, str], list[str]] = {}

        self.file_var = tk.StringVar(value="Keine CSV geladen")
        self.delimiter_var = tk.StringVar(value=";")
        self.record_type_var = tk.StringVar()
        self.system_name_var = tk.StringVar()
        self.status_var = tk.StringVar(value="CSV laden, dann Record Type, System und Spalten waehlen.")
        self.has_plot = False
        self.theme_name = "dark"

        self._build_menu()
        self._configure_styles()
        self._build_ui()
        self._apply_theme_to_widgets()

    def _build_menu(self) -> None:
        """Create the application menu."""
        menu_bar = tk.Menu(self.root)
        ansicht_menu = tk.Menu(menu_bar, tearoff=False)
        ansicht_menu.add_command(label="Dark Mode", command=lambda: self.set_theme("dark"))
        ansicht_menu.add_command(label="Light Mode", command=lambda: self.set_theme("light"))
        menu_bar.add_cascade(label="Ansicht", menu=ansicht_menu)
        self.root.config(menu=menu_bar)

    def _configure_styles(self) -> None:
        """Apply a dark ttk theme palette."""
        colors = THEMES[self.theme_name]
        self.root.configure(bg=colors["bg"])
        style = ttk.Style(self.root)
        style.theme_use("clam")

        style.configure(".", background=colors["bg"], foreground=colors["text"])
        style.configure("TFrame", background=colors["bg"])
        style.configure("Panel.TFrame", background=colors["panel"])
        style.configure("TLabel", background=colors["bg"], foreground=colors["text"])
        style.configure("Panel.TLabel", background=colors["panel"], foreground=colors["text"])
        style.configure(
            "TButton",
            background=colors["accent"],
            foreground=colors["text"],
            borderwidth=0,
            focusthickness=0,
            padding=6,
        )
        style.map(
            "TButton",
            background=[("active", colors["button_active"]), ("pressed", colors["button_pressed"])],
            foreground=[("disabled", "#7f7f7f")],
        )
        style.configure(
            "TEntry",
            fieldbackground=colors["input"],
            foreground=colors["text"],
            insertcolor=colors["text"],
        )
        style.configure(
            "TCombobox",
            fieldbackground=colors["input"],
            background=colors["input"],
            foreground=colors["text"],
            arrowcolor=colors["text"],
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", colors["input"])],
            foreground=[("readonly", colors["text"])],
            background=[("readonly", colors["input"])],
        )
        style.configure(
            "Status.TLabel",
            background=colors["input"],
            foreground=colors["muted_text"],
            padding=6,
        )

    def _build_ui(self) -> None:
        main = ttk.Frame(self.root, padding=12)
        main.pack(fill=tk.BOTH, expand=True)
        main.columnconfigure(0, weight=0)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(0, weight=1)

        controls = ttk.Frame(main, padding=(0, 0, 12, 0), style="Panel.TFrame")
        controls.grid(row=0, column=0, sticky="ns")
        controls.columnconfigure(0, weight=1)

        ttk.Label(controls, text="CSV-Datei", font=("Segoe UI", 10, "bold"), style="Panel.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Button(controls, text="Datei oeffnen", command=self.open_file).grid(
            row=1, column=0, sticky="ew", pady=(4, 8)
        )
        ttk.Label(
            controls,
            textvariable=self.file_var,
            wraplength=320,
            justify=tk.LEFT,
            style="Panel.TLabel",
        ).grid(row=2, column=0, sticky="w")

        ttk.Label(controls, text="Trennzeichen", style="Panel.TLabel").grid(row=3, column=0, sticky="w", pady=(16, 0))
        delimiter_entry = ttk.Entry(controls, textvariable=self.delimiter_var, width=8)
        delimiter_entry.grid(row=4, column=0, sticky="w", pady=(4, 0))

        ttk.Label(controls, text="Record Type", style="Panel.TLabel").grid(row=5, column=0, sticky="w", pady=(16, 0))
        self.record_type_box = ttk.Combobox(
            controls,
            textvariable=self.record_type_var,
            state="readonly",
            width=38,
        )
        self.record_type_box.grid(row=6, column=0, sticky="ew", pady=(4, 0))
        self.record_type_box.bind("<<ComboboxSelected>>", self.on_record_type_changed)

        ttk.Label(controls, text="System", style="Panel.TLabel").grid(row=7, column=0, sticky="w", pady=(16, 0))
        self.system_box = ttk.Combobox(
            controls,
            textvariable=self.system_name_var,
            state="readonly",
            width=38,
        )
        self.system_box.grid(row=8, column=0, sticky="ew", pady=(4, 0))
        self.system_box.bind("<<ComboboxSelected>>", self.on_system_changed)

        ttk.Label(controls, text="Spalten", style="Panel.TLabel").grid(row=9, column=0, sticky="w", pady=(16, 0))
        list_frame = ttk.Frame(controls, style="Panel.TFrame")
        list_frame.grid(row=10, column=0, sticky="nsew", pady=(4, 0))
        controls.rowconfigure(10, weight=1)
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)

        self.column_list = tk.Listbox(
            list_frame,
            selectmode=tk.EXTENDED,
            exportselection=False,
            width=42,
            height=24,
            highlightthickness=0,
            borderwidth=0,
        )
        self.column_list.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.column_list.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.column_list.configure(yscrollcommand=scrollbar.set)

        button_row = ttk.Frame(controls)
        button_row.grid(row=11, column=0, sticky="ew", pady=(12, 0))
        button_row.columnconfigure(0, weight=1)
        button_row.columnconfigure(1, weight=1)
        ttk.Button(button_row, text="Alle waehlen", command=self.select_all_columns).grid(
            row=0, column=0, sticky="ew", padx=(0, 4)
        )
        ttk.Button(button_row, text="Auswahl loeschen", command=self.clear_column_selection).grid(
            row=0, column=1, sticky="ew", padx=(4, 0)
        )

        ttk.Button(controls, text="Plot anzeigen", command=self.plot_selected_columns).grid(
            row=12, column=0, sticky="ew", pady=(12, 0)
        )
        ttk.Label(
            controls,
            text="Zoom und Pan funktionieren ueber die Toolbar unter dem Plot.",
            wraplength=320,
            justify=tk.LEFT,
            style="Panel.TLabel",
        ).grid(row=13, column=0, sticky="w", pady=(12, 0))

        plot_frame = ttk.Frame(main)
        plot_frame.grid(row=0, column=1, sticky="nsew")
        plot_frame.rowconfigure(0, weight=1)
        plot_frame.columnconfigure(0, weight=1)

        self.figure = Figure(figsize=(10, 7), dpi=100)
        self.axes = self.figure.add_subplot(111)
        self._style_axes()
        self.axes.set_title("Noch kein Plot geladen")
        self.axes.set_xlabel("Datum + Zeit")
        self.axes.set_ylabel("Wert")

        self.canvas = FigureCanvasTkAgg(self.figure, master=plot_frame)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")
        self.canvas.get_tk_widget().configure(highlightthickness=0)

        toolbar_frame = ttk.Frame(plot_frame)
        toolbar_frame.grid(row=1, column=0, sticky="ew")

        self.toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame, pack_toolbar=False)
        self.toolbar.update()
        self.toolbar.pack(fill=tk.X)

        status_bar = ttk.Label(main, textvariable=self.status_var, anchor="w", style="Status.TLabel")
        status_bar.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))

    def _style_axes(self) -> None:
        """Apply the dark plot palette to the current axes."""
        colors = THEMES[self.theme_name]
        self.figure.set_facecolor(colors["plot_bg"])
        self.axes.set_facecolor(colors["plot_bg"])
        self.axes.grid(True, color=colors["grid"], alpha=0.35)
        self.axes.tick_params(axis="x", colors=colors["axis"])
        self.axes.tick_params(axis="y", colors=colors["axis"])
        self.axes.xaxis.label.set_color(colors["axis"])
        self.axes.yaxis.label.set_color(colors["axis"])
        self.axes.title.set_color(colors["text"])
        for spine in self.axes.spines.values():
            spine.set_color(colors["grid"])

    def _apply_theme_to_widgets(self) -> None:
        """Apply theme colors to non-ttk widgets and the plot canvas."""
        colors = THEMES[self.theme_name]
        self.column_list.configure(
            bg=colors["input"],
            fg=colors["text"],
            selectbackground=colors["accent"],
            selectforeground=colors["text"],
        )
        self.canvas.get_tk_widget().configure(bg=colors["plot_bg"])

    def set_theme(self, theme_name: str) -> None:
        """Switch between light and dark UI themes."""
        if theme_name not in THEMES or theme_name == self.theme_name:
            return
        self.theme_name = theme_name
        self._configure_styles()
        self._apply_theme_to_widgets()
        self._style_axes()
        legend = self.axes.get_legend()
        if legend is not None:
            legend.get_frame().set_facecolor(THEMES[self.theme_name]["input"])
            legend.get_frame().set_edgecolor(THEMES[self.theme_name]["grid"])
            for text in legend.get_texts():
                text.set_color(THEMES[self.theme_name]["text"])
        self.canvas.draw_idle()
        self.status_var.set(f"Darstellung auf {theme_name} Modus umgestellt.")

    def open_file(self) -> None:
        """Prompt for a CSV file and populate record/system/column selectors."""
        initial_dir = ROOT_DIR / "input"
        file_name = filedialog.askopenfilename(
            title="CSV-Datei waehlen",
            initialdir=initial_dir if initial_dir.exists() else ROOT_DIR,
            filetypes=[("CSV-Dateien", "*.csv"), ("Alle Dateien", "*.*")],
        )
        if not file_name:
            return

        self.csv_path = Path(file_name)
        self.file_var.set(str(self.csv_path))

        try:
            self._load_metadata()
        except Exception as exc:
            self._reset_selectors()
            messagebox.showerror("CSV konnte nicht geladen werden", str(exc))
            self.status_var.set("Fehler beim Laden der CSV.")
            return

        record_types = sorted(self.record_columns)
        self.record_type_box["values"] = record_types
        if record_types:
            self.record_type_var.set(record_types[0])
            self.on_record_type_changed()
            self.status_var.set(
                f"Datei geladen: {self.csv_path.name}. Record Type, System und Spalten auswaehlen."
            )
        else:
            self._reset_selectors()
            self.status_var.set("Keine auswertbaren Datensaetze in der CSV gefunden.")

    def _load_metadata(self) -> None:
        """Discover record types, systems, and numeric columns inside the CSV."""
        if self.csv_path is None:
            raise ValueError("Es wurde keine CSV-Datei ausgewaehlt.")

        delimiter = self._get_delimiter()
        record_columns: dict[str, list[str]] = {}
        record_systems: dict[str, set[str]] = {}
        numeric_columns: dict[tuple[str, str], set[str]] = {}

        with open_csv_with_fallbacks(self.csv_path) as handle:
            reader = csv.reader(handle, delimiter=delimiter)
            header_map_by_record: dict[str, dict[int, str]] = {}

            for row in reader:
                if len(row) < 3:
                    continue
                record_type = row[0].strip()
                system_name = row[1].strip()
                third_cell = row[2].strip()

                if third_cell == TIMESTAMP_COLUMN:
                    columns = [value.strip() for value in row[3:] if value.strip()]
                    record_columns[record_type] = columns
                    header_map_by_record[record_type] = {
                        idx: value.strip() for idx, value in enumerate(row[3:], start=3) if value.strip()
                    }
                    continue

                if record_type not in header_map_by_record:
                    continue

                record_systems.setdefault(record_type, set()).add(system_name)
                key = (record_type, system_name)
                numeric_columns.setdefault(key, set())

                for idx, raw_value in enumerate(row[3:], start=3):
                    column_name = header_map_by_record[record_type].get(idx)
                    if not column_name:
                        continue
                    value = raw_value.strip()
                    if not value:
                        continue
                    try:
                        float(value)
                    except ValueError:
                        continue
                    numeric_columns[key].add(column_name)

        self.record_columns = record_columns
        self.record_systems = {
            record_type: sorted(systems)
            for record_type, systems in record_systems.items()
        }
        self.numeric_columns = {}
        for key, columns in numeric_columns.items():
            record_type, _system_name = key
            ordered_columns = [
                column
                for column in self.record_columns.get(record_type, [])
                if column in columns
            ]
            self.numeric_columns[key] = ordered_columns

    def _get_delimiter(self) -> str:
        """Return the configured delimiter or fail with a user-friendly message."""
        delimiter = self.delimiter_var.get()
        if not delimiter:
            raise ValueError("Bitte ein Trennzeichen angeben.")
        return delimiter

    def _reset_selectors(self) -> None:
        """Clear all selector widgets after load errors."""
        self.record_columns = {}
        self.record_systems = {}
        self.numeric_columns = {}
        self.record_type_var.set("")
        self.system_name_var.set("")
        self.record_type_box["values"] = []
        self.system_box["values"] = []
        self._set_column_values([])

    def on_record_type_changed(self, _event: object | None = None) -> None:
        """Refresh systems and columns after record type selection changes."""
        record_type = self.record_type_var.get()
        systems = self.record_systems.get(record_type, [])
        self.system_box["values"] = systems
        if systems:
            self.system_name_var.set(systems[0])
        else:
            self.system_name_var.set("")
        self.on_system_changed()

    def on_system_changed(self, _event: object | None = None) -> None:
        """Refresh the selectable numeric column list."""
        key = (self.record_type_var.get(), self.system_name_var.get())
        columns = self.numeric_columns.get(key)
        if not columns:
            columns = self.record_columns.get(self.record_type_var.get(), [])
        self._set_column_values(columns)
        self.status_var.set(
            f"{len(columns)} Spalten verfuegbar fuer {self.record_type_var.get()} / {self.system_name_var.get()}."
        )

    def _set_column_values(self, columns: list[str]) -> None:
        """Replace the listbox content with the given columns."""
        self.column_list.delete(0, tk.END)
        for column in columns:
            self.column_list.insert(tk.END, column)

    def select_all_columns(self) -> None:
        """Select every currently listed column."""
        self.column_list.selection_set(0, tk.END)

    def clear_column_selection(self) -> None:
        """Clear the current column selection."""
        self.column_list.selection_clear(0, tk.END)

    def plot_selected_columns(self) -> None:
        """Parse the CSV for the selected columns and render them to the canvas."""
        if self.csv_path is None:
            messagebox.showwarning("Keine Datei", "Bitte zuerst eine CSV-Datei laden.")
            return

        selected_columns = [self.column_list.get(idx) for idx in self.column_list.curselection()]
        if not selected_columns:
            messagebox.showwarning("Keine Spalten", "Bitte mindestens eine Spalte auswaehlen.")
            return

        try:
            parsed = parse_csv(
                csv_path=self.csv_path,
                system_name=self.system_name_var.get(),
                record_type=self.record_type_var.get(),
                columns=selected_columns,
                delimiter=self._get_delimiter(),
            )
        except Exception as exc:
            messagebox.showerror("Plot fehlgeschlagen", str(exc))
            self.status_var.set("Plot konnte nicht erstellt werden.")
            return

        self.axes.clear()
        self._style_axes()
        for column in selected_columns:
            self.axes.plot(parsed.timestamps, parsed.series[column], label=column, linewidth=1.2)

        locator = mdates.AutoDateLocator()
        self.axes.xaxis.set_major_locator(locator)
        self.axes.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d %H:%M:%S"))
        self.axes.set_title(f"{parsed.csv_path.name}\n{parsed.record_type} | {parsed.system_name}")
        self.axes.set_xlabel("Datum + Zeit")
        self.axes.set_ylabel("Wert")
        legend = self.axes.legend(loc="best")
        legend.get_frame().set_facecolor(THEMES[self.theme_name]["input"])
        legend.get_frame().set_edgecolor(THEMES[self.theme_name]["grid"])
        for text in legend.get_texts():
            text.set_color(THEMES[self.theme_name]["text"])
        self.figure.autofmt_xdate()
        self.canvas.draw_idle()
        self.toolbar.update()
        self.has_plot = True

        self.status_var.set(
            f"Plot aktualisiert: {len(selected_columns)} Spalten, {len(parsed.timestamps)} Datenpunkte."
        )


def main() -> int:
    """Start the desktop application."""
    root = tk.Tk()
    CsvPlotterApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
