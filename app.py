import io
import json
import os
import sys
import traceback
import urllib.request
from datetime import datetime
from functools import lru_cache
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageTk

from templates import (
    BEST_OF_OPTIONS,
    CANVAS_SIZE,
    GAME_TEMPLATES,
    POST_VERSIONS,
    PREVIEW_SIZE,
    get_games,
)


HOME_LOGO_FOLDER_BY_GAME = {
    "Counter Strike": "CS2",
    "Rainbow Six": "R6",
    "Rocket League": "RL",
    "Call of Duty": "COD",
}


def resolve_asset(relative_path):
    return os.path.join(resource_base_dir(), relative_path)


def resource_base_dir():
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(__file__)


def writable_base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(__file__)


def slugify(value):
    return value.lower().replace(" ", "_").replace("-", "_")


@lru_cache(maxsize=32)
def get_font(size, bold=False):
    if not bold:
        koulen_path = resolve_asset("assets/fonts/Koulen-Regular.ttf")
        if os.path.exists(koulen_path):
            try:
                return ImageFont.truetype(koulen_path, size)
            except OSError:
                pass

    candidates = []
    if bold:
        candidates.extend(["arialbd.ttf", "seguisb.ttf", "tahomabd.ttf"])
    else:
        candidates.extend(["arial.ttf", "segoeui.ttf", "tahoma.ttf"])

    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def fit_image_path(image_path, box_size):
    with Image.open(image_path) as src:
        src = src.convert("RGBA")
        return ImageOps.fit(src, box_size, method=Image.Resampling.LANCZOS)


def fit_image_pil(pil_image, box_size):
    return ImageOps.fit(pil_image.convert("RGBA"), box_size, method=Image.Resampling.LANCZOS)


def resize_max_dimension(pil_image, max_dimension):
    image = pil_image.convert("RGBA")
    width, height = image.size
    if width <= 0 or height <= 0:
        return image

    largest_side = max(width, height)
    scale = max_dimension / float(largest_side)
    new_width = max(1, int(round(width * scale)))
    new_height = max(1, int(round(height * scale)))
    return image.resize((new_width, new_height), Image.Resampling.LANCZOS)


def resize_fit_box(pil_image, max_width, max_height):
    image = pil_image.convert("RGBA")
    image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
    return image


def parse_score(value):
    try:
        return int(value)
    except ValueError:
        return 0


def app_settings_path():
    return os.path.join(writable_base_dir(), "app_settings.json")


def load_app_settings():
    settings_path = app_settings_path()
    if not os.path.exists(settings_path):
        return {}

    try:
        with open(settings_path, "r", encoding="utf-8") as settings_file:
            data = json.load(settings_file)
        if isinstance(data, dict):
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return {}


def save_app_settings(settings):
    settings_path = app_settings_path()
    try:
        with open(settings_path, "w", encoding="utf-8") as settings_file:
            json.dump(settings, settings_file, ensure_ascii=True, indent=2)
    except OSError:
        pass


class PostingApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Gaming Penguins - Posting Tool")
        self.geometry("1320x860")
        self.minsize(1180, 760)

        self.app_settings = load_app_settings()
        self.games = get_games()
        initial_game = self.app_settings.get("last_game", self.games[0])
        if initial_game not in self.games:
            initial_game = self.games[0]
        self.game_var = tk.StringVar(value=initial_game)
        self.post_type_var = tk.StringVar(value=POST_VERSIONS[0])
        self.best_of_var = tk.StringVar(value="BO3")
        self.match_date_var = tk.StringVar(value=datetime.now().strftime("%d.%m"))
        self.match_time_var = tk.StringVar(value="19:00")
        self.player_name_var = tk.StringVar(value="PLAYER NAME")

        self.home_logo_var = tk.StringVar(value="")
        self.enemy_logo_url_var = tk.StringVar(value="")
        self.league_logo_var = tk.StringVar(value="")
        self.league_var = tk.StringVar(value="")
        self.league_url_var = tk.StringVar(value="")

        self.enemy_logo_path = None
        self.enemy_logo_url_img = None
        self.league_upload_path = None
        self.league_url_img = None
        self.player_image_path = None

        self.map_vars = [tk.StringVar(value="") for _ in range(5)]
        self.map_home_score_vars = [tk.StringVar(value="0") for _ in range(5)]
        self.map_away_score_vars = [tk.StringVar(value="0") for _ in range(5)]

        self.preview_image_tk = None
        self.home_logo_files_by_game = self.discover_home_logos_by_game()
        self.league_preset_files = []  # Wird dynamisch geladen basierend auf dem Spiel
        self.custom_league_files = []  # Additionale benutzer-define Liga-Ordner
        self.map_rows = []

        self.ui_bg = "#0f1720"
        self.ui_panel_bg = "#16212d"
        self.ui_border = "#3a4a5b"
        self.ui_text = "#e7edf5"
        self.ui_input_bg = "#2a3442"
        self.ui_button_bg = "#263341"
        self.ui_button_hover = "#32465a"
        self.ui_accent_blue = "#208ae8"
        self.ui_accent_teal = "#1fa7a7"
        self.ui_toggle_on = "#1ea653"

        self.current_render_image = None
        self.preview_after_id = None
        self.preview_rebuild_requested = False
        self.image_cache = {}
        self.fitted_image_cache = {}
        self.best_of_buttons = {}
        self.best_of_button_order = ["BO1", "BO2", "BO3", "BO5"]
        self.best_of_options_current = []
        self.active_post_type = self.post_type_var.get()
        self.post_states = {}

        self.configure_ttk_styles()
        self._build_layout()
        self.sync_game_fields()
        self.update_visible_sections()
        self.render_preview()

    def configure_ttk_styles(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(
            "Dark.TEntry",
            fieldbackground=self.ui_input_bg,
            foreground=self.ui_text,
            insertcolor=self.ui_text,
            bordercolor="#5b6878",
            lightcolor="#5b6878",
            darkcolor="#5b6878",
            focuscolor=self.ui_input_bg,
            borderwidth=1,
            padding=4,
            relief="flat",
        )

        style.configure(
            "Dark.TCombobox",
            fieldbackground=self.ui_input_bg,
            background=self.ui_input_bg,
            foreground=self.ui_text,
            bordercolor="#5b6878",
            lightcolor="#5b6878",
            darkcolor="#5b6878",
            focuscolor=self.ui_input_bg,
            borderwidth=1,
            arrowsize=22,
            padding=(8, 7, 10, 7),
            relief="flat",
        )

        style.map(
            "Dark.TCombobox",
            fieldbackground=[("readonly", self.ui_input_bg), ("!disabled", self.ui_input_bg)],
            foreground=[("readonly", self.ui_text), ("!disabled", self.ui_text)],
            selectbackground=[("readonly", self.ui_input_bg)],
            selectforeground=[("readonly", self.ui_text)],
            bordercolor=[("focus", "#5b6878"), ("!focus", "#5b6878")],
        )

        style.configure("Dark.TLabel", background=self.ui_panel_bg, foreground=self.ui_text)
        style.configure("Dark.TFrame", background=self.ui_panel_bg)
        style.configure("Dark.TLabelframe", background=self.ui_panel_bg, bordercolor=self.ui_border)
        style.configure("Dark.TLabelframe.Label", background=self.ui_panel_bg, foreground=self.ui_text)
        style.configure(
            "Vertical.Dark.TScrollbar",
            troughcolor=self.ui_panel_bg,
            background="#3b4a5c",
            bordercolor=self.ui_panel_bg,
            arrowcolor=self.ui_text,
            relief="flat",
        )

        style.configure(
            "Dark.TButton",
            background=self.ui_button_bg,
            foreground=self.ui_text,
            bordercolor=self.ui_border,
            lightcolor=self.ui_border,
            darkcolor=self.ui_border,
            focuscolor=self.ui_button_bg,
            padding=6,
            relief="flat",
        )
        style.map("Dark.TButton", background=[("active", self.ui_button_hover)])

        style.configure(
            "Primary.TButton",
            background=self.ui_accent_blue,
            foreground="#ffffff",
            bordercolor=self.ui_accent_blue,
            lightcolor=self.ui_accent_blue,
            darkcolor=self.ui_accent_blue,
            padding=6,
            relief="flat",
        )
        style.map("Primary.TButton", background=[("active", "#2b9fff")])

        style.configure(
            "Upload.TButton",
            background=self.ui_accent_teal,
            foreground="#ffffff",
            bordercolor=self.ui_accent_teal,
            lightcolor=self.ui_accent_teal,
            darkcolor=self.ui_accent_teal,
            padding=6,
            relief="flat",
        )
        style.map("Upload.TButton", background=[("active", "#28bbbb")])

        style.configure(
            "Toggle.Off.TButton",
            background=self.ui_button_bg,
            foreground=self.ui_text,
            bordercolor=self.ui_border,
            lightcolor=self.ui_border,
            darkcolor=self.ui_border,
            padding=6,
            relief="flat",
        )
        style.map("Toggle.Off.TButton", background=[("active", self.ui_button_hover)])

        style.configure(
            "Toggle.On.TButton",
            background=self.ui_toggle_on,
            foreground="#ffffff",
            bordercolor=self.ui_toggle_on,
            lightcolor=self.ui_toggle_on,
            darkcolor=self.ui_toggle_on,
            padding=6,
            relief="flat",
        )
        style.map("Toggle.On.TButton", background=[("active", "#29bf63")])

        self.option_add("*TCombobox*Listbox.background", self.ui_panel_bg)
        self.option_add("*TCombobox*Listbox.foreground", self.ui_text)
        self.option_add("*TCombobox*Listbox.selectBackground", self.ui_border)
        self.option_add("*TCombobox*Listbox.selectForeground", self.ui_text)

    def default_post_state(self):
        return {
            "best_of": "BO3",
            "home_logo": "",
            "enemy_logo_url": "",
            "league_logo": "",
            "league": "",
            "league_url": "",
            "match_date": datetime.now().strftime("%d.%m"),
            "match_time": "19:00",
            "player_name": "PLAYER NAME",
            "map_names": ["" for _ in range(5)],
            "map_home_scores": ["0" for _ in range(5)],
            "map_away_scores": ["0" for _ in range(5)],
            "enemy_logo_path": None,
            "enemy_logo_url_img": None,
            "league_upload_path": None,
            "league_url_img": None,
            "player_image_path": None,
        }

    def save_current_post_state(self, post_type):
        self.post_states[post_type] = {
            "best_of": self.best_of_var.get(),
            "home_logo": self.home_logo_var.get(),
            "enemy_logo_url": self.enemy_logo_url_var.get(),
            "league_logo": self.league_logo_var.get(),
            "league": self.league_var.get(),
            "league_url": self.league_url_var.get(),
            "match_date": self.match_date_var.get(),
            "match_time": self.match_time_var.get(),
            "player_name": self.player_name_var.get(),
            "map_names": [item.get() for item in self.map_vars],
            "map_home_scores": [item.get() for item in self.map_home_score_vars],
            "map_away_scores": [item.get() for item in self.map_away_score_vars],
            "enemy_logo_path": self.enemy_logo_path,
            "enemy_logo_url_img": self.enemy_logo_url_img,
            "league_upload_path": self.league_upload_path,
            "league_url_img": self.league_url_img,
            "player_image_path": self.player_image_path,
        }

    def load_post_state(self, post_type):
        state = self.post_states.get(post_type, self.default_post_state())
        self.best_of_var.set(state["best_of"])
        self.home_logo_var.set(state["home_logo"])
        self.enemy_logo_url_var.set(state["enemy_logo_url"])
        self.league_logo_var.set(state.get("league_logo", ""))
        self.league_var.set(state["league"])
        self.league_url_var.set(state["league_url"])
        self.match_date_var.set(state["match_date"])
        self.match_time_var.set(state["match_time"])
        self.player_name_var.set(state["player_name"])

        for idx, value in enumerate(state["map_names"]):
            if idx < len(self.map_vars):
                self.map_vars[idx].set(value)

        for idx, value in enumerate(state["map_home_scores"]):
            if idx < len(self.map_home_score_vars):
                self.map_home_score_vars[idx].set(value)

        for idx, value in enumerate(state["map_away_scores"]):
            if idx < len(self.map_away_score_vars):
                self.map_away_score_vars[idx].set(value)

        self.enemy_logo_path = state["enemy_logo_path"]
        self.enemy_logo_url_img = state["enemy_logo_url_img"]
        self.league_upload_path = state["league_upload_path"]
        self.league_url_img = state["league_url_img"]
        self.player_image_path = state["player_image_path"]

    def _on_param_content_configure(self, _event):
        if hasattr(self, "param_canvas"):
            self.param_canvas.configure(scrollregion=self.param_canvas.bbox("all"))
            self._update_param_scrollbar_visibility()

    def _on_param_canvas_configure(self, event):
        if hasattr(self, "param_canvas") and hasattr(self, "param_canvas_window"):
            self.param_canvas.itemconfigure(self.param_canvas_window, width=event.width)
            self._update_param_scrollbar_visibility()

    def _update_param_scrollbar_visibility(self):
        if not hasattr(self, "param_canvas") or not hasattr(self, "param_scrollbar"):
            return

        bbox = self.param_canvas.bbox("all")
        if not bbox:
            self.param_scrollbar.grid_remove()
            return

        content_height = bbox[3] - bbox[1]
        canvas_height = self.param_canvas.winfo_height()
        needs_scroll = content_height > (canvas_height + 2)

        if needs_scroll:
            self.param_scrollbar.grid()
        else:
            self.param_canvas.yview_moveto(0)
            self.param_scrollbar.grid_remove()

    def _on_param_mousewheel(self, event):
        if not hasattr(self, "param_canvas"):
            return
        bbox = self.param_canvas.bbox("all")
        if not bbox:
            return
        content_height = bbox[3] - bbox[1]
        if content_height <= (self.param_canvas.winfo_height() + 2):
            return
        self.param_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def discover_images(self, folder_path, recursive=False):
        if not os.path.isdir(folder_path):
            return []

        files = []
        if recursive:
            for root, _, names in os.walk(folder_path):
                for name in names:
                    lower = name.lower()
                    if lower.endswith((".png", ".jpg", ".jpeg", ".webp")):
                        files.append(os.path.join(root, name))
            return sorted(files)

        for name in os.listdir(folder_path):
            lower = name.lower()
            if lower.endswith((".png", ".jpg", ".jpeg", ".webp")):
                files.append(os.path.join(folder_path, name))
        return sorted(files)

    def discover_home_logos_by_game(self):
        logos_by_game = {}
        for game_name, folder_name in HOME_LOGO_FOLDER_BY_GAME.items():
            folder_path = resolve_asset(os.path.join("assets", "home_logos", folder_name))
            logos_by_game[game_name] = self.discover_images(folder_path, recursive=True)
        return logos_by_game

    def load_league_files_for_game(self):
        """Lädt Liga-Dateien für das aktuell ausgewählte Spiel"""
        game = self.game_var.get()
        game_slug = slugify(game)
        
        # Liga-Dateien aus dem spiel-spezifischen Ordner
        preset_folder = resolve_asset(os.path.join("assets", "leagues", game_slug))
        self.league_preset_files = self.discover_images(preset_folder, recursive=False)
        
        # Zusätzlich: Custom Liga-Ordner laden (für Benutzer-definierte Logos)
        custom_folder = resolve_asset(os.path.join("assets", "leagues", game_slug, "custom"))
        self.custom_league_files = self.discover_images(custom_folder, recursive=False)

    def selected_game_template(self):
        return GAME_TEMPLATES.get(self.game_var.get(), {})

    def home_logo_files_for_selected_game(self):
        return self.home_logo_files_by_game.get(self.game_var.get(), [])

    def home_logo_labels(self):
        logo_files = self.home_logo_files_for_selected_game()
        if not logo_files:
            return ["Keine Heim-Logos gefunden"]
        return [os.path.basename(path) for path in logo_files]

    def league_logo_labels(self):
        labels = [f"Bild: {os.path.basename(path)}" for path in self.league_preset_files]
        labels.extend([f"Custom: {os.path.basename(path)}" for path in self.custom_league_files])
        return labels or ["Keine Liga-Logos gefunden"]

    def create_panel(self, parent, title, height=None):
        panel = tk.Frame(
            parent,
            bg=self.ui_panel_bg,
            highlightthickness=3,
            highlightbackground=self.ui_border,
            highlightcolor=self.ui_border,
            bd=0,
        )
        if height is not None:
            panel.configure(height=height)
            panel.grid_propagate(False)

        title_label = tk.Label(
            panel,
            text=title,
            bg=self.ui_panel_bg,
            fg=self.ui_text,
            font=("Arial", 16, "bold"),
            anchor="w",
            justify="left",
        )
        title_label.pack(fill="x", padx=10, pady=(10, 4))

        body = tk.Frame(panel, bg=self.ui_panel_bg)
        body.pack(fill="both", expand=True, padx=10, pady=(4, 10))
        return panel, body

    def _build_layout(self):
        self.configure(bg=self.ui_bg)

        root = tk.Frame(self, bg=self.ui_bg, padx=16, pady=16)
        root.pack(fill="both", expand=True)
        root.grid_columnconfigure(0, weight=0, minsize=380)
        root.grid_columnconfigure(1, weight=1)
        root.grid_rowconfigure(0, weight=0)
        root.grid_rowconfigure(1, weight=1)

        game_panel, game_body = self.create_panel(root, "SPIEL AUSWAHL", height=76)
        game_panel.grid(row=0, column=0, sticky="ew", padx=(0, 12), pady=(0, 12))

        self.game_cb = ttk.Combobox(game_body, textvariable=self.game_var, values=self.games, state="readonly", style="Dark.TCombobox")
        self.game_cb.pack(fill="x")
        self.game_cb.bind("<<ComboboxSelected>>", lambda _e: self.on_template_change())

        post_panel, post_body = self.create_panel(root, "POST AUSWAHL", height=76)
        post_panel.grid(row=0, column=1, sticky="ew", pady=(0, 12))

        self.post_cb = ttk.Combobox(post_body, textvariable=self.post_type_var, values=POST_VERSIONS, state="readonly", style="Dark.TCombobox", width=24)
        self.post_cb.pack(anchor="w")
        self.post_cb.bind("<<ComboboxSelected>>", lambda _e: self.on_post_type_change())

        param_panel, param_body = self.create_panel(root, "AUSWAHL PARAMETER\n\nUND USER EINGABEN")
        param_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 12))
        param_body.grid_columnconfigure(0, weight=1)
        param_body.grid_rowconfigure(0, weight=1)

        self.param_canvas = tk.Canvas(param_body, bg=self.ui_panel_bg, bd=0, highlightthickness=0)
        self.param_scrollbar = tk.Scrollbar(
            param_body,
            orient="vertical",
            command=self.param_canvas.yview,
            bg="#2f3a47",
            activebackground="#3b4a5c",
            troughcolor="#121b25",
            highlightthickness=0,
            width=10,
            bd=0,
            relief="flat",
        )
        self.param_canvas.configure(yscrollcommand=self.param_scrollbar.set)

        self.param_canvas.grid(row=0, column=0, sticky="nsew")
        self.param_scrollbar.grid(row=0, column=1, sticky="ns")

        self.param_inner = tk.Frame(self.param_canvas, bg=self.ui_panel_bg)
        self.param_canvas_window = self.param_canvas.create_window((0, 0), window=self.param_inner, anchor="nw")
        self.param_inner.grid_columnconfigure(0, weight=1)

        self.param_inner.bind("<Configure>", self._on_param_content_configure)
        self.param_canvas.bind("<Configure>", self._on_param_canvas_configure)
        self.param_canvas.bind("<Enter>", lambda _e: self.bind_all("<MouseWheel>", self._on_param_mousewheel))
        self.param_canvas.bind("<Leave>", lambda _e: self.unbind_all("<MouseWheel>"))

        self.dynamic_sections = {}
        section_row = 0

        self.dynamic_sections["team"] = tk.LabelFrame(
            self.param_inner,
            text="Team-Logos",
            bg=self.ui_panel_bg,
            fg=self.ui_text,
            bd=1,
            relief="solid",
            highlightthickness=0,
            padx=8,
            pady=8,
        )
        self.dynamic_sections["team"].grid(row=section_row, column=0, sticky="ew", pady=(0, 8))
        self.dynamic_sections["team"].columnconfigure(0, weight=1)
        section_row += 1

        ttk.Label(self.dynamic_sections["team"], text="Heim-Logo (Auswahl)", style="Dark.TLabel").grid(row=0, column=0, sticky="w")
        self.home_logo_cb = ttk.Combobox(self.dynamic_sections["team"], textvariable=self.home_logo_var, values=self.home_logo_labels(), state="readonly", style="Dark.TCombobox")
        self.home_logo_cb.grid(row=1, column=0, sticky="ew", pady=(4, 8))
        self.home_logo_cb.bind("<<ComboboxSelected>>", lambda _e: self.render_preview())

        self.opponent_group = tk.LabelFrame(
            self.dynamic_sections["team"],
            text="Gegner Logo",
            bg=self.ui_panel_bg,
            fg=self.ui_text,
            bd=1,
            relief="solid",
            highlightthickness=0,
            padx=8,
            pady=8,
        )
        self.opponent_group.grid(row=2, column=0, sticky="ew")
        self.opponent_group.grid_columnconfigure(0, weight=1)

        ttk.Label(self.opponent_group, text="Gegner-Logo URL", style="Dark.TLabel").grid(row=0, column=0, sticky="w")
        enemy_url_entry = ttk.Entry(self.opponent_group, textvariable=self.enemy_logo_url_var, style="Dark.TEntry")
        enemy_url_entry.grid(row=1, column=0, sticky="ew", pady=(4, 6))
        ttk.Button(self.opponent_group, text="Logo-URL laden", command=self.load_enemy_logo_from_url, style="Primary.TButton").grid(row=2, column=0, sticky="ew", pady=(0, 6))
        ttk.Button(self.opponent_group, text="Gegnerlogo Datei auswählen", command=self.pick_enemy_logo, style="Upload.TButton").grid(row=3, column=0, sticky="ew", pady=(0, 6))
        ttk.Button(self.opponent_group, text="Gegnerlogo zurücksetzen", command=self.clear_enemy_logo, style="Dark.TButton").grid(row=4, column=0, sticky="ew", pady=(6, 0))

        self.dynamic_sections["league"] = tk.LabelFrame(
            self.param_inner,
            text="Liga",
            bg=self.ui_panel_bg,
            fg=self.ui_text,
            bd=1,
            relief="solid",
            highlightthickness=0,
            padx=8,
            pady=8,
        )
        self.dynamic_sections["league"].grid(row=section_row, column=0, sticky="ew", pady=(0, 8))
        self.dynamic_sections["league"].columnconfigure(0, weight=1)
        section_row += 1

        ttk.Label(self.dynamic_sections["league"], text="Liga-Logo (Auswahl)", style="Dark.TLabel").grid(row=0, column=0, sticky="w")
        self.league_cb = ttk.Combobox(self.dynamic_sections["league"], textvariable=self.league_logo_var, values=self.league_logo_labels(), state="readonly", style="Dark.TCombobox")
        self.league_cb.grid(row=1, column=0, sticky="ew", pady=(4, 6))
        self.league_cb.bind("<<ComboboxSelected>>", lambda _e: self.render_preview())

        ttk.Label(self.dynamic_sections["league"], text="Liga-Name (Text)", style="Dark.TLabel").grid(row=2, column=0, sticky="w")
        league_text_entry = ttk.Entry(self.dynamic_sections["league"], textvariable=self.league_var, style="Dark.TEntry")
        league_text_entry.grid(row=3, column=0, sticky="ew", pady=(4, 6))
        league_text_entry.bind("<KeyRelease>", lambda _e: self.schedule_preview_render())

        ttk.Label(self.dynamic_sections["league"], text="Liga-Bild URL", style="Dark.TLabel").grid(row=4, column=0, sticky="w")
        league_url_entry = ttk.Entry(self.dynamic_sections["league"], textvariable=self.league_url_var, style="Dark.TEntry")
        league_url_entry.grid(row=5, column=0, sticky="ew", pady=(4, 6))
        ttk.Button(self.dynamic_sections["league"], text="Bild-URL laden", command=self.load_league_image_from_url, style="Primary.TButton").grid(row=6, column=0, sticky="ew", pady=(0, 6))
        ttk.Button(self.dynamic_sections["league"], text="Datei auswählen", command=self.pick_league_image, style="Upload.TButton").grid(row=7, column=0, sticky="ew", pady=(0, 6))
        ttk.Button(self.dynamic_sections["league"], text="Liga-Bild zurücksetzen", command=self.clear_league_image, style="Dark.TButton").grid(row=8, column=0, sticky="ew", pady=(6, 0))

        self.dynamic_sections["matchday"] = tk.LabelFrame(
            self.param_inner,
            text="Matchday",
            bg=self.ui_panel_bg,
            fg=self.ui_text,
            bd=1,
            relief="solid",
            highlightthickness=0,
            padx=8,
            pady=8,
        )
        self.dynamic_sections["matchday"].grid(row=section_row, column=0, sticky="ew", pady=(0, 8))
        self.dynamic_sections["matchday"].columnconfigure(0, weight=1)
        section_row += 1

        ttk.Label(self.dynamic_sections["matchday"], text="Datum", style="Dark.TLabel").grid(row=0, column=0, sticky="w")
        date_entry = ttk.Entry(self.dynamic_sections["matchday"], textvariable=self.match_date_var, style="Dark.TEntry")
        date_entry.grid(row=1, column=0, sticky="ew", pady=(4, 6))
        date_entry.bind("<KeyRelease>", lambda _e: self.schedule_preview_render())
        ttk.Label(self.dynamic_sections["matchday"], text="Uhrzeit", style="Dark.TLabel").grid(row=2, column=0, sticky="w")
        time_entry = ttk.Entry(self.dynamic_sections["matchday"], textvariable=self.match_time_var, style="Dark.TEntry")
        time_entry.grid(row=3, column=0, sticky="ew", pady=(4, 0))
        time_entry.bind("<KeyRelease>", lambda _e: self.schedule_preview_render())

        self.dynamic_sections["player"] = tk.LabelFrame(
            self.param_inner,
            text="Spieler Welcome",
            bg=self.ui_panel_bg,
            fg=self.ui_text,
            bd=1,
            relief="solid",
            highlightthickness=0,
            padx=8,
            pady=8,
        )
        self.dynamic_sections["player"].grid(row=section_row, column=0, sticky="ew", pady=(0, 8))
        self.dynamic_sections["player"].columnconfigure(0, weight=1)
        section_row += 1

        player_name_group = tk.LabelFrame(
            self.dynamic_sections["player"],
            text="Spielername",
            bg=self.ui_panel_bg,
            fg=self.ui_text,
            bd=1,
            relief="solid",
            highlightthickness=0,
            padx=8,
            pady=8,
        )
        player_name_group.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        player_name_group.grid_columnconfigure(0, weight=1)

        player_name_entry = ttk.Entry(player_name_group, textvariable=self.player_name_var, style="Dark.TEntry")
        player_name_entry.grid(row=0, column=0, sticky="ew")
        player_name_entry.bind("<KeyRelease>", lambda _e: self.schedule_preview_render())

        player_image_group = tk.LabelFrame(
            self.dynamic_sections["player"],
            text="Spielerbild",
            bg=self.ui_panel_bg,
            fg=self.ui_text,
            bd=1,
            relief="solid",
            highlightthickness=0,
            padx=8,
            pady=8,
        )
        player_image_group.grid(row=1, column=0, sticky="ew")
        player_image_group.grid_columnconfigure(0, weight=1)

        ttk.Button(player_image_group, text="Datei auswählen", command=self.pick_player_image, style="Upload.TButton").grid(row=0, column=0, sticky="ew", pady=(0, 6))
        ttk.Button(player_image_group, text="Bild zurücksetzen", command=self.clear_player_image, style="Dark.TButton").grid(row=1, column=0, sticky="ew")

        self.dynamic_sections["maps"] = tk.LabelFrame(
            self.param_inner,
            text="Maps & Ergebnisse",
            bg=self.ui_panel_bg,
            fg=self.ui_text,
            bd=1,
            relief="solid",
            highlightthickness=0,
            padx=8,
            pady=8,
        )
        self.dynamic_sections["maps"].grid(row=section_row, column=0, sticky="ew", pady=(0, 8))
        self.dynamic_sections["maps"].columnconfigure(0, weight=1)
        section_row += 1

        ttk.Label(self.dynamic_sections["maps"], text="Match Format", style="Dark.TLabel").grid(row=0, column=0, sticky="w")

        self.best_of_button_row = ttk.Frame(self.dynamic_sections["maps"], style="Dark.TFrame")
        self.best_of_button_row.grid(row=1, column=0, sticky="w", pady=(4, 8))

        for idx, option in enumerate(self.best_of_button_order):
            button = ttk.Button(
                self.best_of_button_row,
                text=option,
                style="Toggle.Off.TButton",
                command=lambda value=option: self.select_best_of(value),
                width=6,
            )
            button.grid(row=0, column=idx, padx=(0, 8), sticky="w")
            self.best_of_buttons[option] = button

        self.maps_header_label = ttk.Label(self.dynamic_sections["maps"], text="Maps + Scores (Heim:Gegner)", style="Dark.TLabel")
        self.maps_header_label.grid(row=2, column=0, sticky="w")

        for idx in range(5):
            row_idx = 3 + idx
            row_frame = ttk.Frame(self.dynamic_sections["maps"], style="Dark.TFrame")
            row_frame.grid(row=row_idx, column=0, sticky="ew", pady=(4, 0))
            row_frame.columnconfigure(0, weight=1)

            map_cb = ttk.Combobox(row_frame, textvariable=self.map_vars[idx], values=[], state="readonly", width=16, style="Dark.TCombobox")
            map_cb.grid(row=0, column=0, sticky="ew")
            map_cb.bind("<<ComboboxSelected>>", lambda _e: self.render_preview())

            ttk.Label(row_frame, text=":", style="Dark.TLabel").grid(row=0, column=2, padx=4)

            home_score = ttk.Entry(row_frame, textvariable=self.map_home_score_vars[idx], width=3, style="Dark.TEntry")
            home_score.grid(row=0, column=1, padx=(8, 0))
            home_score.bind("<KeyRelease>", lambda _e: self.schedule_preview_render())

            away_score = ttk.Entry(row_frame, textvariable=self.map_away_score_vars[idx], width=3, style="Dark.TEntry")
            away_score.grid(row=0, column=3)
            away_score.bind("<KeyRelease>", lambda _e: self.schedule_preview_render())

            self.map_rows.append((row_frame, map_cb, home_score, away_score))

        action_frame = tk.Frame(self.param_inner, bg=self.ui_panel_bg)
        action_frame.grid(row=section_row, column=0, sticky="ew", pady=(6, 0))
        action_frame.grid_columnconfigure(0, weight=1)
        self.action_frame = action_frame
        ttk.Button(action_frame, text="Vorschau aktualisieren", command=self.render_preview, style="Dark.TButton").grid(row=0, column=0, sticky="ew", pady=(0, 6))
        ttk.Button(action_frame, text="Als JPG exportieren", command=self.export_jpg, style="Primary.TButton").grid(row=1, column=0, sticky="ew")

        preview_panel, preview_body = self.create_panel(root, "VORSCHAU FENSTER")
        preview_panel.grid(row=1, column=1, sticky="nsew")
        preview_body.grid_rowconfigure(0, weight=1)
        preview_body.grid_columnconfigure(0, weight=1)
        preview_body.configure(bg=self.ui_bg)
        self.preview_container = preview_body
        self.preview_container.bind("<Configure>", self.on_preview_container_resize)

        self.preview_label = tk.Label(
            preview_body,
            bg=self.ui_bg,
            bd=1,
            relief="solid",
            highlightthickness=1,
            highlightbackground="#5b6878",
            highlightcolor="#5b6878",
        )
        self.preview_label.place(relx=0.5, rely=0.5, anchor="center")

    def update_visible_sections(self):
        post_type = self.post_type_var.get()
        game = self.game_var.get()
        for frame in self.dynamic_sections.values():
            frame.grid_remove()

        show_team = post_type in ("Matchday", "Victory", "Defeat", "Liga-Teilnahme")
        show_league = post_type in ("Matchday", "Victory", "Defeat", "Liga-Teilnahme")
        show_matchday = post_type == "Matchday"
        show_player = post_type == "Spieler-Welcome"
        show_maps = post_type in ("Victory", "Defeat")
        # Maps nicht anzeigen für Rocket League Matchday
        if game == "Rocket League" and post_type == "Matchday":
            show_maps = False

        order = ["team", "league", "matchday", "player", "maps"]
        current_row = 0
        for key in order:
            should_show = (
                (key == "team" and show_team)
                or (key == "league" and show_league)
                or (key == "matchday" and show_matchday)
                or (key == "player" and show_player)
                or (key == "maps" and show_maps)
            )
            if should_show:
                self.dynamic_sections[key].grid(row=current_row, column=0, sticky="ew", pady=(0, 8))
                current_row += 1

        if hasattr(self, "action_frame"):
            self.action_frame.grid(row=current_row, column=0, sticky="ew", pady=(6, 0))
        self._update_param_scrollbar_visibility()

    def on_template_change(self):
        self.app_settings["last_game"] = self.game_var.get()
        save_app_settings(self.app_settings)
        self.sync_game_fields()
        self.update_visible_sections()
        self.render_preview()

    def on_best_of_change(self):
        self.refresh_best_of_buttons_ui()
        self.sync_map_row_visibility()
        self.render_preview()

    def select_best_of(self, value):
        if value not in self.best_of_options_current:
            return
        self.best_of_var.set(value)
        self.on_best_of_change()

    def on_post_type_change(self):
        current_post = self.post_type_var.get()
        if self.active_post_type != current_post:
            self.save_current_post_state(self.active_post_type)
            self.load_post_state(current_post)
            self.active_post_type = current_post

        self.sync_game_fields()
        self.sync_best_of_options()
        self.sync_map_row_visibility()
        self.update_visible_sections()
        self.render_preview()

    def available_best_of_options(self):
        if self.post_type_var.get() in ("Victory", "Defeat"):
            return ["BO1", "BO2", "BO3", "BO5"]
        return ["BO1", "BO3", "BO5"]

    def sync_best_of_options(self):
        options = self.available_best_of_options()
        self.best_of_options_current = options
        if self.best_of_var.get() not in options:
            self.best_of_var.set(options[0])
        self.refresh_best_of_buttons_ui()

    def refresh_best_of_buttons_ui(self):
        selected = self.best_of_var.get()
        for option, button in self.best_of_buttons.items():
            if option in self.best_of_options_current:
                button.grid()
                if option == selected:
                    button.configure(style="Toggle.On.TButton")
                else:
                    button.configure(style="Toggle.Off.TButton")
            else:
                button.grid_remove()

    def visible_map_indices(self):
        if self.post_type_var.get() not in ("Victory", "Defeat"):
            return []

        best_of = self.best_of_var.get()
        if best_of == "BO1":
            return [1]
        if best_of == "BO2":
            return [0, 1]
        if best_of == "BO3":
            return [0, 1, 2]
        return [0, 1, 2, 3, 4]

    def sync_map_row_visibility(self):
        visible = set(self.visible_map_indices())
        for idx, (frame, _, _, _) in enumerate(self.map_rows):
            if idx in visible:
                frame.grid()
            else:
                frame.grid_remove()

    def sync_game_fields(self):
        # Lade Liga-Dateien für das aktuell ausgewählte Spiel
        self.load_league_files_for_game()
        
        maps = self.selected_game_template().get("maps", [])
        game = self.game_var.get()
        post_type = self.post_type_var.get()
        is_rl_matchday = game == "Rocket League" and post_type == "Matchday"
        
        for idx, (_, map_cb, _, _) in enumerate(self.map_rows):
            map_cb.configure(values=maps)
            
            # Für RL Matchday: Maps automatisch zyklisch setzen, nicht änderbar
            if is_rl_matchday:
                if maps:
                    map_cb.configure(state="readonly")
                    # Automatisch Map aus dem Pool zyklisch setzen
                    self.map_vars[idx].set(maps[idx % len(maps)])
            else:
                map_cb.configure(state="readonly")
                if maps and self.map_vars[idx].get() not in maps:
                    self.map_vars[idx].set(maps[min(idx, len(maps) - 1)])

        home_labels = self.home_logo_labels()
        self.home_logo_cb.configure(values=home_labels)
        if self.home_logo_var.get() not in home_labels:
            self.home_logo_var.set(home_labels[0])

        league_logos = self.league_logo_labels()
        self.league_cb.configure(values=league_logos)
        if self.league_logo_var.get() not in league_logos:
            self.league_logo_var.set("")

        self.sync_best_of_options()
        self.sync_map_row_visibility()

    def pick_enemy_logo(self):
        path = filedialog.askopenfilename(
            title="Gegnerlogo auswählen",
            filetypes=[("Bilddateien", "*.png *.jpg *.jpeg *.webp"), ("Alle Dateien", "*.*")],
        )
        if path:
            self.enemy_logo_path = path
            self.enemy_logo_url_img = None
            self.render_preview()

    def clear_enemy_logo(self):
        self.enemy_logo_path = None
        self.enemy_logo_url_img = None
        self.enemy_logo_url_var.set("")
        self.render_preview()

    def pick_league_image(self):
        path = filedialog.askopenfilename(
            title="Liga-Bild auswählen",
            filetypes=[("Bilddateien", "*.png *.jpg *.jpeg *.webp"), ("Alle Dateien", "*.*")],
        )
        if path:
            self.league_upload_path = path
            self.league_url_img = None
            self.render_preview()

    def clear_league_image(self):
        self.league_upload_path = None
        self.league_url_img = None
        self.league_logo_var.set("")
        self.league_url_var.set("")
        self.render_preview()

    def pick_player_image(self):
        path = filedialog.askopenfilename(
            title="Spielerbild auswählen",
            filetypes=[("Bilddateien", "*.png *.jpg *.jpeg *.webp"), ("Alle Dateien", "*.*")],
        )
        if path:
            self.player_image_path = path
            self.render_preview()

    def clear_player_image(self):
        self.player_image_path = None
        self.render_preview()

    def load_image_from_url(self, url):
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=12) as response:
            data = response.read()
        image = Image.open(io.BytesIO(data)).convert("RGBA")
        return image

    def load_enemy_logo_from_url(self):
        url = self.enemy_logo_url_var.get().strip()
        if not url:
            return
        try:
            self.enemy_logo_url_img = self.load_image_from_url(url)
            self.enemy_logo_path = None
            self.render_preview()
        except Exception as exc:
            messagebox.showerror("Fehler", f"Gegnerlogo URL konnte nicht geladen werden:\n{exc}")

    def load_league_image_from_url(self):
        url = self.league_url_var.get().strip()
        if not url:
            return
        try:
            self.league_url_img = self.load_image_from_url(url)
            self.league_upload_path = None
            self.render_preview()
        except Exception as exc:
            messagebox.showerror("Fehler", f"Liga-Bild URL konnte nicht geladen werden:\n{exc}")

    def selected_home_logo_path(self):
        label = self.home_logo_var.get()
        for path in self.home_logo_files_for_selected_game():
            if os.path.basename(path) == label:
                return path
        return None

    def selected_league_preset_path(self):
        label = self.league_logo_var.get().strip()
        if label.startswith("Bild: "):
            filename = label.replace("Bild: ", "", 1)
            for path in self.league_preset_files:
                if os.path.basename(path) == filename:
                    return path
        # Custom-Logos auch in den Ordner suchen
        elif label.startswith("Custom: "):
            filename = label.replace("Custom: ", "", 1)
            for path in self.custom_league_files:
                if os.path.basename(path) == filename:
                    return path
        return None

    def find_map_asset_path(self, game_name, map_name):
        game_slug = slugify(game_name)
        map_slug = slugify(map_name)
        base = resolve_asset(os.path.join("assets", "maps", game_slug))
        for ext in (".png", ".jpg", ".jpeg", ".webp"):
            path = os.path.join(base, f"{map_slug}{ext}")
            if os.path.exists(path):
                return path
        return None

    def schedule_preview_render(self, delay=120, rebuild=True):
        if rebuild:
            self.preview_rebuild_requested = True

        if self.preview_after_id is not None:
            self.after_cancel(self.preview_after_id)

        self.preview_after_id = self.after(delay, self._flush_preview_render)

    def _flush_preview_render(self):
        self.preview_after_id = None
        rebuild = self.preview_rebuild_requested
        self.preview_rebuild_requested = False
        self.render_preview(rebuild=rebuild)

    def get_cached_fitted_image(self, image_path, box_size):
        if not image_path or not os.path.exists(image_path):
            return None

        cache_key = (image_path, box_size)
        cached = self.fitted_image_cache.get(cache_key)
        if cached is not None:
            return cached

        fitted = fit_image_path(image_path, box_size)
        self.fitted_image_cache[cache_key] = fitted
        return fitted

    def paste_into_box(self, target_img, box, image_path=None, pil_img=None):
        width = box[2] - box[0]
        height = box[3] - box[1]
        if pil_img is not None:
            layer = fit_image_pil(pil_img, (width, height))
            target_img.alpha_composite(layer, (box[0], box[1]))
            return
        if image_path and os.path.exists(image_path):
            layer = self.get_cached_fitted_image(image_path, (width, height))
            if layer is not None:
                target_img.alpha_composite(layer, (box[0], box[1]))

    def load_image_source(self, image_path=None, pil_img=None):
        if pil_img is not None:
            return pil_img.convert("RGBA")
        if image_path and os.path.exists(image_path):
            cached = self.image_cache.get(image_path)
            if cached is not None:
                return cached
            with Image.open(image_path) as src:
                converted = src.convert("RGBA")
            self.image_cache[image_path] = converted
            return converted
        return None

    def draw_result_overlay(self, card_img, result):
        color = None
        if result == "home":
            color = (34, 197, 94)
        elif result == "away":
            color = (239, 68, 68)

        if color is None:
            return

        w, h = card_img.size
        overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(overlay)
        for y in range(h):
            alpha = int(26 + (74 * (y / max(1, h - 1))))
            d.line([(0, y), (w, y)], fill=(color[0], color[1], color[2], alpha))
        card_img.alpha_composite(overlay)

    def map_slots(self):
        if self.best_of_var.get() == "BO2":
            return [
                (220, 805, 520, 975),
                (560, 805, 860, 975),
            ]

        return [
            (50, 805, 350, 975),
            (390, 805, 690, 975),
            (730, 805, 1030, 975),
            (220, 1005, 520, 1175),
            (560, 1005, 860, 1175),
        ]

    def build_player_welcome_image(self, img, template):
        player_img = None
        if self.player_image_path and os.path.exists(self.player_image_path):
            player_img = self.load_image_source(image_path=self.player_image_path)

        if player_img is None:
            placeholder_rel = template.get("player_welcome_placeholder", "")
            if placeholder_rel:
                placeholder_path = resolve_asset(placeholder_rel)
                if os.path.exists(placeholder_path):
                    player_img = self.load_image_source(image_path=placeholder_path)

        if player_img is not None:
            player_layer = fit_image_pil(player_img, CANVAS_SIZE)
            img.alpha_composite(player_layer)

        fade_rel = template.get("player_welcome_foreground", "")
        if fade_rel:
            fade_path = resolve_asset(fade_rel)
            if os.path.exists(fade_path):
                fade_layer = self.get_cached_fitted_image(fade_path, CANVAS_SIZE)
                if fade_layer is not None:
                    img.alpha_composite(fade_layer)

        draw = ImageDraw.Draw(img)
        player_name = self.player_name_var.get().strip() or "PLAYER NAME"
        max_name_width = CANVAS_SIZE[0] - 80
        name_font_size = 96
        name_font = get_font(name_font_size, bold=True)
        bbox = draw.textbbox((0, 0), player_name, font=name_font)
        text_w = bbox[2] - bbox[0]

        while text_w > max_name_width and name_font_size > 28:
            name_font_size -= 2
            name_font = get_font(name_font_size, bold=True)
            bbox = draw.textbbox((0, 0), player_name, font=name_font)
            text_w = bbox[2] - bbox[0]

        bbox = draw.textbbox((0, 0), player_name, font=name_font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        text_x = int((CANVAS_SIZE[0] - text_w) / 2)
        text_y = int(CANVAS_SIZE[1] - text_h - 50)
        draw.text((text_x, text_y), player_name, font=name_font, fill="#FFFFFF")

        return img

    def build_image(self):
        game = self.game_var.get()
        post_type = self.post_type_var.get()
        template = self.selected_game_template()

        base_color = template.get("base", "#101010")
        img = Image.new("RGBA", CANVAS_SIZE, base_color)

        bg_rel = template.get("backgrounds", {}).get(post_type)
        if bg_rel:
            bg_path = resolve_asset(bg_rel)
            if os.path.exists(bg_path):
                cached_bg = self.get_cached_fitted_image(bg_path, CANVAS_SIZE)
                if cached_bg is not None:
                    img = cached_bg.copy()

        if post_type == "Spieler-Welcome":
            player_welcome_img = self.build_player_welcome_image(img, template)
            return player_welcome_img.convert("RGB")

        draw = ImageDraw.Draw(img)

        is_liga_teilnahme = post_type == "Liga-Teilnahme"
        is_matchday = post_type == "Matchday"
        vs_font_size = 70 if is_matchday else 50
        logo_max_size = 320 if is_matchday else 250
        fixed_gap = 60

        vs_font = get_font(vs_font_size, bold=False)
        score_font = get_font(66, bold=False)
        helper_font = get_font(28, bold=True)

        vs_text = "VS"
        vs_bbox = draw.textbbox((0, 0), vs_text, font=vs_font)
        vs_w = vs_bbox[2] - vs_bbox[0]
        vs_h = vs_bbox[3] - vs_bbox[1]
        center_x = CANVAS_SIZE[0] // 2
        spacing = 45
        center_y = 500

        home_logo = self.load_image_source(image_path=self.selected_home_logo_path())
        if home_logo is not None:
            home_logo = resize_max_dimension(home_logo, logo_max_size)
            home_w, home_h = home_logo.size
        else:
            home_w, home_h = 0, 0

        if self.enemy_logo_url_img is not None:
            enemy_logo = self.load_image_source(pil_img=self.enemy_logo_url_img)
        else:
            enemy_logo = self.load_image_source(image_path=self.enemy_logo_path)

        if enemy_logo is None:
            fallback_enemy_path = resolve_asset(os.path.join("assets", "placeholders", "no_logo.png"))
            if os.path.exists(fallback_enemy_path):
                enemy_logo = self.load_image_source(image_path=fallback_enemy_path)

        if enemy_logo is not None:
            enemy_logo = resize_max_dimension(enemy_logo, logo_max_size)
            enemy_w, enemy_h = enemy_logo.size
        else:
            enemy_w, enemy_h = 0, 0

        league_w, max_league_h = 340, 120
        league_preset_path = self.selected_league_preset_path()
        league_img = None
        if self.league_url_img is not None:
            league_img = resize_fit_box(self.league_url_img, league_w, max_league_h)
        elif self.league_upload_path:
            upload_img = self.load_image_source(image_path=self.league_upload_path)
            if upload_img is not None:
                league_img = resize_fit_box(upload_img, league_w, max_league_h)
        elif league_preset_path:
            preset_img = self.load_image_source(image_path=league_preset_path)
            if preset_img is not None:
                league_img = resize_fit_box(preset_img, league_w, max_league_h)

        league_text = self.league_var.get().strip()
        # Größere Schrift für manuell eingetippte Liga-Namen
        league_text_font = helper_font
        if league_img is None and league_text:
            league_text_font = get_font(40, bold=True)
        
        text_box = draw.textbbox((0, 0), league_text, font=league_text_font)
        text_w = text_box[2] - text_box[0]
        text_h = text_box[3] - text_box[1]

        if league_img is not None:
            league_render_w, league_render_h = league_img.size
        else:
            league_render_w, league_render_h = text_w, text_h

        if is_liga_teilnahme:
            x_text = "X"
            x_font = get_font(150, bold=False)
            x_bbox = draw.textbbox((0, 0), x_text, font=x_font)
            x_w = x_bbox[2] - x_bbox[0]
            x_h = x_bbox[3] - x_bbox[1]

            liga_logo_max = 280
            if home_logo is not None:
                home_logo = resize_max_dimension(home_logo, liga_logo_max)
                home_w, home_h = home_logo.size
            else:
                home_w, home_h = 0, 0

            if league_img is not None:
                league_logo = resize_max_dimension(league_img, liga_logo_max)
                league_w, league_h = league_logo.size
            else:
                league_logo = None
                league_w, league_h = text_w, text_h

            available_for_logos = CANVAS_SIZE[0] - x_w
            total_logo_width = home_w + league_w
            if total_logo_width > 0 and total_logo_width > (available_for_logos * 0.75):
                max_each = max(100, int((available_for_logos * 0.75) / 2))
                if home_logo is not None:
                    home_logo = resize_max_dimension(home_logo, max_each)
                    home_w, home_h = home_logo.size
                if league_logo is not None:
                    league_logo = resize_max_dimension(league_logo, max_each)
                    league_w, league_h = league_logo.size
                else:
                    league_w = min(league_w, max_each)

            lower_third_start = int((CANVAS_SIZE[1] * 2) / 3)
            content_center_y = lower_third_start + 35
            x_center_x = int(CANVAS_SIZE[0] / 2)
            draw.text((x_center_x, content_center_y), x_text, font=x_font, fill="#FFFFFF", anchor="mm")

            x_x = int(x_center_x - (x_w / 2))

            left_total = x_x
            right_total = CANVAS_SIZE[0] - (x_x + x_w)

            left_gap = max(20, int((left_total - home_w) / 2)) if home_w > 0 else max(20, int(left_total / 2))
            right_gap = max(20, int((right_total - league_w) / 2)) if league_w > 0 else max(20, int(right_total / 2))

            if home_logo is not None:
                home_x = left_gap
                home_y = int(content_center_y - (home_h / 2))
                img.alpha_composite(home_logo, (home_x, home_y))

            right_x = x_x + x_w + right_gap
            if league_logo is not None:
                league_y = int(content_center_y - (league_h / 2))
                img.alpha_composite(league_logo, (right_x, league_y))
            elif league_text:
                text_y = int(content_center_y - (text_h / 2))
                draw.text((right_x, text_y), league_text, font=league_text_font, fill="#FFFFFF")

            return img.convert("RGB")

        team_block_h = max(vs_h, home_h, enemy_h)
        if is_matchday:
            package_h = team_block_h + fixed_gap + league_render_h
            package_top = int((CANVAS_SIZE[1] / 2) - (package_h / 2))
            # Matchday Elemente 10% nach unten verschieben
            matchday_offset = int(CANVAS_SIZE[1] * 0.10)
            package_top += matchday_offset
            center_y = int(package_top + (team_block_h / 2))

        vs_x = int(center_x - (vs_w / 2))
        vs_y = int(center_y - (vs_h / 2))
        draw.text((vs_x, vs_y), vs_text, font=vs_font, fill="#FFFFFF")

        left_logo_right = vs_x - spacing
        right_logo_left = vs_x + vs_w + spacing

        home_bottom = vs_y + vs_h
        if home_logo is not None:
            home_pos = (int(left_logo_right - home_w), int(center_y - (home_h / 2)))
            img.alpha_composite(home_logo, home_pos)
            home_bottom = home_pos[1] + home_h

        enemy_bottom = vs_y + vs_h
        if enemy_logo is not None:
            enemy_pos = (int(right_logo_left), int(center_y - (enemy_h / 2)))
            img.alpha_composite(enemy_logo, enemy_pos)
            enemy_bottom = enemy_pos[1] + enemy_h

        team_block_bottom = max(vs_y + vs_h, home_bottom, enemy_bottom)
        visible_indices = self.visible_map_indices()
        slots = self.map_slots()

        league_top = team_block_bottom + fixed_gap
        league_center_y = league_top + int(league_render_h / 2)

        if visible_indices:
            required_maps_top = league_top + league_render_h + fixed_gap
            current_maps_top = min(slots[idx][1] for idx in visible_indices)
            map_shift = max(0, required_maps_top - current_maps_top)
            if map_shift > 0:
                slots = [(x1, y1 + map_shift, x2, y2 + map_shift) for (x1, y1, x2, y2) in slots]

        if league_img is not None:
            img.alpha_composite(league_img, (int(center_x - (league_render_w / 2)), int(league_center_y - (league_render_h / 2))))
        elif league_text:
            draw.text((center_x - text_w // 2, int(league_center_y - text_h / 2)), league_text, font=league_text_font, fill="#FFFFFF")

        if is_matchday:
            match_info_text = f"{self.match_date_var.get().strip()} - {self.match_time_var.get().strip()}"
            match_info_text = match_info_text.strip(" -")
            if match_info_text:
                info_font = get_font(34, bold=True)
                info_box = draw.textbbox((0, 0), match_info_text, font=info_font)
                info_w = info_box[2] - info_box[0]
                info_h = info_box[3] - info_box[1]
                info_x = int(center_x - (info_w / 2))
                info_y = int(league_top + league_render_h + 22)
                draw.text((info_x, info_y), match_info_text, font=info_font, fill="#FFFFFF")

        for idx in visible_indices:
            if idx >= len(slots):
                continue

            slot = slots[idx]

            map_name = self.map_vars[idx].get()
            map_asset = self.find_map_asset_path(game, map_name)
            if map_asset:
                self.paste_into_box(img, slot, image_path=map_asset)
            else:
                if map_name:
                    draw.text((slot[0] + 8, slot[1] + 8), map_name, font=helper_font, fill="#e5e7eb")

            home_score = parse_score(self.map_home_score_vars[idx].get().strip())
            away_score = parse_score(self.map_away_score_vars[idx].get().strip())
            result = None
            if home_score > away_score:
                result = "home"
            elif away_score > home_score:
                result = "away"

            card = img.crop((slot[0], slot[1], slot[2], slot[3])).convert("RGBA")
            self.draw_result_overlay(card, result)
            img.alpha_composite(card, (slot[0], slot[1]))

            score_text = f"{home_score:02d}:{away_score:02d}"
            sb = draw.textbbox((0, 0), score_text, font=score_font)
            sw = sb[2] - sb[0]
            sh = sb[3] - sb[1]
            sx = slot[0] + ((slot[2] - slot[0]) // 2) - (sw // 2)
            sy = slot[1] + ((slot[3] - slot[1]) // 2) - (sh // 2)
            draw.text((sx, sy), score_text, font=score_font, fill="#FFFFFF")

        return img.convert("RGB")

    def on_preview_container_resize(self, _event):
        self.render_preview(rebuild=False)

    def render_preview(self, rebuild=True):
        if rebuild or self.current_render_image is None:
            self.current_render_image = self.build_image()

        if self.current_render_image is None:
            return

        container_w = self.preview_container.winfo_width() if hasattr(self, "preview_container") else 0
        container_h = self.preview_container.winfo_height() if hasattr(self, "preview_container") else 0

        if container_w <= 1 or container_h <= 1:
            max_size = PREVIEW_SIZE
        else:
            max_size = (max(1, container_w - 8), max(1, container_h - 8))

        preview = self.current_render_image.copy()
        preview.thumbnail(max_size, Image.Resampling.LANCZOS)
        self.preview_image_tk = ImageTk.PhotoImage(preview)
        self.preview_label.configure(image=self.preview_image_tk)
        self.preview_label.configure(width=preview.width, height=preview.height)

    def export_jpg(self):
        file_path = filedialog.asksaveasfilename(
            title="Post als JPG speichern",
            defaultextension=".jpg",
            filetypes=[("JPEG", "*.jpg *.jpeg")],
            initialfile=f"{self.game_var.get().replace(' ', '_')}_{self.post_type_var.get().replace(' ', '_')}.jpg",
        )
        if not file_path:
            return

        try:
            image = self.build_image()
            image.save(file_path, "JPEG", quality=95)
            messagebox.showinfo("Erfolg", f"Post gespeichert:\n{file_path}")
        except Exception as exc:
            messagebox.showerror("Fehler", f"Export fehlgeschlagen:\n{exc}")


def show_startup_error(error_text):
    try:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Startfehler",
            "Die Anwendung konnte nicht gestartet werden.\n\n"
            "Details stehen in startup_error.log im Programmordner.",
        )
        root.destroy()
    except Exception:
        pass
    print(error_text)


if __name__ == "__main__":
    try:
        app = PostingApp()
        app.mainloop()
    except Exception:
        trace = traceback.format_exc()
        log_path = os.path.join(writable_base_dir(), "startup_error.log")
        with open(log_path, "w", encoding="utf-8") as log_file:
            log_file.write(trace)
        show_startup_error(trace)
