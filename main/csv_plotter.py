#!/usr/bin/env python3
"""Interactive CSV plotter with column selection and zoomable charts."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
import sys
import traceback

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from functions.csv_parser import TIMESTAMP_COLUMN, open_csv_with_fallbacks
from functions.dependencies import ensure_dependencies, ensure_package

ensure_dependencies()
ensure_package("tkinterdnd2")

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
except ImportError as exc:
    raise SystemExit(
        "Missing dependency: tkinter. Install Python with Tcl/Tk support to run csv_plotter.py."
    ) from exc

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD  # noqa: E402
except ImportError:
    DND_FILES = None
    TkinterDnD = None

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk  # noqa: E402
from matplotlib import dates as mdates  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
from functions.csv_plotter_export import get_export_row_indices, write_plot_export  # noqa: E402
from functions.csv_plotter_interactions import (  # noqa: E402
    find_nearest_point,
    is_left_mouse_button,
    is_middle_mouse_button,
    pan_axes_from_drag,
    zoom_axes_around_cursor,
)
from functions.csv_plotter_logging import configure_csv_plotter_logging, log_exception  # noqa: E402
from functions.csv_plotter_utils import (  # noqa: E402
    XValue,
    convert_x_values,
    detect_timestamp_column,
    format_x_value,
    get_row_value,
    is_float_row_value,
    normalize_header,
)
from functions.csv_plotter_theme import THEMES  # noqa: E402
from functions.version_utils import read_project_version  # noqa: E402


APP_VERSION = read_project_version(ROOT_DIR)
LOGGER, LOG_FILE_PATH = configure_csv_plotter_logging(ROOT_DIR)
LOGGER.info("CSV-Plotter-Protokollierung gestartet. Version: %s | Log-Datei: %s", APP_VERSION, LOG_FILE_PATH)


def handle_unexpected_exception(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_traceback: object,
) -> None:
    """Protokolliert ungefangene Prozessfehler in die Log-Datei."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    LOGGER.error(
        "Unbehandelter Prozessfehler\n%s",
        "".join(traceback.format_exception(exc_type, exc_value, exc_traceback)),
    )


