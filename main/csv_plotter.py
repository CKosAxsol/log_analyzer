#!/usr/bin/env python3
"""Interactive CSV plotter with column selection and zoomable charts."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from functions.csv_parser import TIMESTAMP_COLUMN, open_csv_with_fallbacks
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
    """Desktop UI for selecting CSV columns and plotting them interactively.

    The UI supports two file structures:

    - APS/APU exports with multiple logical tables in one file
    - regular CSV files with one header row

    Both end up in the same plotting path: choose X-axis values, choose
    numeric Y columns, then render the selected series.
    """

    ROW_INDEX_LABEL = "Zeilennummer"

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("CSV Plotter")
        self.root.geometry("1400x900")

        self.csv_path: Path | None = None
        self.csv_mode = "structured"
        self.timestamp_column: str | None = None
        self.plain_columns: list[str] = []
        self.record_columns: dict[str, list[str]] = {}
        self.record_systems: dict[str, list[str]] = {}
        self.numeric_columns: dict[tuple[str, str], list[str]] = {}

        self.file_var = tk.StringVar(value="Keine CSV geladen")
        self.delimiter_var = tk.StringVar(value=";")
        self.record_type_var = tk.StringVar()
        self.system_name_var = tk.StringVar()
        self.x_axis_var = tk.StringVar(value="Datum + Zeit")
        self.status_var = tk.StringVar(value="CSV laden, dann Record Type, System und Spalten waehlen.")
        self.has_plot = False
        self.theme_name = "light"

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

        ttk.Label(controls, text="X-Achse", style="Panel.TLabel").grid(row=9, column=0, sticky="w", pady=(16, 0))
        self.x_axis_box = ttk.Combobox(
            controls,
            textvariable=self.x_axis_var,
            state="readonly",
            width=38,
        )
        self.x_axis_box.grid(row=10, column=0, sticky="ew", pady=(4, 0))

        ttk.Label(controls, text="Spalten", style="Panel.TLabel").grid(row=11, column=0, sticky="w", pady=(16, 0))
        list_frame = ttk.Frame(controls, style="Panel.TFrame")
        list_frame.grid(row=12, column=0, sticky="nsew", pady=(4, 0))
        controls.rowconfigure(12, weight=1)
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
        button_row.grid(row=13, column=0, sticky="ew", pady=(12, 0))
        button_row.columnconfigure(0, weight=1)
        button_row.columnconfigure(1, weight=1)
        ttk.Button(button_row, text="Alle waehlen", command=self.select_all_columns).grid(
            row=0, column=0, sticky="ew", padx=(0, 4)
        )
        ttk.Button(button_row, text="Auswahl loeschen", command=self.clear_column_selection).grid(
            row=0, column=1, sticky="ew", padx=(4, 0)
        )

        ttk.Button(controls, text="Plot anzeigen", command=self.plot_selected_columns).grid(
            row=14, column=0, sticky="ew", pady=(12, 0)
        )
        ttk.Label(
            controls,
            text="Zoom und Pan funktionieren ueber die Toolbar unter dem Plot.",
            wraplength=320,
            justify=tk.LEFT,
            style="Panel.TLabel",
        ).grid(row=15, column=0, sticky="w", pady=(12, 0))

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
            if self.csv_mode == "plain":
                if self.timestamp_column is not None:
                    self.status_var.set(
                        f"Datei geladen: {self.csv_path.name}. Standard-CSV erkannt, Zeitspalte: {self.timestamp_column}."
                    )
                else:
                    self.status_var.set(
                        f"Datei geladen: {self.csv_path.name}. Standard-CSV ohne Zeitspalte erkannt, X-Achse = Zeilennummer."
                    )
            else:
                self.status_var.set(
                    f"Datei geladen: {self.csv_path.name}. Record Type, System, X-Achse und Spalten auswaehlen."
                )
        else:
            self._reset_selectors()
            self.status_var.set("Keine auswertbaren Datensaetze in der CSV gefunden.")

    def _load_metadata(self) -> None:
        """Discover record types, systems, and numeric columns inside the CSV.

        We detect the file structure first, because APS/APU exports need a
        different metadata scan than a standard one-header CSV.
        """
        if self.csv_path is None:
            raise ValueError("Es wurde keine CSV-Datei ausgewaehlt.")

        delimiter = self._get_delimiter()
        self.csv_mode = "structured"
        self.timestamp_column = None
        self.plain_columns = []
        with open_csv_with_fallbacks(self.csv_path) as probe_handle:
            probe_reader = csv.reader(probe_handle, delimiter=delimiter)
            for row in probe_reader:
                if not row:
                    continue
                if len(row) >= 3 and row[2].strip() == TIMESTAMP_COLUMN:
                    self._load_structured_metadata(delimiter)
                    return
        self._load_plain_metadata(delimiter)

    def _load_structured_metadata(self, delimiter: str) -> None:
        """Load metadata for the existing APS/APU export structure.

        APS/APU files contain multiple record blocks. Each block has its own
        schema row and then many data rows for one or more systems.
        """
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
                    # The schema row defines the available columns for this
                    # record type. Later data rows are interpreted against it.
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

    def _load_plain_metadata(self, delimiter: str) -> None:
        """Load metadata for a regular CSV with one header row.

        For standard CSV files we expose every numeric column as a possible
        Y series and every header column as a possible X-axis source.
        """
        if self.csv_path is None:
            raise ValueError("Es wurde keine CSV-Datei ausgewaehlt.")

        with open_csv_with_fallbacks(self.csv_path) as handle:
            reader = csv.reader(handle, delimiter=delimiter)
            header = next(reader, None)
            if header is None:
                raise ValueError("Die CSV-Datei ist leer.")

            normalized_header = self._normalize_header(header)
            if not normalized_header:
                raise ValueError("Die CSV-Datei enthaelt keine gueltige Header-Zeile.")

            sample_rows = [row for row in reader if any(cell.strip() for cell in row)]

        self.csv_mode = "plain"
        self.plain_columns = normalized_header
        self.timestamp_column = self._detect_timestamp_column(normalized_header, sample_rows)

        numeric_columns: list[str] = []
        for index, column_name in enumerate(normalized_header):
            if column_name == self.timestamp_column:
                continue
            if any(self._is_float_row_value(row, index) for row in sample_rows):
                numeric_columns.append(column_name)

        if not numeric_columns:
            raise ValueError("Keine numerischen Spalten in der CSV gefunden.")

        record_type = "CSV"
        system_name = "Alle Daten"
        self.record_columns = {record_type: numeric_columns}
        self.record_systems = {record_type: [system_name]}
        self.numeric_columns = {(record_type, system_name): numeric_columns}

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
        self.csv_mode = "structured"
        self.timestamp_column = None
        self.plain_columns = []
        self.record_type_var.set("")
        self.system_name_var.set("")
        self.x_axis_var.set("Datum + Zeit")
        self.record_type_box["values"] = []
        self.system_box["values"] = []
        self.x_axis_box["values"] = []
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
        self._update_x_axis_options()
        self.status_var.set(
            f"{len(columns)} Spalten verfuegbar fuer {self.record_type_var.get()} / {self.system_name_var.get()}."
        )

    def _update_x_axis_options(self) -> None:
        """Refresh X-axis choices for the current CSV mode.

        APS/APU and plain CSV files expose X values differently, but the UI
        presents both through the same selector widget.
        """
        if self.csv_mode == "plain":
            values = [self.ROW_INDEX_LABEL, *self.plain_columns]
            self.x_axis_box["values"] = values
            preferred_value = self.timestamp_column or self.ROW_INDEX_LABEL
            if self.x_axis_var.get() not in values:
                self.x_axis_var.set(preferred_value)
        else:
            record_type = self.record_type_var.get()
            values = [self.ROW_INDEX_LABEL, TIMESTAMP_COLUMN, *self.record_columns.get(record_type, [])]
            self.x_axis_box["values"] = values
            if self.x_axis_var.get() not in values:
                self.x_axis_var.set(TIMESTAMP_COLUMN)

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
            x_values, series_map, title_suffix, x_label = self._load_selected_series(selected_columns)
        except Exception as exc:
            messagebox.showerror("Plot fehlgeschlagen", str(exc))
            self.status_var.set("Plot konnte nicht erstellt werden.")
            return

        self.axes.clear()
        self._style_axes()
        for column in selected_columns:
            self.axes.plot(x_values, series_map[column], label=column, linewidth=1.2)

        if x_values and isinstance(x_values[0], datetime):
            locator = mdates.AutoDateLocator()
            self.axes.xaxis.set_major_locator(locator)
            self.axes.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d %H:%M:%S"))
            self.figure.autofmt_xdate()

        self.axes.set_title(f"{self.csv_path.name}\n{title_suffix}")
        self.axes.set_xlabel(x_label)
        self.axes.set_ylabel("Wert")
        legend = self.axes.legend(loc="best")
        legend.get_frame().set_facecolor(THEMES[self.theme_name]["input"])
        legend.get_frame().set_edgecolor(THEMES[self.theme_name]["grid"])
        for text in legend.get_texts():
            text.set_color(THEMES[self.theme_name]["text"])
        self.canvas.draw_idle()
        self.toolbar.update()
        self.has_plot = True

        self.status_var.set(
            f"Plot aktualisiert: {len(selected_columns)} Spalten, {len(x_values)} Datenpunkte."
        )

    def _load_selected_series(
        self,
        selected_columns: list[str],
    ) -> tuple[list[datetime] | list[int] | list[float] | list[str], dict[str, list[float]], str, str]:
        """Load the selected series for either structured or plain CSV files.

        This is the single dispatcher that hides the source file structure
        from the plotting code below.
        """
        if self.csv_path is None:
            raise ValueError("Es wurde keine CSV-Datei ausgewaehlt.")

        if self.csv_mode == "structured":
            return self._parse_structured_csv(selected_columns)

        return self._parse_plain_csv(selected_columns)

    def _parse_structured_csv(
        self,
        selected_columns: list[str],
    ) -> tuple[list[datetime] | list[int] | list[float] | list[str], dict[str, list[float]], str, str]:
        """Parse one APS/APU record block with a selectable X-axis column.

        Compared with the CLI parser, this reader is intentionally more
        flexible because the GUI allows the user to choose any column as
        the X axis, not only the timestamp column.
        """
        if self.csv_path is None:
            raise ValueError("Es wurde keine CSV-Datei ausgewaehlt.")

        delimiter = self._get_delimiter()
        record_type = self.record_type_var.get()
        system_name = self.system_name_var.get()
        x_axis_column = self.x_axis_var.get().strip() or TIMESTAMP_COLUMN

        series = {column: [] for column in selected_columns}
        raw_x_values: list[str] = []
        header_map: dict[str, int] | None = None

        with open_csv_with_fallbacks(self.csv_path) as handle:
            reader = csv.reader(handle, delimiter=delimiter)
            for row in reader:
                if not row or len(row) < 3:
                    continue

                if row[0].strip() == record_type and row[2].strip() == TIMESTAMP_COLUMN:
                    # APS/APU schema rows keep the timestamp in column 2 and
                    # all named data columns from column 3 onwards.
                    header_map = {TIMESTAMP_COLUMN: 2}
                    for idx, value in enumerate(row[3:], start=3):
                        stripped = value.strip()
                        if stripped:
                            header_map[stripped] = idx
                    continue

                if row[0].strip() != record_type or row[1].strip() != system_name:
                    continue

                if header_map is None:
                    raise ValueError(
                        f"Keine Schema-Zeile fuer Record Type '{record_type}' in {self.csv_path} gefunden."
                    )

                missing_columns = [column for column in selected_columns if column not in header_map]
                if missing_columns:
                    raise ValueError(
                        "Ausgewaehlte Spalten fehlen in der CSV: " + ", ".join(missing_columns)
                    )
                if x_axis_column != self.ROW_INDEX_LABEL and x_axis_column not in header_map:
                    raise ValueError(f"X-Achsen-Spalte fehlt in der CSV: {x_axis_column}")

                parsed_values: list[float] = []
                for column in selected_columns:
                    value = self._get_row_value(row, header_map[column]).strip()
                    try:
                        parsed_values.append(float(value))
                    except ValueError:
                        parsed_values = []
                        break
                if not parsed_values:
                    continue

                if x_axis_column == self.ROW_INDEX_LABEL:
                    raw_x_values.append(str(len(raw_x_values) + 1))
                else:
                    raw_x_value = self._get_row_value(row, header_map[x_axis_column]).strip()
                    if not raw_x_value:
                        continue
                    raw_x_values.append(raw_x_value)

                for column, value in zip(selected_columns, parsed_values):
                    series[column].append(value)

        if not raw_x_values:
            raise ValueError(
                f"Keine plottbaren Datenzeilen fuer {record_type} / {system_name} gefunden."
            )

        x_values, x_label, _x_is_datetime = self._convert_x_values(raw_x_values, x_axis_column)
        title_suffix = f"{record_type} | {system_name} | X-Achse: {x_label}"
        return x_values, series, title_suffix, x_label

    def _parse_plain_csv(
        self,
        selected_columns: list[str],
    ) -> tuple[list[datetime] | list[int] | list[float] | list[str], dict[str, list[float]], str, str]:
        """Parse a regular CSV with a single header row.

        Rows are only kept when all selected Y columns can be parsed as
        numbers. This prevents misaligned X/Y lists.
        """
        if self.csv_path is None:
            raise ValueError("Es wurde keine CSV-Datei ausgewaehlt.")

        delimiter = self._get_delimiter()
        x_axis_column = self.x_axis_var.get().strip() or self.ROW_INDEX_LABEL
        series = {column: [] for column in selected_columns}
        raw_x_values: list[str] = []

        with open_csv_with_fallbacks(self.csv_path) as handle:
            reader = csv.reader(handle, delimiter=delimiter)
            header = next(reader, None)
            if header is None:
                raise ValueError("Die CSV-Datei ist leer.")

            normalized_header = self._normalize_header(header)
            header_map = {name: idx for idx, name in enumerate(normalized_header)}

            missing_columns = [column for column in selected_columns if column not in header_map]
            if missing_columns:
                raise ValueError(
                    "Ausgewaehlte Spalten fehlen in der CSV: " + ", ".join(missing_columns)
                )
            if x_axis_column != self.ROW_INDEX_LABEL and x_axis_column not in header_map:
                raise ValueError(f"X-Achsen-Spalte fehlt in der CSV: {x_axis_column}")

            row_index = 0
            for row in reader:
                if not any(cell.strip() for cell in row):
                    continue

                parsed_values: list[float] = []
                for column in selected_columns:
                    value = self._get_row_value(row, header_map[column]).strip()
                    try:
                        parsed_values.append(float(value))
                    except ValueError:
                        parsed_values = []
                        break
                if not parsed_values:
                    continue

                if x_axis_column == self.ROW_INDEX_LABEL:
                    row_index += 1
                    raw_x_values.append(str(row_index))
                else:
                    raw_x_value = self._get_row_value(row, header_map[x_axis_column]).strip()
                    if not raw_x_value:
                        continue
                    raw_x_values.append(raw_x_value)

                for column, value in zip(selected_columns, parsed_values):
                    series[column].append(value)

        if not raw_x_values:
            raise ValueError("Keine plottbaren Datenzeilen fuer die aktuelle Auswahl gefunden.")

        x_values, x_label, x_is_datetime = self._convert_x_values(raw_x_values, x_axis_column)
        title_suffix = "Standard CSV"
        if x_axis_column != self.ROW_INDEX_LABEL:
            title_suffix = f"Standard CSV | X-Achse: {x_axis_column}"
        elif x_is_datetime:
            title_suffix = "Standard CSV | X-Achse: Datum + Zeit"
        return x_values, series, title_suffix, x_label

    def _convert_x_values(
        self,
        raw_x_values: list[str],
        x_axis_column: str,
    ) -> tuple[list[datetime] | list[int] | list[float] | list[str], str, bool]:
        """Convert raw X values to datetime, float, or keep them as strings.

        Matplotlib handles these three broad X-axis types differently, so
        we normalize them once here instead of scattering conversion logic
        across the parsing code.
        """
        if x_axis_column == self.ROW_INDEX_LABEL:
            return [int(value) for value in raw_x_values], self.ROW_INDEX_LABEL, False

        timestamp_values: list[datetime] = []
        if all((parsed := self._try_parse_timestamp(value)) is not None for value in raw_x_values):
            for value in raw_x_values:
                parsed = self._try_parse_timestamp(value)
                if parsed is None:
                    break
                timestamp_values.append(parsed)
            if len(timestamp_values) == len(raw_x_values):
                return timestamp_values, x_axis_column, True

        float_values: list[float] = []
        try:
            float_values = [float(value) for value in raw_x_values]
        except ValueError:
            return raw_x_values, x_axis_column, False
        return float_values, x_axis_column, False

    @staticmethod
    def _normalize_header(header: list[str]) -> list[str]:
        """Strip header cells and fill empty names with placeholders."""
        normalized: list[str] = []
        for index, value in enumerate(header, start=1):
            stripped = value.strip()
            normalized.append(stripped if stripped else f"column_{index}")
        return normalized

    @staticmethod
    def _get_row_value(row: list[str], index: int) -> str:
        """Safely return a row value or an empty string when the field is missing."""
        if index >= len(row):
            return ""
        return row[index]

    @classmethod
    def _is_float_row_value(cls, row: list[str], index: int) -> bool:
        """Check whether the given cell contains a float-compatible value."""
        value = cls._get_row_value(row, index).strip()
        if not value:
            return False
        try:
            float(value)
        except ValueError:
            return False
        return True

    @classmethod
    def _detect_timestamp_column(
        cls,
        header: list[str],
        sample_rows: list[list[str]],
    ) -> str | None:
        """Pick a likely timestamp column for plain CSV files."""
        preferred_names = {"timestamp", "time", "datetime", "date", "datum", "zeit"}
        for index, column_name in enumerate(header):
            normalized_name = column_name.strip().lower()
            if normalized_name in preferred_names and cls._column_looks_like_timestamp(sample_rows, index):
                return column_name

        for index, column_name in enumerate(header):
            if cls._column_looks_like_timestamp(sample_rows, index):
                return column_name
        return None

    @classmethod
    def _column_looks_like_timestamp(cls, rows: list[list[str]], index: int) -> bool:
        """Return True when at least one non-empty sample cell parses as a timestamp."""
        for row in rows[:50]:
            value = cls._get_row_value(row, index).strip()
            if not value:
                continue
            if cls._try_parse_timestamp(value) is not None:
                return True
        return False

    @staticmethod
    def _try_parse_timestamp(value: str) -> datetime | None:
        """Parse common timestamp formats used by generic CSV files."""
        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M",
            "%d.%m.%Y %H:%M:%S",
            "%d.%m.%Y %H:%M",
            "%d/%m/%Y %H:%M:%S",
            "%d/%m/%Y %H:%M",
            "%m/%d/%Y %H:%M:%S",
            "%m/%d/%Y %H:%M",
            "%Y-%m-%d",
            "%d.%m.%Y",
            "%d/%m/%Y",
            "%m/%d/%Y",
        ):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None


def main() -> int:
    """Start the desktop application."""
    root = tk.Tk()
    CsvPlotterApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
