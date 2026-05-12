from __future__ import annotations

import json
import os
import subprocess
import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import matplotlib.pyplot as plt

plt.rcParams["toolbar"] = "None"
plt.rcParams["font.family"] = "Segoe UI"


TASK_DEFINITIONS = [
    {
        "id": "first-dirichlet-test",
        "tab": "1. Тестовая",
        "title": "Первая краевая тестовая задача",
        "subtitle": "Метод баланса, проверка по аналитическому решению",
        "owner": "Исполнитель 1",
        "expected": [
            "Построить тестовую задачу с кусочно-постоянными коэффициентами.",
            "Вывести u(x), v(x), u(x)-v(x) и величину epsilon_1.",
            "Проверить второй порядок изменения ошибки при сгущении сетки.",
        ],
    },
    {
        "id": "first-dirichlet-main",
        "tab": "2. Основная",
        "title": "Первая краевая основная задача",
        "subtitle": "Основная задача, сравнение решений на сетках n и 2n",
        "owner": "Исполнитель 2",
        "expected": [
            "Решить основную задачу с разрывными коэффициентами варианта 8.",
            "Вывести v(x), v2(x), v(x)-v2(x) и достигнутую точность epsilon_2.",
            "Построить таблицы порядка сходимости и широкий анализ по n.",
        ],
    },
    {
        "id": "mixed-test-classic",
        "tab": "3. Смеш. тест.",
        "title": "Смешанная краевая тестовая задача",
        "subtitle": "Классическая аппроксимация граничных условий",
        "owner": "Исполнитель 3",
        "expected": [
            "Собрать тестовую смешанную задачу с аналитическим решением.",
            "Реализовать классическую аппроксимацию граничных условий.",
            "Показать графики u(x), v(x), сеточной ошибки и таблицу порядка.",
        ],
    },
    {
        "id": "mixed-main-improved",
        "tab": "4. Смеш. осн. улучш.",
        "title": "Смешанная краевая основная задача",
        "subtitle": "Улучшенная аппроксимация граничных условий",
        "owner": "Смешанная краевая основная задача, улучш. аппрокс. ГУ",
        "expected": [
            "Решить основную задачу варианта 8 для смешанных граничных условий.",
            "Использовать улучшенную аппроксимацию граничных условий.",
            "Вывести v(x), v2(x), v(x)-v2(x), epsilon_2 и таблицы для отчета.",
        ],
    },
]


class RoundedFrame(tk.Canvas):
    def __init__(self, parent, bg_color="#ffffff", corner_radius=10, padding=12, autoresize=True, **kwargs):
        super().__init__(parent, highlightthickness=0, borderwidth=0, **kwargs)
        self.bg_color = bg_color
        self.corner_radius = corner_radius
        self.padding = padding
        self.autoresize = autoresize
        self.bind("<Configure>", self._on_resize)

        self.inner_frame = ttk.Frame(self, style="Card.TFrame")
        self.window_id = self.create_window(0, 0, window=self.inner_frame, anchor="nw")
        self.inner_frame.bind("<Configure>", self._on_inner_configure)

    def _on_inner_configure(self, event):
        if not self.autoresize:
            return
        target_height = event.height + 2 * self.padding
        if abs(self.winfo_height() - target_height) > 4:
            self.configure(height=target_height)

    def _on_resize(self, event):
        width, height = event.width, event.height
        self._draw_background(width, height)
        inner_width = max(1, width - 2 * self.padding)
        inner_height = max(1, height - 2 * self.padding)
        self.itemconfigure(self.window_id, width=inner_width, height=inner_height)
        self.coords(self.window_id, self.padding, self.padding)

    def _draw_background(self, width, height):
        self.delete("bg_rect")
        radius = min(self.corner_radius, width // 2, height // 2)
        self.create_rectangle(radius, 0, width - radius, height, fill=self.bg_color, outline=self.bg_color, tags="bg_rect")
        self.create_rectangle(0, radius, width, height - radius, fill=self.bg_color, outline=self.bg_color, tags="bg_rect")
        self.create_oval(0, 0, 2 * radius, 2 * radius, fill=self.bg_color, outline=self.bg_color, tags="bg_rect")
        self.create_oval(width - 2 * radius, 0, width, 2 * radius, fill=self.bg_color, outline=self.bg_color, tags="bg_rect")
        self.create_oval(0, height - 2 * radius, 2 * radius, height, fill=self.bg_color, outline=self.bg_color, tags="bg_rect")
        self.create_oval(width - 2 * radius, height - 2 * radius, width, height, fill=self.bg_color, outline=self.bg_color, tags="bg_rect")


class RoundedButton(tk.Canvas):
    def __init__(
        self,
        parent,
        text,
        command=None,
        width=130,
        height=36,
        bg_color="#3b82f6",
        fg_color="white",
        hover_color="#2563eb",
        corner_radius=18,
        font=None,
    ):
        try:
            parent_bg = parent["background"]
        except tk.TclError:
            parent_bg = "#ffffff"

        super().__init__(parent, width=width, height=height, highlightthickness=0, borderwidth=0, bg=parent_bg)
        self.command = command
        self.text = text
        self.bg_color = bg_color
        self.fg_color = fg_color
        self.hover_color = hover_color
        self.corner_radius = corner_radius
        self.font = font or ("Segoe UI", 9, "bold")
        self.rect_id = None
        self.text_id = None

        self._redraw(width, height, bg_color)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)
        self.bind("<Configure>", self._on_resize)

    def _rounded_rect(self, x, y, width, height, radius, color):
        radius = min(radius, width / 2, height / 2)
        points = [
            x + radius, y,
            x + width - radius, y,
            x + width, y,
            x + width, y + radius,
            x + width, y + height - radius,
            x + width, y + height,
            x + width - radius, y + height,
            x + radius, y + height,
            x, y + height,
            x, y + height - radius,
            x, y + radius,
            x, y,
        ]
        return self.create_polygon(points, smooth=True, fill=color, outline=color)

    def _redraw(self, width, height, color):
        self.delete("all")
        self.rect_id = self._rounded_rect(0, 0, width, height, self.corner_radius, color)
        self.text_id = self.create_text(width / 2, height / 2, text=self.text, fill=self.fg_color, font=self.font)

    def _on_resize(self, event):
        self._redraw(event.width, event.height, self.bg_color)

    def _on_enter(self, _event):
        self.itemconfig(self.rect_id, fill=self.hover_color, outline=self.hover_color)
        self.config(cursor="hand2")

    def _on_leave(self, _event):
        self.itemconfig(self.rect_id, fill=self.bg_color, outline=self.bg_color)
        self.config(cursor="")

    def _on_click(self, _event):
        if self.command:
            self.command()