class CsvPlotterManager:
    """Verwaltet mehrere Plotter-Fenster innerhalb eines einzigen Tk-Prozesses."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.windows: list[CsvPlotterApp] = []
        self.root.withdraw()
        self.root.report_callback_exception = self._handle_tk_exception
        LOGGER.info("Fensterverwaltung initialisiert.")

    def open_new_window(self) -> "CsvPlotterApp":
        """Erzeugt ein neues, komplett eigenstaendiges Plotter-Fenster."""
        window = tk.Toplevel(self.root)
        app = CsvPlotterApp(window, manager=self)
        self.windows.append(app)
        LOGGER.info("Neues Plotter-Fenster geoeffnet. Aktive Fenster: %s", len(self.windows))
        return app

    def close_window(self, app: "CsvPlotterApp") -> None:
        """Schliesst den Prozess automatisch, wenn das letzte Fenster weg ist."""
        if app in self.windows:
            self.windows.remove(app)
            LOGGER.info("Plotter-Fenster geschlossen. Verbleibende Fenster: %s", len(self.windows))
        if not self.windows:
            LOGGER.info("Letztes Plotter-Fenster geschlossen. Anwendung wird beendet.")
            self.root.quit()
            self.root.destroy()

    def _handle_tk_exception(
        self,
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_traceback: object,
    ) -> None:
        """Faengt Tk-Callback-Fehler ab und schreibt sie in die Log-Datei."""
        LOGGER.error(
            "Unbehandelter Tk-Fehler\n%s",
            "".join(traceback.format_exception(exc_type, exc_value, exc_traceback)),
        )
        messagebox.showerror(
            "Unerwarteter Fehler",
            f"Der Plotter hat einen Fehler protokolliert.\nLog-Datei: {LOG_FILE_PATH}",
        )


class CsvPlotterApp:
    """Desktop UI for selecting CSV columns and plotting them interactively.

    The UI supports two file structures:

    - APS/APU exports with multiple logical tables in one file
    - regular CSV files with one header row

    Both end up in the same plotting path: choose X-axis values, choose
    numeric Y columns, then render the selected series.
    """

    ROW_INDEX_LABEL = "Zeilennummer"

    def __init__(self, root: tk.Misc, manager: CsvPlotterManager) -> None:
        self.root = root
        self.manager = manager
        self.root.title(f"CSV Plotter {APP_VERSION}")
        self.root.geometry("1400x900")
        self.root.protocol("WM_DELETE_WINDOW", self.close_window)
        LOGGER.info("Plotter-Fenster aufgebaut. Version: %s", APP_VERSION)

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
        self.drop_label: ttk.Label | None = None
        self.picker_annotation = None
        self.picker_marker = None
        self.current_plot_columns: list[str] = []
        self.current_x_values: list[XValue] = []
        self.current_series_map: dict[str, list[float]] = {}
        self.current_x_label = "X"
        self.middle_pan_start: tuple[float, float, tuple[float, float], tuple[float, float]] | None = None

        self._build_menu()
        self._configure_styles()
        self._build_ui()
        self._apply_theme_to_widgets()

    def _build_menu(self) -> None:
        """Create the application menu."""
        menu_bar = tk.Menu(self.root)

        datei_menu = tk.Menu(menu_bar, tearoff=False)
        datei_menu.add_command(label="Neues Fenster", command=self.manager.open_new_window)
        datei_menu.add_separator()
        export_menu = tk.Menu(datei_menu, tearoff=False)
        export_menu.add_command(label="Gesamten Plot exportieren", command=lambda: self.export_current_plot("all"))
        export_menu.add_command(
            label="Sichtbaren Ausschnitt exportieren",
            command=lambda: self.export_current_plot("visible"),
        )
        datei_menu.add_cascade(label="Export", menu=export_menu)
        datei_menu.add_separator()
        datei_menu.add_command(label="Fenster schliessen", command=self.close_window)
        menu_bar.add_cascade(label="Datei", menu=datei_menu)

        ansicht_menu = tk.Menu(menu_bar, tearoff=False)
        ansicht_menu.add_command(label="Dark Mode", command=lambda: self.set_theme("dark"))
        ansicht_menu.add_command(label="Light Mode", command=lambda: self.set_theme("light"))
        menu_bar.add_cascade(label="Ansicht", menu=ansicht_menu)

        hilfe_menu = tk.Menu(menu_bar, tearoff=False)
        hilfe_menu.add_command(label=f"Version: {APP_VERSION}", state="disabled")
        menu_bar.add_cascade(label="Hilfe", menu=hilfe_menu)
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

        self.drop_label = ttk.Label(
            controls,
            text="CSV hier ins Fenster ziehen oder ueber 'Datei oeffnen' laden.",
            wraplength=320,
            justify=tk.LEFT,
            style="Panel.TLabel",
        )
        self.drop_label.grid(row=3, column=0, sticky="ew", pady=(12, 0))

        ttk.Label(controls, text="Trennzeichen", style="Panel.TLabel").grid(row=4, column=0, sticky="w", pady=(16, 0))
        delimiter_entry = ttk.Entry(controls, textvariable=self.delimiter_var, width=8)
        delimiter_entry.grid(row=5, column=0, sticky="w", pady=(4, 0))

        ttk.Label(controls, text="Record Type", style="Panel.TLabel").grid(row=6, column=0, sticky="w", pady=(16, 0))
        self.record_type_box = ttk.Combobox(
            controls,
            textvariable=self.record_type_var,
            state="readonly",
            width=38,
        )
        self.record_type_box.grid(row=7, column=0, sticky="ew", pady=(4, 0))
        self.record_type_box.bind("<<ComboboxSelected>>", self.on_record_type_changed)

        ttk.Label(controls, text="System", style="Panel.TLabel").grid(row=8, column=0, sticky="w", pady=(16, 0))
        self.system_box = ttk.Combobox(
            controls,
            textvariable=self.system_name_var,
            state="readonly",
            width=38,
        )
        self.system_box.grid(row=9, column=0, sticky="ew", pady=(4, 0))
        self.system_box.bind("<<ComboboxSelected>>", self.on_system_changed)

        ttk.Label(controls, text="X-Achse", style="Panel.TLabel").grid(row=10, column=0, sticky="w", pady=(16, 0))
        self.x_axis_box = ttk.Combobox(
            controls,
            textvariable=self.x_axis_var,
            state="readonly",
            width=38,
        )
        self.x_axis_box.grid(row=11, column=0, sticky="ew", pady=(4, 0))

        ttk.Label(controls, text="Spalten", style="Panel.TLabel").grid(row=12, column=0, sticky="w", pady=(16, 0))
        list_frame = ttk.Frame(controls, style="Panel.TFrame")
        list_frame.grid(row=13, column=0, sticky="nsew", pady=(4, 0))
        controls.rowconfigure(13, weight=1)
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
        button_row.grid(row=14, column=0, sticky="ew", pady=(12, 0))
        button_row.columnconfigure(0, weight=1)
        button_row.columnconfigure(1, weight=1)
        ttk.Button(button_row, text="Alle waehlen", command=self.select_all_columns).grid(
            row=0, column=0, sticky="ew", padx=(0, 4)
        )
        ttk.Button(button_row, text="Auswahl loeschen", command=self.clear_column_selection).grid(
            row=0, column=1, sticky="ew", padx=(4, 0)
        )

        ttk.Button(controls, text="Plot anzeigen", command=self.plot_selected_columns).grid(
            row=15, column=0, sticky="ew", pady=(12, 0)
        )
        ttk.Label(
            controls,
            text="Zoom und Pan funktionieren ueber die Toolbar unter dem Plot.",
            wraplength=320,
            justify=tk.LEFT,
            style="Panel.TLabel",
        ).grid(row=16, column=0, sticky="w", pady=(12, 0))

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
        self.canvas.mpl_connect("button_press_event", self._on_plot_clicked)
        self.canvas.mpl_connect("scroll_event", self._on_mousewheel_zoom)
        self.canvas.mpl_connect("motion_notify_event", self._on_middle_pan_motion)
        self.canvas.mpl_connect("button_release_event", self._on_middle_pan_release)

        toolbar_frame = ttk.Frame(plot_frame)
        toolbar_frame.grid(row=1, column=0, sticky="ew")

        self.toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame, pack_toolbar=False)
        self.toolbar.update()
        self.toolbar.pack(fill=tk.X)

        status_bar = ttk.Label(main, textvariable=self.status_var, anchor="w", style="Status.TLabel")
        status_bar.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))

        self._enable_drag_and_drop(main, controls, plot_frame, self.canvas.get_tk_widget(), status_bar)

    def _enable_drag_and_drop(self, *widgets: tk.Widget) -> None:
        """Enable dropping CSV files onto the application window."""
        if DND_FILES is None:
            self.status_var.set("Drag & Drop nicht verfuegbar. tkinterdnd2 konnte nicht geladen werden.")
            return

        for widget in widgets:
            widget.drop_target_register(DND_FILES)
            widget.dnd_bind("<<Drop>>", self._on_file_dropped)

    def _on_file_dropped(self, event: object) -> None:
        """Load the first dropped CSV file."""
        dropped_files = self.root.tk.splitlist(event.data)
        if not dropped_files:
            return
        self.load_csv_path(dropped_files[0])

    def close_window(self) -> None:
        """Schliesst nur dieses Fenster und laesst andere Instanzen weiterlaufen."""
        self.root.destroy()
        self.manager.close_window(self)

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
        self._style_picker_artists()

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

    def _style_picker_artists(self) -> None:
        """Update picker annotation and marker colors to match the current theme."""
        colors = THEMES[self.theme_name]
        if self.picker_annotation is not None:
            self.picker_annotation.get_bbox_patch().set_facecolor(colors["input"])
            self.picker_annotation.get_bbox_patch().set_edgecolor(colors["grid"])
            self.picker_annotation.get_bbox_patch().set_alpha(0.95)
            # Matplotlib stellt den Pfeil je nach Version nicht immer ueber
            # dieselbe Methode bereit. Darum wird hier vorsichtig geprueft,
            # welcher Zugriff in der aktuellen Installation vorhanden ist.
            arrow_patch = getattr(self.picker_annotation, "arrow_patch", None)
            if arrow_patch is None and hasattr(self.picker_annotation, "get_arrow_patch"):
                arrow_patch = self.picker_annotation.get_arrow_patch()
            if arrow_patch is not None:
                arrow_patch.set_color(colors["grid"])
            self.picker_annotation.set_color(colors["text"])
        if self.picker_marker is not None:
            self.picker_marker.set_markerfacecolor(colors["accent"])
            self.picker_marker.set_markeredgecolor(colors["axis"])

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

        self.load_csv_path(file_name)

    def load_csv_path(self, file_path: str | Path) -> None:
        """Load a CSV file from a path and refresh the selector widgets."""
        path = Path(file_path)
        if path.suffix.lower() != ".csv":
            messagebox.showwarning("Keine CSV", "Bitte eine CSV-Datei ablegen oder auswaehlen.")
            LOGGER.info("Datei verworfen, weil sie keine CSV ist: %s", path)
            return
        if not path.exists():
            messagebox.showerror("Datei nicht gefunden", str(path))
            LOGGER.info("CSV-Datei nicht gefunden: %s", path)
            return

        self.csv_path = path
        self.file_var.set(str(self.csv_path))
        LOGGER.info("CSV-Datei wird geladen: %s", self.csv_path)

        try:
            self._load_metadata()
        except Exception as exc:
            log_exception(LOGGER, f"Fehler beim Laden der CSV-Datei: {path}", exc)
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
            LOGGER.info(
                "CSV-Datei erfolgreich geladen: %s | Modus: %s | Record Types: %s",
                self.csv_path.name,
                self.csv_mode,
                len(record_types),
            )
        else:
            self._reset_selectors()
            self.status_var.set("Keine auswertbaren Datensaetze in der CSV gefunden.")
            LOGGER.info("CSV-Datei enthaelt keine auswertbaren Datensaetze: %s", self.csv_path)

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
                    # Diese Schema-Zeile beschreibt, welche Spalten es fuer
                    # diesen Record Type gibt. Die spaeteren Datenzeilen werden
                    # anhand dieser Spaltenliste gelesen.
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

            normalized_header = normalize_header(header)
            if not normalized_header:
                raise ValueError("Die CSV-Datei enthaelt keine gueltige Header-Zeile.")

            sample_rows = [row for row in reader if any(cell.strip() for cell in row)]

        self.csv_mode = "plain"
        self.plain_columns = normalized_header
        self.timestamp_column = detect_timestamp_column(normalized_header, sample_rows)

        numeric_columns: list[str] = []
        for index, column_name in enumerate(normalized_header):
            if column_name == self.timestamp_column:
                continue
            if any(is_float_row_value(row, index) for row in sample_rows):
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
            log_exception(LOGGER, "Fehler beim Erstellen des Plots.", exc)
            messagebox.showerror("Plot fehlgeschlagen", str(exc))
            self.status_var.set("Plot konnte nicht erstellt werden.")
            return

        # Vor dem Neuaufbau des Diagramms werden vorhandene Marker und
        # Hinweisfelder entfernt, solange sie noch an der alten Zeichenflaeche haengen.
        self._clear_picker_artists()
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
        self.current_plot_columns = selected_columns
        self.current_x_values = x_values
        self.current_series_map = series_map
        self.current_x_label = x_label

        self.status_var.set(
            f"Plot aktualisiert: {len(selected_columns)} Spalten, {len(x_values)} Datenpunkte."
        )
        LOGGER.info(
            "Plot erstellt: Datei=%s | Spalten=%s | Datenpunkte=%s | X-Achse=%s",
            self.csv_path.name if self.csv_path is not None else "<unbekannt>",
            ", ".join(selected_columns),
            len(x_values),
            x_label,
        )

    def export_current_plot(self, export_scope: str) -> None:
        """Export the currently plotted data to a standalone CSV file."""
        if not self.has_plot or not self.current_x_values or not self.current_plot_columns:
            messagebox.showwarning("Kein Plot", "Bitte zuerst einen Plot erstellen.")
            return

        row_indices = get_export_row_indices(
            export_scope,
            self.current_x_values,
            self.current_series_map,
            self.current_plot_columns,
            self.axes.get_xlim(),
            self.axes.get_ylim(),
            self._to_plot_coordinate,
        )
        if not row_indices:
            messagebox.showwarning("Keine Daten", "Im gewaehlten Exportbereich liegen keine Datenpunkte.")
            return

        default_name = "plot_export.csv"
        if self.csv_path is not None:
            suffix = "sichtbar" if export_scope == "visible" else "gesamt"
            default_name = f"{self.csv_path.stem}_{suffix}.csv"

        output_path = filedialog.asksaveasfilename(
            title="Plot als CSV exportieren",
            defaultextension=".csv",
            initialdir=str(ROOT_DIR / "output" if (ROOT_DIR / "output").exists() else ROOT_DIR),
            initialfile=default_name,
            filetypes=[("CSV-Dateien", "*.csv"), ("Alle Dateien", "*.*")],
        )
        if not output_path:
            return

        try:
            write_plot_export(
                Path(output_path),
                self._get_delimiter(),
                self.current_x_label,
                self.current_x_values,
                self.current_plot_columns,
                self.current_series_map,
                row_indices,
            )
        except Exception as exc:
            log_exception(LOGGER, f"Fehler beim CSV-Export nach: {output_path}", exc)
            messagebox.showerror("Export fehlgeschlagen", str(exc))
            self.status_var.set("CSV-Export konnte nicht erstellt werden.")
            return

        self.status_var.set(f"CSV exportiert: {Path(output_path).name} ({len(row_indices)} Datenpunkte).")
        LOGGER.info(
            "Plot exportiert: Ziel=%s | Datenpunkte=%s | Modus=%s",
            output_path,
            len(row_indices),
            export_scope,
        )

    def _clear_picker_artists(self) -> None:
        """Remove the currently visible picker marker and tooltip from the axes."""
        if self.picker_annotation is not None:
            self._safe_remove_artist(self.picker_annotation)
            self.picker_annotation = None
        if self.picker_marker is not None:
            self._safe_remove_artist(self.picker_marker)
            self.picker_marker = None

    def _safe_remove_artist(self, artist: object) -> None:
        """Entfernt ein Matplotlib-Objekt nur dann hart, wenn das noch moeglich ist."""
        try:
            artist.remove()
        except (AttributeError, NotImplementedError, ValueError):
            # Manche Matplotlib-Objekte sind nach einem Achsen-Reset bereits
            # intern geloest. In diesem Fall reicht es, wenn unsere Referenz
            # spaeter verworfen wird.
            if hasattr(artist, "set_visible"):
                artist.set_visible(False)

    def _on_plot_clicked(self, event: object) -> None:
        """Highlight and describe the nearest plotted point after a mouse click."""
        if not self.has_plot or event.inaxes != self.axes:
            return
        if is_middle_mouse_button(event):
            self._start_middle_pan(event)
            return
        if self.toolbar.mode:
            return
        if not is_left_mouse_button(event):
            return
        if event.x is None or event.y is None:
            return
        if not self.current_x_values or not self.current_plot_columns:
            return

        nearest = find_nearest_point(
            self.axes,
            event.x,
            event.y,
            self.current_x_values,
            self.current_series_map,
            self.current_plot_columns,
            self._to_plot_coordinate,
        )
        if nearest is None:
            return

        column_name, point_index, x_value, y_value = nearest
        self._show_picked_point(column_name, point_index, x_value, y_value)

    def _on_mousewheel_zoom(self, event: object) -> None:
        """Zoom in/out around the mouse cursor."""
        if not self.has_plot or event.inaxes != self.axes:
            return
        if event.xdata is None or event.ydata is None:
            return

        zoom_factor = 1 / 1.2 if event.button == "up" else 1.2
        zoom_axes_around_cursor(self.axes, event.xdata, event.ydata, zoom_factor)
        self.toolbar.push_current()
        self.canvas.draw_idle()

    def _start_middle_pan(self, event: object) -> None:
        """Store the current view before middle-button drag panning starts."""
        if event.x is None or event.y is None:
            return
        self.middle_pan_start = (event.x, event.y, self.axes.get_xlim(), self.axes.get_ylim())

    def _on_middle_pan_motion(self, event: object) -> None:
        """Pan the plot while the middle mouse button is dragged."""
        if self.middle_pan_start is None or not self.has_plot:
            return
        if event.inaxes != self.axes or event.x is None or event.y is None:
            return

        start_x, start_y, start_xlim, start_ylim = self.middle_pan_start
        if pan_axes_from_drag(self.axes, start_x, start_y, event.x, event.y, start_xlim, start_ylim):
            self.canvas.draw_idle()

    def _on_middle_pan_release(self, event: object) -> None:
        """Finish middle-button drag panning and add the view to the toolbar history."""
        if self.middle_pan_start is None:
            return
        if is_middle_mouse_button(event):
            self.toolbar.push_current()
            self.middle_pan_start = None

    def _show_picked_point(
        self,
        column_name: str,
        point_index: int,
        x_value: datetime | int | float | str,
        y_value: float,
    ) -> None:
        """Draw a marker plus tooltip for the selected point and mirror it to the status bar."""
        self._clear_picker_artists()
        colors = THEMES[self.theme_name]

        self.picker_marker = self.axes.plot(
            [x_value],
            [y_value],
            marker="o",
            markersize=7,
            linestyle="None",
            markerfacecolor=colors["accent"],
            markeredgecolor=colors["axis"],
            markeredgewidth=1.0,
            zorder=5,
        )[0]

        tooltip_text = (
            f"{column_name}\n"
            f"Punkt: {point_index + 1}\n"
            f"X: {format_x_value(x_value)}\n"
            f"Y: {y_value:g}"
        )
        self.picker_annotation = self.axes.annotate(
            tooltip_text,
            xy=(x_value, y_value),
            xytext=(12, 12),
            textcoords="offset points",
            bbox={"boxstyle": "round,pad=0.3", "fc": colors["input"], "ec": colors["grid"], "alpha": 0.95},
            arrowprops={"arrowstyle": "->", "color": colors["grid"]},
            color=colors["text"],
            fontsize=9,
        )
        self.canvas.draw_idle()
        self.status_var.set(
            f"Messpunkt: {column_name} | Punkt {point_index + 1} | X={format_x_value(x_value)} | Y={y_value:g}"
        )

    def _to_plot_coordinate(self, x_value: XValue) -> float | int | str:
        """Convert X values to the numeric representation used by the current Matplotlib axis."""
        if isinstance(x_value, datetime):
            return mdates.date2num(x_value)
        converted = self.axes.xaxis.convert_units(x_value)
        if hasattr(converted, "item"):
            return converted.item()
        return converted

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
                    # Bei APS/APU-Dateien steht der Zeitstempel fest in Spalte 2.
                    # Alle benannten Daten-Spalten beginnen danach ab Spalte 3.
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
                    value = get_row_value(row, header_map[column]).strip()
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
                    raw_x_value = get_row_value(row, header_map[x_axis_column]).strip()
                    if not raw_x_value:
                        continue
                    raw_x_values.append(raw_x_value)

                for column, value in zip(selected_columns, parsed_values):
                    series[column].append(value)

        if not raw_x_values:
            raise ValueError(
                f"Keine plottbaren Datenzeilen fuer {record_type} / {system_name} gefunden."
            )

        x_values, x_label, _x_is_datetime = convert_x_values(raw_x_values, x_axis_column, self.ROW_INDEX_LABEL)
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

            normalized_header = normalize_header(header)
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
                    value = get_row_value(row, header_map[column]).strip()
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
                    raw_x_value = get_row_value(row, header_map[x_axis_column]).strip()
                    if not raw_x_value:
                        continue
                    raw_x_values.append(raw_x_value)

                for column, value in zip(selected_columns, parsed_values):
                    series[column].append(value)

        if not raw_x_values:
            raise ValueError("Keine plottbaren Datenzeilen fuer die aktuelle Auswahl gefunden.")

        x_values, x_label, x_is_datetime = convert_x_values(raw_x_values, x_axis_column, self.ROW_INDEX_LABEL)
        title_suffix = "Standard CSV"
        if x_axis_column != self.ROW_INDEX_LABEL:
            title_suffix = f"Standard CSV | X-Achse: {x_axis_column}"
        elif x_is_datetime:
            title_suffix = "Standard CSV | X-Achse: Datum + Zeit"
        return x_values, series, title_suffix, x_label

def main() -> int:
    """Start the desktop application."""
    sys.excepthook = handle_unexpected_exception
    LOGGER.info("CSV-Plotter wird gestartet. Version: %s", APP_VERSION)
    if TkinterDnD is not None:
        root = TkinterDnD.Tk()
        LOGGER.info("TkinterDnD aktiviert.")
    else:
        root = tk.Tk()
        LOGGER.info("TkinterDnD nicht verfuegbar. Standard-Tk wird verwendet.")
    manager = CsvPlotterManager(root)
    manager.open_new_window()
    root.mainloop()
    LOGGER.info("CSV-Plotter wurde beendet.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