class SegmentedTaskButton(tk.Canvas):
    def __init__(self, parent, text, command=None, width=220, height=40, font=None):
        super().__init__(parent, width=width, height=height, highlightthickness=0, borderwidth=0, bg="#ffffff")
        self.text = text
        self.command = command
        self.font = font or ("Segoe UI", 9, "bold")
        self.active = False
        self.hover = False
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)
        self.bind("<Configure>", lambda event: self._redraw(event.width, event.height))
        self._redraw(width, height)

    def set_active(self, active: bool) -> None:
        self.active = active
        self._redraw(self.winfo_width() or 1, self.winfo_height() or 1)

    def _rounded_rect(self, width, height, radius, fill, outline):
        radius = min(radius, width / 2, height / 2)
        pad = 2
        points = [
            pad + radius, pad,
            width - pad - radius, pad,
            width - pad, pad,
            width - pad, pad + radius,
            width - pad, height - pad - radius,
            width - pad, height - pad,
            width - pad - radius, height - pad,
            pad + radius, height - pad,
            pad, height - pad,
            pad, height - pad - radius,
            pad, pad + radius,
            pad, pad,
        ]
        self.create_polygon(points, smooth=True, fill=fill, outline=outline, width=1)

    def _redraw(self, width, height):
        self.delete("all")
        if self.active:
            fill, outline, fg = "#3b82f6", "#3b82f6", "#ffffff"
        elif self.hover:
            fill, outline, fg = "#e5e7eb", "#d1d5db", "#111827"
        else:
            fill, outline, fg = "#f9fafb", "#d1d5db", "#374151"
        self._rounded_rect(width, height, 18, fill, outline)
        self.create_text(width / 2, height / 2, text=self.text, fill=fg, font=self.font, width=max(40, width - 18))

    def _on_enter(self, _event):
        self.hover = True
        self.config(cursor="hand2")
        self._redraw(self.winfo_width(), self.winfo_height())

    def _on_leave(self, _event):
        self.hover = False
        self.config(cursor="")
        self._redraw(self.winfo_width(), self.winfo_height())

    def _on_click(self, _event):
        if self.command:
            self.command()


class CustomScrollbar(tk.Canvas):
    def __init__(self, parent, width=14, bg_color="#ffffff", thumb_color="#d1d5db", thumb_hover_color="#9ca3af", **kwargs):
        super().__init__(parent, width=width, highlightthickness=0, borderwidth=0, bg=bg_color, **kwargs)
        self.command = None
        self.thumb_color = thumb_color
        self.thumb_hover_color = thumb_hover_color
        self.top = 0.0
        self.bottom = 1.0
        self.dragging = False
        self.drag_start_y = 0
        self.drag_start_top = 0.0
        self.thumb_id = None
        self.bind("<Button-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Enter>", lambda _event: self._set_thumb(self.thumb_hover_color))
        self.bind("<Leave>", lambda _event: self._set_thumb(self.thumb_color) if not self.dragging else None)
        self.bind("<Configure>", lambda _event: self._redraw())

    def set(self, lo, hi):
        self.top = float(lo)
        self.bottom = float(hi)
        self._redraw()

    def _set_thumb(self, color):
        if self.thumb_id:
            self.itemconfig(self.thumb_id, fill=color)

    def _redraw(self):
        height = self.winfo_height()
        width = self.winfo_width()
        if height <= 0 or width <= 0:
            return
        self.delete("all")
        y1 = height * self.top
        y2 = max(y1 + 12, height * self.bottom)
        pad = 4
        self.thumb_id = self.create_rectangle(pad, y1, width - pad, min(height, y2), fill=self.thumb_color, outline="", width=0)

    def _on_press(self, event):
        if self.command is None:
            return
        height = max(1, self.winfo_height())
        y1 = height * self.top
        y2 = height * self.bottom
        if y1 <= event.y <= y2:
            self.dragging = True
            self.drag_start_y = event.y
            self.drag_start_top = self.top
            self._set_thumb(self.thumb_hover_color)
        else:
            self.command("moveto", event.y / height)

    def _on_drag(self, event):
        if self.dragging and self.command:
            self.command("moveto", self.drag_start_top + (event.y - self.drag_start_y) / max(1, self.winfo_height()))

    def _on_release(self, _event):
        self.dragging = False
        self._set_thumb(self.thumb_color)


class LabUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Лабораторная работа: решение краевых задач для ОДУ")
        self.geometry("1500x900")
        self.minsize(1220, 760)

        self.project_root = Path(__file__).resolve().parent.parent
        self.default_input = self.project_root / "input_examples" / "default_input.json"
        self.default_output = self.project_root / "output"
        self.default_output.mkdir(exist_ok=True)

        self.input_path_var = tk.StringVar(value=str(self.default_input))
        self.output_dir_var = tk.StringVar(value=str(self.default_output))
        self.solver_path_var = tk.StringVar(value=str(self._default_solver_path()))

        self.segments_var = tk.StringVar(value="20")
        self.tolerance_var = tk.StringVar(value="5e-7")
        self.refinement_var = tk.StringVar(value="2")
        self.max_segments_var = tk.StringVar(value="1000000")
        self.table_stride_var = tk.StringVar(value="1")
        self.text_scale_var = tk.DoubleVar(value=100.0)
        self.text_scale_label_var = tk.StringVar(value="100%")

        self.result_data: dict | None = None
        self.task_data_by_id: dict[str, dict] = {}
        self.task_widgets: dict[str, dict] = {}
        self.task_switch_buttons: dict[str, SegmentedTaskButton] = {}
        self.current_task_id = TASK_DEFINITIONS[0]["id"]
        self.config_card: RoundedFrame | None = None
        self.visualization_card: RoundedFrame | None = None
        self.variant_card: RoundedFrame | None = None
        self.task_switcher_card: RoundedFrame | None = None
        self.summary_card: RoundedFrame | None = None
        self._scale_after_id: str | None = None

        self.style = ttk.Style(self)
        self._init_fonts()
        self._configure_style()
        self._build_ui()
        self._load_input_file(self.default_input, show_message=False)

    def _init_fonts(self) -> None:
        self.font_specs = {
            "header": {"family": "Segoe UI", "size": 20, "weight": "bold"},
            "subheader": {"family": "Segoe UI", "size": 10},
            "label": {"family": "Segoe UI", "size": 9, "weight": "bold"},
            "section": {"family": "Segoe UI", "size": 11, "weight": "bold"},
            "body": {"family": "Segoe UI", "size": 10},
            "button": {"family": "Segoe UI", "size": 9, "weight": "bold"},
            "mono": {"family": "Consolas", "size": 10},
            "table": {"family": "Consolas", "size": 9},
            "table_heading": {"family": "Segoe UI", "size": 9, "weight": "bold"},
        }
        self.fonts = {name: tkfont.Font(root=self, **spec) for name, spec in self.font_specs.items()}

    def _scaled_size(self, base_size: int) -> int:
        return max(8, int(round(base_size * self.text_scale_var.get() / 100)))

    def _apply_font_scale(self) -> None:
        for name, spec in self.font_specs.items():
            self.fonts[name].configure(size=self._scaled_size(spec["size"]))
        self.text_scale_label_var.set(f"{int(round(self.text_scale_var.get()))}%")
        plt.rcParams["font.size"] = self.fonts["body"].cget("size")
        self._refresh_styles()
        self._resize_scaled_controls()

    def _resize_scaled_controls(self) -> None:
        if not hasattr(self, "task_switch_buttons"):
            return
        scale = self.text_scale_var.get() / 100.0
        if hasattr(self, "sidebar_frame"):
            self.sidebar_frame.configure(width=int(round(540 * min(scale, 1.25))))
        height = int(round(40 * scale))
        for button in self.task_switch_buttons.values():
            button.configure(height=height)
            button._redraw(button.winfo_width() or 1, height)
        if self.config_card is not None:
            self.config_card.configure(height=int(round(500 * min(scale, 1.45))))
        if self.visualization_card is not None:
            self.visualization_card.configure(height=int(round(205 * scale)))
        if self.variant_card is not None:
            self.variant_card.configure(height=int(round(140 * scale)))
        if self.task_switcher_card is not None:
            self.task_switcher_card.configure(height=int(round(96 * scale)))
        if self.summary_card is not None:
            self.summary_card.configure(height=int(round(300 * min(scale, 1.25))))

    def _on_text_scale_changed(self, value: str) -> None:
        scale = max(100.0, min(160.0, float(value)))
        self.text_scale_label_var.set(f"{int(round(scale))}%")
        if self._scale_after_id is not None:
            self.after_cancel(self._scale_after_id)
        self._scale_after_id = self.after(80, self._apply_font_scale)

    def _configure_style(self) -> None:
        self.configure(bg="#f3f4f6")
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass
        self._apply_font_scale()

    def _refresh_styles(self) -> None:
        self.style.configure("TFrame", background="#f3f4f6")
        self.style.configure("Card.TFrame", background="#ffffff")
        self.style.configure("TLabel", background="#f3f4f6", foreground="#111827", font=self.fonts["body"])
        self.style.configure("Header.TLabel", font=self.fonts["header"], background="#f3f4f6", foreground="#111827")
        self.style.configure("Subheader.TLabel", font=self.fonts["subheader"], background="#f3f4f6", foreground="#6b7280")
        self.style.configure("Card.TLabel", background="#ffffff", foreground="#111827", font=self.fonts["body"])
        self.style.configure("Field.TLabel", font=self.fonts["label"], background="#ffffff", foreground="#374151")
        self.style.configure("Section.TLabel", font=self.fonts["section"], background="#ffffff", foreground="#111827")
        self.style.configure("TButton", font=self.fonts["body"])
        self.style.configure("TNotebook", background="#f3f4f6", borderwidth=0)
        self.style.configure("TNotebook.Tab", font=self.fonts["body"], padding=(14, 8))
        self.style.configure("TEntry", font=self.fonts["body"], fieldbackground="#f9fafb", foreground="#1f2937", padding=(8, 7))
        self.style.configure(
            "Treeview",
            font=self.fonts["table"],
            rowheight=self.fonts["table"].metrics("linespace") + 12,
            background="#ffffff",
            fieldbackground="#ffffff",
            foreground="#1f2937",
            borderwidth=0,
        )
        self.style.configure(
            "Treeview.Heading",
            font=self.fonts["table_heading"],
            background="#f3f4f6",
            foreground="#6b7280",
            relief="flat",
            padding=(8, 8),
        )

    def _default_solver_path(self) -> Path:
        candidates = [
            self.project_root / "build" / "Release" / "bvp_solver.exe",
            self.project_root / "build" / "Debug" / "bvp_solver.exe",
            self.project_root / "build" / "bvp_solver.exe",
            self.project_root / "build" / "bvp_solver",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return candidates[0]

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=12)
        root.pack(fill=tk.BOTH, expand=True)

        header_row = ttk.Frame(root)
        header_row.pack(fill=tk.X)
        left_header = ttk.Frame(header_row)
        left_header.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(left_header, text="Решение краевых задач для ОДУ", style="Header.TLabel").pack(anchor=tk.W)
        ttk.Label(
            left_header,
            text="Лабораторная работа №3, вариант 8. Команда №6.",
            style="Subheader.TLabel",
        ).pack(anchor=tk.W, pady=(0, 10))

        scale_frame = ttk.Frame(header_row)
        scale_frame.pack(side=tk.RIGHT, anchor=tk.NE)
        ttk.Label(scale_frame, text="Масштаб текста", style="Subheader.TLabel").pack(anchor=tk.E)
        ttk.Scale(scale_frame, from_=100, to=160, variable=self.text_scale_var, command=self._on_text_scale_changed, length=160).pack(side=tk.LEFT)
        ttk.Label(scale_frame, textvariable=self.text_scale_label_var, style="Subheader.TLabel", width=5).pack(side=tk.LEFT, padx=(8, 0))

        workspace = ttk.Frame(root)
        workspace.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

        sidebar_shell = ttk.Frame(workspace, width=540)
        self.sidebar_frame = sidebar_shell
        sidebar_shell.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 12))
        sidebar_shell.pack_propagate(False)

        sidebar_canvas = tk.Canvas(sidebar_shell, highlightthickness=0, borderwidth=0, bg="#f3f4f6")
        sidebar_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sidebar_scrollbar = CustomScrollbar(sidebar_shell, width=12, bg_color="#f3f4f6", thumb_color="#d1d5db", thumb_hover_color="#9ca3af")
        sidebar_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        sidebar_scrollbar.command = sidebar_canvas.yview
        sidebar_canvas.configure(yscrollcommand=sidebar_scrollbar.set)

        sidebar = ttk.Frame(sidebar_canvas)
        sidebar_window = sidebar_canvas.create_window(0, 0, window=sidebar, anchor="nw")
        sidebar.bind("<Configure>", lambda _event: sidebar_canvas.configure(scrollregion=sidebar_canvas.bbox("all")))
        sidebar_canvas.bind("<Configure>", lambda event: sidebar_canvas.itemconfigure(sidebar_window, width=event.width))
        self._bind_mousewheel_scroll(sidebar_canvas, sidebar_canvas)
        self._bind_mousewheel_scroll(sidebar, sidebar_canvas)

        main = ttk.Frame(workspace)
        main.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._create_sidebar_config(sidebar)
        self._create_visualization_card(sidebar)
        self._create_sidebar_variant(sidebar)
        self._create_task_switcher(main)
        self._create_summary_and_table(main)

        self.select_task(self.current_task_id)

    def _create_sidebar_config(self, parent) -> None:
        card = RoundedFrame(parent, height=500, bg_color="#ffffff", corner_radius=12, padding=14, autoresize=False, bg="#f3f4f6")
        self.config_card = card
        card.pack(fill=tk.X, pady=(0, 12))
        inner = card.inner_frame

        ttk.Label(inner, text="Конфигурация и ввод", style="Section.TLabel").pack(anchor=tk.W, pady=(0, 12))
        self._create_path_row(inner, "Solver", self.solver_path_var, self.pick_solver)
        self._create_path_row(inner, "Input JSON", self.input_path_var, self.pick_input)
        self._create_path_row(inner, "Output dir", self.output_dir_var, self.pick_output)

        ttk.Label(inner, text="Параметры расчета", style="Section.TLabel").pack(anchor=tk.W, pady=(10, 8))
        self._create_param_row(inner, "n", self.segments_var, "epsilon", self.tolerance_var)
        self._create_param_row(inner, "Сгущение", self.refinement_var, "max n", self.max_segments_var)
        self._create_param_row(inner, "Шаг таблицы", self.table_stride_var)

        buttons = ttk.Frame(inner, style="Card.TFrame")
        buttons.pack(fill=tk.X, pady=(18, 0))
        RoundedButton(buttons, text="Запустить расчет", command=self.run_solver, width=500, height=46, font=self.fonts["button"]).pack(fill=tk.X, pady=(0, 12))
        RoundedButton(
            buttons,
            text="Загрузить готовый результат",
            command=self.load_result_from_output,
            width=500,
            height=46,
            bg_color="#e5e7eb",
            fg_color="#111827",
            hover_color="#d1d5db",
            font=self.fonts["button"],
        ).pack(fill=tk.X)

    def _create_visualization_card(self, parent) -> None:
        card = RoundedFrame(parent, height=205, bg_color="#ffffff", corner_radius=12, padding=14, autoresize=False, bg="#f3f4f6")
        self.visualization_card = card
        card.pack(fill=tk.X, pady=(0, 12))
        inner = card.inner_frame

        ttk.Label(inner, text="Визуализация", style="Section.TLabel").pack(anchor=tk.W, pady=(0, 12))
        RoundedButton(
            inner,
            text="График решения",
            command=lambda: self.plot_task(self.current_task_id, "solution"),
            width=500,
            height=34,
            bg_color="#e5e7eb",
            fg_color="#111827",
            hover_color="#d1d5db",
            font=self.fonts["button"],
        ).pack(fill=tk.X, pady=(0, 8))
        RoundedButton(
            inner,
            text="График разности",
            command=lambda: self.plot_task(self.current_task_id, "difference"),
            width=500,
            height=34,
            bg_color="#e5e7eb",
            fg_color="#111827",
            hover_color="#d1d5db",
            font=self.fonts["button"],
        ).pack(fill=tk.X, pady=(0, 8))
        RoundedButton(
            inner,
            text="Сохранить input",
            command=self.save_input_dialog,
            width=500,
            height=34,
            bg_color="#0d9488",
            hover_color="#0f766e",
            font=self.fonts["button"],
        ).pack(fill=tk.X)

    def _create_sidebar_variant(self, parent) -> None:
        card = RoundedFrame(parent, height=140, bg_color="#ffffff", corner_radius=12, padding=14, autoresize=False, bg="#f3f4f6")
        self.variant_card = card
        card.pack(fill=tk.X)
        inner = card.inner_frame
        ttk.Label(inner, text="Вариант 8", style="Section.TLabel").pack(anchor=tk.W, pady=(0, 8))
        text = (
            "xi = 1/sqrt(3),  mu1 = 2,  mu2 = 1\n"
            "k1(x)=1,  k2(x)=exp(x^2)\n"
            "q1(x)=x^2,  q2(x)=1+x^4\n"
            "f1(x)=x^2-1,  f2(x)=1"
        )
        ttk.Label(inner, text=text, style="Card.TLabel", justify=tk.LEFT).pack(anchor=tk.W)

    def _create_task_switcher(self, parent) -> None:
        card = RoundedFrame(parent, height=96, bg_color="#ffffff", corner_radius=12, padding=12, autoresize=False, bg="#f3f4f6")
        self.task_switcher_card = card
        card.pack(fill=tk.X, pady=(0, 12))
        inner = card.inner_frame

        ttk.Label(inner, text="Задание", style="Section.TLabel").pack(side=tk.LEFT, padx=(0, 14))
        buttons = ttk.Frame(inner, style="Card.TFrame")
        buttons.pack(side=tk.LEFT, fill=tk.X, expand=True)
        for column, task_def in enumerate(TASK_DEFINITIONS):
            button = SegmentedTaskButton(
                buttons,
                text=task_def["tab"],
                command=lambda task_id=task_def["id"]: self.select_task(task_id),
                width=220,
                height=40,
                font=self.fonts["button"],
            )
            button.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 5, 0 if column == len(TASK_DEFINITIONS) - 1 else 5))
            buttons.columnconfigure(column, weight=1, uniform="tasks")
            self.task_switch_buttons[task_def["id"]] = button

    def _create_summary_and_table(self, parent) -> None:
        summary_card = RoundedFrame(parent, height=300, bg_color="#ffffff", corner_radius=12, padding=14, autoresize=False, bg="#f3f4f6")
        self.summary_card = summary_card
        summary_card.pack(fill=tk.X, pady=(0, 12))
        summary_inner = summary_card.inner_frame
        ttk.Label(summary_inner, text="Сводка результатов", style="Section.TLabel").pack(anchor=tk.W, pady=(0, 8))
        summary = tk.Text(summary_inner, height=11, wrap="word", font=self.fonts["mono"], relief="flat", bg="#ffffff", fg="#1f2937")
        summary.pack(fill=tk.BOTH, expand=True)
        summary.configure(state=tk.DISABLED)

        table_card = RoundedFrame(parent, bg_color="#ffffff", corner_radius=12, padding=14, autoresize=False, bg="#f3f4f6")
        table_card.pack(fill=tk.BOTH, expand=True)
        table_inner = table_card.inner_frame
        table_header = ttk.Frame(table_inner, style="Card.TFrame")
        table_header.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(table_header, text="Таблица результатов", style="Section.TLabel").pack(side=tk.LEFT)
        ttk.Label(table_header, text="Набор данных:", style="Field.TLabel").pack(side=tk.RIGHT, padx=(8, 0))

        table_container = ttk.Frame(table_inner, style="Card.TFrame")
        table_container.pack(fill=tk.BOTH, expand=True)
        scrollbar = CustomScrollbar(table_container, width=12, bg_color="#ffffff", thumb_color="#d1d5db", thumb_hover_color="#9ca3af")
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        table = ttk.Treeview(table_container, show="headings", yscrollcommand=scrollbar.set)
        table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.command = table.yview

        for task_def in TASK_DEFINITIONS:
            self.task_widgets[task_def["id"]] = {
                "summary": summary,
                "table": table,
                "definition": task_def,
            }

    def _create_paths_card(self, parent) -> None:
        card = RoundedFrame(parent, height=176, bg_color="#ffffff", corner_radius=10, padding=12, autoresize=False, bg="#f3f4f6")
        card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        inner = card.inner_frame
        ttk.Label(inner, text="Пути", style="Section.TLabel").pack(anchor=tk.W, pady=(0, 8))
        self._create_path_row(inner, "Solver", self.solver_path_var, self.pick_solver)
        self._create_path_row(inner, "Input JSON", self.input_path_var, self.pick_input)
        self._create_path_row(inner, "Output dir", self.output_dir_var, self.pick_output)

    def _create_params_card(self, parent) -> None:
        card = RoundedFrame(parent, height=176, bg_color="#ffffff", corner_radius=10, padding=12, autoresize=False, bg="#f3f4f6")
        card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        inner = card.inner_frame
        ttk.Label(inner, text="Параметры расчета", style="Section.TLabel").pack(anchor=tk.W, pady=(0, 8))
        self._create_param_row(inner, "n", self.segments_var, "epsilon", self.tolerance_var)
        self._create_param_row(inner, "Сгущение", self.refinement_var, "max n", self.max_segments_var)
        self._create_param_row(inner, "Шаг таблицы", self.table_stride_var)

    def _create_variant_card(self, parent) -> None:
        card = RoundedFrame(parent, height=176, bg_color="#ffffff", corner_radius=10, padding=12, autoresize=False, bg="#f3f4f6")
        card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        inner = card.inner_frame
        ttk.Label(inner, text="Вариант 8", style="Section.TLabel").pack(anchor=tk.W, pady=(0, 8))
        text = (
            "xi = 1/sqrt(3),  mu1 = 2,  mu2 = 1\n"
            "k1(x)=1,  k2(x)=exp(x^2)\n"
            "q1(x)=x^2,  q2(x)=1+x^4\n"
            "f1(x)=x^2-1,  f2(x)=1"
        )
        ttk.Label(inner, text=text, style="Card.TLabel", justify=tk.LEFT).pack(anchor=tk.W)

    def _create_path_row(self, parent, label, variable, command) -> None:
        row = ttk.Frame(parent, style="Card.TFrame")
        row.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(row, text=label, style="Field.TLabel", width=10).pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=variable).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 8))
        ttk.Button(row, text="...", width=3, command=command).pack(side=tk.RIGHT)

    def _create_param_row(self, parent, label1, var1, label2=None, var2=None) -> None:
        row = ttk.Frame(parent, style="Card.TFrame")
        row.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(row, text=label1, style="Field.TLabel", width=14).pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=var1, width=12).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 12))
        if label2 and var2:
            ttk.Label(row, text=label2, style="Field.TLabel", width=12).pack(side=tk.LEFT)
            ttk.Entry(row, textvariable=var2, width=12).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0))

    def _create_task_tab(self, task_def: dict) -> None:
        frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(frame, text=task_def["tab"])

        top = ttk.Frame(frame)
        top.pack(fill=tk.X)

        info = RoundedFrame(top, height=245, bg_color="#ffffff", corner_radius=10, padding=14, autoresize=False, bg="#f3f4f6")
        info.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        info_inner = info.inner_frame
        ttk.Label(info_inner, text=task_def["title"], style="Section.TLabel").pack(anchor=tk.W)
        ttk.Label(info_inner, text=task_def["subtitle"], style="Card.TLabel", foreground="#6b7280").pack(anchor=tk.W, pady=(2, 10))
        ttk.Label(info_inner, text=f"Ответственный блок: {task_def['owner']}", style="Field.TLabel").pack(anchor=tk.W, pady=(0, 8))
        for line in task_def["expected"]:
            ttk.Label(info_inner, text=f"- {line}", style="Card.TLabel", justify=tk.LEFT).pack(anchor=tk.W, pady=(0, 2))

        summary_card = RoundedFrame(top, height=245, bg_color="#ffffff", corner_radius=10, padding=14, autoresize=False, bg="#f3f4f6")
        summary_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        summary_inner = summary_card.inner_frame
        ttk.Label(summary_inner, text="Справка и состояние", style="Section.TLabel").pack(anchor=tk.W, pady=(0, 8))
        summary = tk.Text(summary_inner, height=9, wrap="word", font=self.fonts["mono"], relief="flat", bg="#ffffff", fg="#1f2937")
        summary.pack(fill=tk.BOTH, expand=True)
        summary.insert(tk.END, self._default_summary(task_def))
        summary.configure(state=tk.DISABLED)

        controls = ttk.Frame(frame)
        controls.pack(fill=tk.X, pady=(10, 10))
        RoundedButton(
            controls,
            text="График решения",
            command=lambda task_id=task_def["id"]: self.plot_task(task_id, "solution"),
            width=140,
            bg_color="#e5e7eb",
            fg_color="#374151",
            hover_color="#d1d5db",
            font=self.fonts["button"],
        ).pack(side=tk.LEFT, padx=(0, 8))
        RoundedButton(
            controls,
            text="График разности",
            command=lambda task_id=task_def["id"]: self.plot_task(task_id, "difference"),
            width=140,
            bg_color="#e5e7eb",
            fg_color="#374151",
            hover_color="#d1d5db",
            font=self.fonts["button"],
        ).pack(side=tk.LEFT, padx=(0, 8))

        table_card = RoundedFrame(frame, bg_color="#ffffff", corner_radius=10, padding=14, autoresize=False, bg="#f3f4f6")
        table_card.pack(fill=tk.BOTH, expand=True)
        table_card.configure(height=420)
        table_inner = table_card.inner_frame
        ttk.Label(table_inner, text="Таблица результатов", style="Section.TLabel").pack(anchor=tk.W, pady=(0, 8))
        table_container = ttk.Frame(table_inner, style="Card.TFrame")
        table_container.pack(fill=tk.BOTH, expand=True)
        scrollbar = CustomScrollbar(table_container, width=12, bg_color="#ffffff", thumb_color="#d1d5db", thumb_hover_color="#9ca3af")
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        table = ttk.Treeview(table_container, show="headings", yscrollcommand=scrollbar.set)
        table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.command = table.yview

        self.task_widgets[task_def["id"]] = {
            "summary": summary,
            "table": table,
            "definition": task_def,
        }
        self._fill_table_placeholder(table, task_def["id"])

    def _default_summary(self, task_def: dict) -> str:
        return (
            "Статус: UI-заготовка готова, C++ численная реализация будет добавлена позже.\n"
            f"Задача: {task_def['title']}.\n"
            "Формат результата уже ожидает result.json от bvp_solver.\n"
            "После реализации backend должен вернуть строки таблицы, справку, epsilon_1/epsilon_2 и данные для графиков."
        )

    def _build_input_payload(self) -> dict:
        try:
            payload = {
                "segments": int(self.segments_var.get()),
                "tolerance": float(self.tolerance_var.get()),
                "refinementMultiplier": int(self.refinement_var.get()),
                "maxSegments": int(self.max_segments_var.get()),
                "tableStride": int(self.table_stride_var.get()),
            }
        except ValueError as ex:
            raise ValueError("Проверьте числовые параметры расчета.") from ex
        if payload["segments"] <= 0 or payload["tolerance"] <= 0:
            raise ValueError("n и epsilon должны быть положительными.")
        return payload

    def _load_input_file(self, path: Path, show_message=True) -> None:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as ex:
            if show_message:
                messagebox.showerror("Ошибка", f"Не удалось открыть input JSON:\n{ex}")
            return

        self.input_path_var.set(str(path))
        self.segments_var.set(str(data.get("segments", self.segments_var.get())))
        self.tolerance_var.set(str(data.get("tolerance", self.tolerance_var.get())))
        self.refinement_var.set(str(data.get("refinementMultiplier", self.refinement_var.get())))
        self.max_segments_var.set(str(data.get("maxSegments", self.max_segments_var.get())))
        self.table_stride_var.set(str(data.get("tableStride", self.table_stride_var.get())))

    def pick_solver(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("Исполняемые файлы", "*.exe"), ("Все файлы", "*.*")])
        if path:
            self.solver_path_var.set(path)

    def pick_input(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("Файлы JSON", "*.json")])
        if path:
            self._load_input_file(Path(path))

    def pick_output(self) -> None:
        path = filedialog.askdirectory()
        if path:
            self.output_dir_var.set(path)

    def save_input_dialog(self) -> None:
        try:
            payload = self._build_input_payload()
        except Exception as ex:
            messagebox.showerror("Ошибка ввода", str(ex))
            return

        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("Файлы JSON", "*.json")])
        if not path:
            return
        Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        self.input_path_var.set(path)

    def run_solver(self) -> None:
        solver = Path(self.solver_path_var.get())
        if not solver.exists():
            messagebox.showerror("Ошибка", "Не найден bvp_solver. Сначала соберите проект через .\\run.ps1 -Mode build")
            return

        try:
            payload = self._build_input_payload()
        except Exception as ex:
            messagebox.showerror("Ошибка ввода", str(ex))
            return

        output_dir = Path(self.output_dir_var.get())
        output_dir.mkdir(parents=True, exist_ok=True)
        input_json = output_dir / "_ui_runtime_input.json"
        input_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        try:
            completed = subprocess.run(
                [str(solver), str(input_json), str(output_dir)],
                capture_output=True,
                text=True,
                check=True,
                encoding="utf-8",
                errors="replace",
            )
        except subprocess.CalledProcessError as ex:
            messagebox.showerror("Ошибка запуска", ex.stderr or ex.stdout or str(ex))
            return

        self.load_result_from_output(show_error=True)
        messagebox.showinfo("Готово", completed.stdout.strip() or "Расчет завершен.")

    def load_result_from_output(self, show_error=True) -> None:
        result_path = Path(self.output_dir_var.get()) / "result.json"
        try:
            self.result_data = json.loads(result_path.read_text(encoding="utf-8"))
        except Exception as ex:
            if show_error:
                messagebox.showerror("Ошибка", f"Не удалось открыть result.json:\n{ex}")
            return

        self.task_data_by_id = {task["id"]: task for task in self.result_data.get("tasks", [])}
        self.refresh_task(self.current_task_id)

    def select_task(self, task_id: str) -> None:
        self.current_task_id = task_id
        for current_id, button in self.task_switch_buttons.items():
            button.set_active(current_id == task_id)
        self.refresh_task(task_id)

    def refresh_task(self, task_id: str) -> None:
        widgets = self.task_widgets[task_id]
        task_def = widgets["definition"]
        task = self.task_data_by_id.get(task_id)
        summary = widgets["summary"]

        summary.configure(state=tk.NORMAL)
        summary.delete("1.0", tk.END)
        if not task:
            summary.insert(tk.END, self._default_summary(task_def))
            self._fill_table_placeholder(widgets["table"], task_id)
        else:
            summary.insert(tk.END, self._format_task_summary(task, task_def))
            self._fill_task_table(widgets["table"], task)
        summary.configure(state=tk.DISABLED)

    def _format_task_summary(self, task: dict, task_def: dict) -> str:
        status = task.get("status", "unknown")
        note = task.get("note", "")
        rows_count = len(task.get("rows", []))
        return (
            f"Статус: {status}\n"
            f"Задача: {task.get('title', task_def['title'])}\n"
            f"Тип условий: {task.get('boundaryKind', '')}\n"
            f"Аппроксимация: {task.get('approximationKind', '')}\n"
            f"Работу выполнил(а): {task.get('ownerHint', task_def['owner'])}\n"
            f"Строк таблицы: {rows_count}\n\n"
            f"{note}"
        )

    def _fill_table_placeholder(self, table: ttk.Treeview, task_id: str) -> None:
        if task_id in {"first-dirichlet-test", "mixed-test-classic"}:
            columns = [("index", "i", 70), ("x", "x_i", 120), ("u", "u(x_i)", 140), ("v", "v(x_i)", 140), ("difference", "u-v", 140)]
        else:
            columns = [("index", "i", 70), ("x", "x_i", 120), ("v", "v(x_i)", 140), ("v2", "v2(x_2i)", 140), ("difference", "v-v2", 140)]
        self._setup_columns(table, columns)
        table.delete(*table.get_children())

    def _fill_task_table(self, table: ttk.Treeview, task: dict) -> None:
        columns = []
        for column in task.get("columns", []):
            columns.append((column["key"], column["title"], 135 if column["key"] != "index" else 70))
        if not columns:
            self._fill_table_placeholder(table, task["id"])
            return

        self._setup_columns(table, columns)
        table.delete(*table.get_children())
        for row in task.get("rows", []):
            values = [self._format_cell(row.get(key)) for key, _title, _width in columns]
            table.insert("", tk.END, values=values)

    def _setup_columns(self, table: ttk.Treeview, columns) -> None:
        table["columns"] = [column[0] for column in columns]
        for key, title, width in columns:
            table.heading(key, text=title)
            table.column(key, width=width, stretch=True)

    def _bind_mousewheel_scroll(self, widget, canvas) -> None:
        def on_mousewheel(event) -> None:
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        widget.bind("<Enter>", lambda _event: canvas.bind_all("<MouseWheel>", on_mousewheel))
        widget.bind("<Leave>", lambda _event: canvas.unbind_all("<MouseWheel>"))

    def _enable_plot_zoom(self, fig, axes) -> None:
        axes_list = list(axes if isinstance(axes, (list, tuple)) else [axes])
        initial_limits = [(axis.get_xlim(), axis.get_ylim()) for axis in axes_list]
        drag_state = {"axis": None, "x": 0.0, "y": 0.0, "xlim": None, "ylim": None}

        def on_scroll(event):
            if event.inaxes not in axes_list or event.xdata is None or event.ydata is None:
                return
            axis = event.inaxes
            scale = 0.8 if event.button == "up" else 1.25
            x_left, x_right = axis.get_xlim()
            y_bottom, y_top = axis.get_ylim()
            new_width = (x_right - x_left) * scale
            new_height = (y_top - y_bottom) * scale
            rel_x = (x_right - event.xdata) / (x_right - x_left)
            rel_y = (y_top - event.ydata) / (y_top - y_bottom)
            axis.set_xlim(event.xdata - new_width * (1 - rel_x), event.xdata + new_width * rel_x)
            axis.set_ylim(event.ydata - new_height * (1 - rel_y), event.ydata + new_height * rel_y)
            fig.canvas.draw_idle()

        def on_press(event):
            if event.button != 1 or event.inaxes not in axes_list:
                return
            drag_state["axis"] = event.inaxes
            drag_state["x"] = event.x
            drag_state["y"] = event.y
            drag_state["xlim"] = event.inaxes.get_xlim()
            drag_state["ylim"] = event.inaxes.get_ylim()

        def on_motion(event):
            axis = drag_state["axis"]
            if axis is None:
                return
            x_left, x_right = drag_state["xlim"]
            y_bottom, y_top = drag_state["ylim"]
            bbox = axis.get_window_extent()
            if bbox.width <= 0 or bbox.height <= 0:
                return
            dx = (event.x - drag_state["x"]) / bbox.width * (x_right - x_left)
            dy = (event.y - drag_state["y"]) / bbox.height * (y_top - y_bottom)
            axis.set_xlim(x_left - dx, x_right - dx)
            axis.set_ylim(y_bottom - dy, y_top - dy)
            fig.canvas.draw_idle()

        def on_release(_event):
            drag_state["axis"] = None

        def on_key(event):
            if event.key not in {"r", "к"}:
                return
            for axis, (xlim, ylim) in zip(axes_list, initial_limits):
                axis.set_xlim(xlim)
                axis.set_ylim(ylim)
            fig.canvas.draw_idle()

        fig.canvas.mpl_connect("scroll_event", on_scroll)
        fig.canvas.mpl_connect("button_press_event", on_press)
        fig.canvas.mpl_connect("motion_notify_event", on_motion)
        fig.canvas.mpl_connect("button_release_event", on_release)
        fig.canvas.mpl_connect("key_press_event", on_key)

    def plot_task(self, task_id: str, mode: str) -> None:
        task = self.task_data_by_id.get(task_id)
        if not task or not task.get("rows"):
            messagebox.showinfo("График", "Данные для графика появятся после реализации C++-расчета.")
            return

        rows = task["rows"]
        x = [row["x"] for row in rows]
        column_keys = {column.get("key") for column in task.get("columns", [])}
        fig, ax = plt.subplots(num=task.get("shortTitle", "График"), figsize=(9.8, 5.8), clear=True)
        if mode == "solution":
            if "u" in column_keys:
                ax.plot(x, [row.get("u", 0.0) for row in rows], label="u(x)", linewidth=2, color="#3b82f6")
            ax.plot(x, [row.get("v", 0.0) for row in rows], label="v(x)", linestyle="--", color="#f97316")
            if "v2" in column_keys:
                ax.plot(x, [row.get("v2", 0.0) for row in rows], label="v2(x)", linestyle=":", color="#10b981")
        else:
            ax.plot(x, [row.get("difference", 0.0) for row in rows], label="Разность", color="#d97706")
        ax.set_title(task.get("title", "Результат"))
        ax.set_xlabel("x")
        ax.grid(True, alpha=0.3, linestyle="--")
        ax.legend(loc="upper left", framealpha=0.95, facecolor="white")
        fig.suptitle("Колесо мыши: приблизить/отдалить, левая кнопка: переместить, R: сброс", fontsize=self.fonts["body"].cget("size"))
        self._enable_plot_zoom(fig, ax)
        plt.tight_layout()
        plt.show()

    @staticmethod
    def _format_cell(value) -> str:
        if value is None:
            return ""
        if isinstance(value, float):
            if abs(value) < 1e-12:
                return "0"
            return f"{value:.10g}"
        return str(value)


if __name__ == "__main__":
    os.chdir(Path(__file__).resolve().parent.parent)
    app = LabUI()
    app.mainloop()
