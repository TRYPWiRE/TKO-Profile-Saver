import customtkinter as ctk
from tkinter import messagebox
import tkinter as tk
import os, sys, json, random
import urllib.request, urllib.error

# ══════════════════════════════════════════════════════════════════════════════
# GLOBAL COLOUR PALETTE  (everything purple)
# ══════════════════════════════════════════════════════════════════════════════
PRIMARY   = "#8229b6"
HOVER     = "#5d1d83"
LIGHT     = "#a855f7"
DARK_BG   = "#1a0a2e"
SCROLL_C  = "#8229b6"

# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTS / PATHS
# ══════════════════════════════════════════════════════════════════════════════
def _resource_path(relative: str) -> str:
    """
    Return absolute path to a bundled asset.
    - When frozen by PyInstaller: files are in sys._MEIPASS (temp extraction folder).
    - When running as a plain script: files are next to this .py file.
    Use this ONLY for read-only assets shipped with the app (PNGs, ICO, JSON data).
    Do NOT use it for user data (profiles/, data/) — those must stay next to the exe.
    """
    import sys
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative)


PROFILES_DIR        = "profiles"
DATA_DIR            = "data"
WEAPON_PROFILE_FILE = os.path.join(DATA_DIR, "prestige_profiles.json")
WEAPON_CACHE_FILE   = os.path.join(DATA_DIR, "weapons_cache.json")
CAMO_PROFILE_FILE   = os.path.join(DATA_DIR, "camo_profiles.json")
CATEGORIES_FILE     = os.path.join(DATA_DIR, "categories.json")
CAMO_DATA_FILE      = _resource_path("bo7_camos_full.json")
CAMO_DATA_URL       = ""   # fill in your GitHub raw URL when ready

WEAPONS_DATA_URL    = "https://raw.githubusercontent.com/TRYPWiRE/BO7WeaponTracker/main/weapons_data.json"

PRESTIGE_OPTIONS = [f"Prestige {i}" for i in range(1, 11)] + ["Prestige Master"]
PRESTIGE_KEYS    = ("p1", "p2", "pm")

RANKS = ["Bronze", "Silver", "Gold", "Platinum", "Diamond", "Crimson", "Iridescent", "TOP250"]
RANK_ORDER = {r: i for i, r in enumerate(RANKS)}  # higher index = higher rank

# ══════════════════════════════════════════════════════════════════════════════
# DATA LOADERS
# ══════════════════════════════════════════════════════════════════════════════

def _load_json_file(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_json_file(path: str, data: dict):
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# ── Weapon prestige data ─────────────────────────────────────────────────────

def _fetch_weapons_data() -> dict:
    os.makedirs(DATA_DIR, exist_ok=True)
    try:
        with urllib.request.urlopen(WEAPONS_DATA_URL, timeout=5) as r:
            data = json.loads(r.read().decode("utf-8"))
        _save_json_file(WEAPON_CACHE_FILE, data)
        return data
    except Exception:
        pass
    return _load_json_file(WEAPON_CACHE_FILE)

WEAPONS_DATA: dict = _fetch_weapons_data()

def _load_prestige_profiles() -> dict:
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(WEAPON_PROFILE_FILE):
        _save_json_file(WEAPON_PROFILE_FILE, {"Default": {}})
        return {"Default": {}}
    return _load_json_file(WEAPON_PROFILE_FILE) or {"Default": {}}

def _save_prestige_profiles(data: dict):
    _save_json_file(WEAPON_PROFILE_FILE, data)

# ── Camo data ────────────────────────────────────────────────────────────────

def _fetch_camo_data() -> dict:
    """Try GitHub URL first, fall back to local file."""
    if CAMO_DATA_URL:
        try:
            with urllib.request.urlopen(CAMO_DATA_URL, timeout=5) as r:
                data = json.loads(r.read().decode("utf-8"))
            _save_json_file(CAMO_DATA_FILE, data)
            return data
        except Exception:
            pass
    # Local file (shipped alongside the script)
    return _load_json_file(CAMO_DATA_FILE)

CAMO_DATA: dict = _fetch_camo_data()
# CAMO_DATA structure: { mode: { "mastery": str, "weapons": { weapon_name: { "challenges": [...] } } } }

def _load_camo_profiles() -> dict:
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(CAMO_PROFILE_FILE):
        _save_json_file(CAMO_PROFILE_FILE, {"Default": {}})
        return {"Default": {}}
    return _load_json_file(CAMO_PROFILE_FILE) or {"Default": {}}

def _save_camo_profiles(data: dict):
    _save_json_file(CAMO_PROFILE_FILE, data)

def _load_categories() -> dict:
    """Returns {category_name: [profile_name, ...]}"""
    os.makedirs(DATA_DIR, exist_ok=True)
    data = _load_json_file(CATEGORIES_FILE)
    if not isinstance(data, dict):
        data = {}
    return data

def _save_categories(data: dict):
    _save_json_file(CATEGORIES_FILE, data)

def _get_profile_category(categories: dict, profile_name: str) -> str | None:
    for cat, profiles in categories.items():
        if profile_name in profiles:
            return cat
    return None

def _set_profile_category(categories: dict, profile_name: str, category: str | None):
    """Remove profile from any existing category then add to new one."""
    for profiles in categories.values():
        if profile_name in profiles:
            profiles.remove(profile_name)
    if category:
        categories.setdefault(category, [])
        if profile_name not in categories[category]:
            categories[category].append(profile_name)

# ══════════════════════════════════════════════════════════════════════════════
# TOOLTIP
# ══════════════════════════════════════════════════════════════════════════════

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget; self.text = text; self.tip = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, _=None):
        if self.tip or not self.text: return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 1
        self.tip = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tk.Label(tw, text=self.text, background="#ffffe0", relief="solid",
                 borderwidth=1, font=("tahoma", "8")).pack(ipadx=5, ipady=2)

    def hide(self, _=None):
        tw = self.tip; self.tip = None
        if tw: tw.destroy()

# ══════════════════════════════════════════════════════════════════════════════
# WEAPON PRESTIGE TRACKER PANEL
# ══════════════════════════════════════════════════════════════════════════════

class WeaponTrackerPanel:
    def __init__(self, parent_frame: ctk.CTkFrame, profile_name: str):
        self.frame        = parent_frame
        self.profile_name = profile_name
        self.prestige_profiles = _load_prestige_profiles()
        self.current_category  = list(WEAPONS_DATA.keys())[0] if WEAPONS_DATA else ""
        if profile_name not in self.prestige_profiles:
            self.prestige_profiles[profile_name] = {}
            _save_prestige_profiles(self.prestige_profiles)
        self._build()

    def _build(self):
        hdr = ctk.CTkFrame(self.frame, fg_color="transparent")
        hdr.pack(fill="x", padx=8, pady=(8, 2))
        ctk.CTkLabel(hdr, text="WEAPON PRESTIGE TRACKER",
                     font=("Segoe UI", 13, "bold"), text_color=PRIMARY).pack(side="left", padx=4)

        cat_row = ctk.CTkFrame(self.frame, fg_color="transparent")
        cat_row.pack(fill="x", padx=8, pady=(2, 0))
        ctk.CTkLabel(cat_row, text="Category:", font=("Segoe UI", 12, "bold")).pack(side="left", padx=4)
        self.cat_label = ctk.CTkLabel(cat_row, text=self.current_category,
                                      font=("Segoe UI", 12, "bold"), text_color=LIGHT)
        self.cat_label.pack(side="left", padx=4)

        cat_scroll = ctk.CTkScrollableFrame(self.frame, orientation="horizontal", height=44)
        cat_scroll.pack(fill="x", padx=8, pady=(4, 4))
        try: cat_scroll._scrollbar.configure(button_color=SCROLL_C)
        except Exception: pass

        self.cat_buttons: dict = {}
        for i, cat in enumerate(WEAPONS_DATA.keys()):
            btn = ctk.CTkButton(cat_scroll, text=self._cat_text(cat), width=160,
                                fg_color=PRIMARY, hover_color=HOVER,
                                command=lambda c=cat: self.select_category(c))
            btn.grid(row=0, column=i, padx=5, pady=4)
            self.cat_buttons[cat] = btn

        self.weapon_scroll = ctk.CTkScrollableFrame(self.frame)
        self.weapon_scroll.pack(fill="both", expand=True, padx=8, pady=(0, 4))
        try: self.weapon_scroll._scrollbar.configure(button_color=SCROLL_C)
        except Exception: pass

        totals_bar = ctk.CTkFrame(self.frame, fg_color="transparent")
        totals_bar.pack(fill="x", padx=8, pady=(2, 8))

        def badge(parent, text, color):
            f = ctk.CTkFrame(parent, corner_radius=8, border_width=2,
                             border_color=color, fg_color="transparent")
            l = ctk.CTkLabel(f, text=text, font=("Segoe UI", 12, "bold"), text_color=color)
            l.pack(padx=10, pady=4)
            return f, l

        self.p1_frame, self.p1_lbl = badge(totals_bar, "Prestige 1: 0",      "#9A9A9A")
        self.p2_frame, self.p2_lbl = badge(totals_bar, "Prestige 2: 0",      "#bbbbbb")
        self.pm_frame, self.pm_lbl = badge(totals_bar, "Prestige Master: 0", "#D4AF37")
        for f in (self.p1_frame, self.p2_frame, self.pm_frame):
            f.pack(side="left", padx=20)

        if self.current_category:
            self.select_category(self.current_category)

    def switch_profile(self, profile_name: str):
        self.profile_name = profile_name
        if profile_name not in self.prestige_profiles:
            self.prestige_profiles[profile_name] = {}
            _save_prestige_profiles(self.prestige_profiles)
        if self.current_category:
            self.select_category(self.current_category)
        else:
            self._update_totals()

    def select_category(self, category: str):
        self.current_category = category
        self.cat_label.configure(text=category)
        for w in self.weapon_scroll.winfo_children():
            w.destroy()

        if not WEAPONS_DATA:
            ctk.CTkLabel(self.weapon_scroll, text="No weapon data. Check connection.",
                         text_color="#ff6666").pack(pady=20)
            return

        hdr = ctk.CTkFrame(self.weapon_scroll)
        hdr.grid(row=0, column=0, sticky="ew", padx=6, pady=(6, 4))
        hdr.grid_columnconfigure(0, weight=1)
        for col, w in [(1, 160), (2, 160), (3, 190)]:
            hdr.grid_columnconfigure(col, minsize=w)
        ctk.CTkLabel(hdr, text="Weapon",          font=("Segoe UI", 12, "bold")).grid(row=0, column=0, sticky="w", padx=10)
        ctk.CTkLabel(hdr, text="Prestige 1",      font=("Segoe UI", 12, "bold")).grid(row=0, column=1)
        ctk.CTkLabel(hdr, text="Prestige 2",      font=("Segoe UI", 12, "bold")).grid(row=0, column=2)
        ctk.CTkLabel(hdr, text="Prestige Master", font=("Segoe UI", 12, "bold")).grid(row=0, column=3)

        for r, weapon in enumerate(WEAPONS_DATA.get(category, [])):
            row = ctk.CTkFrame(self.weapon_scroll)
            row.grid(row=r + 1, column=0, sticky="ew", padx=6, pady=2)
            row.grid_columnconfigure(0, weight=1)
            for col, w in [(1, 160), (2, 160), (3, 190)]:
                row.grid_columnconfigure(col, minsize=w)
            ctk.CTkLabel(row, text=weapon, font=("Segoe UI", 13, "bold")).grid(row=0, column=0, sticky="w", padx=10)
            entry = self._ensure_entry(category, weapon)
            v1 = ctk.BooleanVar(value=bool(entry["p1"]))
            v2 = ctk.BooleanVar(value=bool(entry["p2"]))
            vm = ctk.BooleanVar(value=bool(entry["pm"]))
            ctk.CTkCheckBox(row, text="", variable=v1, width=26, height=26,
                            checkmark_color=PRIMARY,
                            command=lambda wpn=weapon, v=v1: self._on_toggle(category, wpn, "p1", v)
                            ).grid(row=0, column=1)
            ctk.CTkCheckBox(row, text="", variable=v2, width=26, height=26,
                            checkmark_color=PRIMARY,
                            command=lambda wpn=weapon, v=v2: self._on_toggle(category, wpn, "p2", v)
                            ).grid(row=0, column=2)
            ctk.CTkCheckBox(row, text="", variable=vm, width=26, height=26,
                            checkmark_color=PRIMARY,
                            command=lambda wpn=weapon, v=vm: self._on_toggle(category, wpn, "pm", v)
                            ).grid(row=0, column=3)
            row._vars   = {"p1": v1, "p2": v2, "pm": vm}
            row._weapon = weapon

        self._update_totals()
        self._refresh_cat_buttons()

    # ── data helpers ──────────────────────────────────────────────────────────

    def _profile_root(self) -> dict:
        if self.profile_name not in self.prestige_profiles:
            self.prestige_profiles[self.profile_name] = {}
        return self.prestige_profiles[self.profile_name]

    def _ensure_entry(self, category: str, weapon: str) -> dict:
        root = self._profile_root()
        root.setdefault(category, {})
        root[category].setdefault(weapon, {"p1": False, "p2": False, "pm": False})
        for k in PRESTIGE_KEYS:
            root[category][weapon].setdefault(k, False)
        return root[category][weapon]

    def _set_prestige(self, category: str, weapon: str, key: str, value: bool):
        e = self._ensure_entry(category, weapon)
        if   key == "pm" and value:     e["p1"] = e["p2"] = e["pm"] = True
        elif key == "p2" and value:     e["p1"] = e["p2"] = True
        elif key == "p1" and not value: e["p1"] = e["p2"] = e["pm"] = False
        elif key == "p2" and not value: e["p2"] = e["pm"] = False
        elif key == "pm" and not value: e["p1"] = e["p2"] = e["pm"] = False
        else:                           e[key] = value
        _save_prestige_profiles(self.prestige_profiles)
        self._update_totals()

    def _on_toggle(self, category: str, weapon: str, key: str, var: ctk.BooleanVar):
        self._set_prestige(category, weapon, key, bool(var.get()))
        for row in self.weapon_scroll.winfo_children():
            if getattr(row, "_weapon", None) == weapon:
                e = self._ensure_entry(category, weapon)
                row._vars["p1"].set(e["p1"])
                row._vars["p2"].set(e["p2"])
                row._vars["pm"].set(e["pm"])
                break

    def _update_totals(self):
        p1 = p2 = pm = 0
        pd = self.prestige_profiles.get(self.profile_name, {})
        for cat, wlist in WEAPONS_DATA.items():
            cd = pd.get(cat, {})
            for wpn in wlist:
                e = cd.get(wpn)
                if not e: continue
                if e.get("p1"): p1 += 1
                if e.get("p2"): p2 += 1
                if e.get("pm"): pm += 1
        self.p1_lbl.configure(text=f"Prestige 1: {p1}")
        self.p2_lbl.configure(text=f"Prestige 2: {p2}")
        self.pm_lbl.configure(text=f"Prestige Master: {pm}")
        pd = self.prestige_profiles.get(self.profile_name, {})
        if pm >= 30 and not pd.get("_touch_grass_unlocked", False):
            pd["_touch_grass_unlocked"] = True
            _save_prestige_profiles(self.prestige_profiles)
            self._touch_grass()
        self._refresh_cat_buttons()

    def _cat_pm_progress(self, cat: str) -> tuple:
        pd      = self.prestige_profiles.get(self.profile_name, {})
        weapons = WEAPONS_DATA.get(cat, [])
        cd      = pd.get(cat, {})
        total   = len(weapons)
        done    = sum(1 for w in weapons if cd.get(w, {}).get("pm", False))
        return done, total

    def _cat_text(self, cat: str) -> str:
        done, total = self._cat_pm_progress(cat)
        if total == 0: return cat
        t = f"{cat} ({done}/{total})"
        if done == total: t += " ⭐✅"
        return t

    def _refresh_cat_buttons(self):
        for cat, btn in self.cat_buttons.items():
            btn.configure(text=self._cat_text(cat))

    def _touch_grass(self):
        popup = ctk.CTkToplevel(self.frame)
        popup.title("Congratulations!")
        popup.geometry("520x300")
        popup.resizable(False, False)
        popup.grab_set()
        canvas = tk.Canvas(popup, width=520, height=300, bg="#1E1E1E", highlightthickness=0)
        canvas.place(x=0, y=0)
        frame = ctk.CTkFrame(popup, corner_radius=12, fg_color="transparent")
        frame.place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(frame, text="Congratulations!", font=("Segoe UI", 18, "bold")).pack(pady=(10, 10))
        ctk.CTkLabel(frame,
                     text="You got 30 weapons to Prestige Master!\nUnlocked: \"Touch Grass\" calling card.\n\nNow seriously… go touch some grass.",
                     font=("Segoe UI", 13), justify="center", wraplength=460).pack(pady=(0, 16))
        confetti = []; running = [True]; GOLD = ["#FFD700", "#E6BE8A", "#D4AF37"]
        def spawn():
            if not running[0]: return
            x = random.randint(0, 520); sz = random.randint(6, 10)
            pid = canvas.create_rectangle(x, -sz, x+sz, sz, fill=random.choice(GOLD), outline="")
            confetti.append({"id": pid, "vy": random.uniform(2, 4.5), "vx": random.uniform(-1, 1)})
        def animate():
            if not running[0]: return
            for p in confetti[:]:
                canvas.move(p["id"], p["vx"], p["vy"])
                coords = canvas.coords(p["id"])
                if coords and coords[1] > 320:
                    canvas.delete(p["id"]); confetti.remove(p)
            if random.random() < 0.35: spawn()
            popup.after(30, animate)
        animate()
        def close(): running[0] = False; popup.destroy()
        ctk.CTkButton(frame, text="Ok, I'll touch grass",
                      fg_color=PRIMARY, hover_color=HOVER, command=close).pack(pady=(0, 10))


# ══════════════════════════════════════════════════════════════════════════════
# CAMO TRACKER PANEL
# ══════════════════════════════════════════════════════════════════════════════

CAMO_MODES = ["Multiplayer", "Warzone", "Zombies", "Endgame"]

# Mastery camo names + colours per mode (gold → final mastery, in order)
CAMO_MASTERIES = {
    "Multiplayer": [
        ("Shattered Gold", "#FFD700"),
        ("Arclight",       "#8ab4d4"),
        ("Tempest",        "#2244aa"),
        ("Singularity",    "#6a0dad"),
    ],
    "Zombies": [
        ("Golden Dragon",  "#FFD700"),
        ("Bloodstone",     "#ffb3c6"),
        ("Doomsteel",      "#4caf50"),
        ("Infestation",    "#8b0000"),
    ],
    "Endgame": [
        ("Molten Gold",    "#FFD700"),
        ("Moonstone",      "#ffb3c6"),
        ("Chroma Flux",    "#87ceeb"),
        ("Genesis",        "#1b5e20"),
    ],
    "Warzone": [
        ("Golden Damascus","#FFD700"),
        ("Starglass",      "#1a3a6b"),
        ("Absolute Zero",  "#87ceeb"),
        ("Apocalypse",     "#8b0000"),
    ],
}

class CamoTrackerPanel:
    """
    Camo tracker driven entirely by bo7_camos_full.json.
    JSON structure:
      { mode: { "mastery": str, "weapon_classes": { class: { weapon: {
          "military": [{name,target,display}],
          "special":  [{name,target,display}, ...],
          "mastery":  [{name,target,display}, ...]
      }}}}}
    Save keys per weapon entry:
      "mil_0"          = military challenge (always 1)
      "spc_0/1/2"      = special challenges
      "mst_0/1/2"      = JSON mastery challenges (sub-challenges)
      "camo_0/1/2/3"   = the 4 named camo unlocks (Shattered Gold etc.)
    Cascade rules:
      - tick any special → auto-tick military
      - tick gold (camo_0) → auto-tick military + all specials
      - untick military → untick all specials, mst challenges, all camos
    """

    def __init__(self, parent_frame: ctk.CTkFrame, profile_name: str):
        self.frame           = parent_frame
        self.profile_name    = profile_name
        self.camo_profiles   = _load_camo_profiles()
        self.current_mode    = CAMO_MODES[0]
        self.current_class   = None
        self.current_weapon  = None
        self._challenge_vars: list[ctk.BooleanVar] = []
        self._vars: dict[str, ctk.BooleanVar] = {}

        if profile_name not in self.camo_profiles:
            self.camo_profiles[profile_name] = {}
            _save_camo_profiles(self.camo_profiles)

        self._build()

    # ── build ─────────────────────────────────────────────────────────────────

    def _build(self):
        # Title
        title_row = ctk.CTkFrame(self.frame, fg_color="transparent")
        title_row.pack(fill="x", padx=8, pady=(8, 2))
        ctk.CTkLabel(title_row, text="CAMO TRACKER",
                     font=("Segoe UI", 13, "bold"), text_color=PRIMARY).pack(side="left", padx=4)

        # Mode buttons
        mode_row = ctk.CTkFrame(self.frame, fg_color="transparent")
        mode_row.pack(fill="x", padx=8, pady=(2, 6))
        ctk.CTkLabel(mode_row, text="Mode:", font=("Segoe UI", 12, "bold")).pack(side="left", padx=(4, 8))
        self._mode_btns: dict[str, ctk.CTkButton] = {}
        for mode in CAMO_MODES:
            mastery = CAMO_DATA.get(mode, {}).get("mastery", mode)
            btn = ctk.CTkButton(mode_row, text=f"{mode}  [{mastery}]",
                                width=190, fg_color=PRIMARY, hover_color=HOVER,
                                command=lambda m=mode: self._select_mode(m))
            btn.pack(side="left", padx=4)
            self._mode_btns[mode] = btn
        self._mode_btns[self.current_mode].configure(fg_color=HOVER)

        # Weapon class buttons
        cls_lbl = ctk.CTkFrame(self.frame, fg_color="transparent")
        cls_lbl.pack(fill="x", padx=8, pady=(0, 0))
        ctk.CTkLabel(cls_lbl, text="Class:", font=("Segoe UI", 12, "bold")).pack(side="left", padx=4)
        self._cls_lbl = ctk.CTkLabel(cls_lbl, text="None selected",
                                     font=("Segoe UI", 11), text_color=LIGHT)
        self._cls_lbl.pack(side="left", padx=4)

        self._cls_scroll = ctk.CTkScrollableFrame(self.frame, orientation="horizontal", height=48)
        self._cls_scroll.pack(fill="x", padx=8, pady=(2, 4))
        try: self._cls_scroll._scrollbar.configure(button_color=SCROLL_C)
        except Exception: pass
        self._cls_btns: dict[str, ctk.CTkButton] = {}

        # Weapon buttons
        wpn_lbl = ctk.CTkFrame(self.frame, fg_color="transparent")
        wpn_lbl.pack(fill="x", padx=8, pady=(0, 0))
        ctk.CTkLabel(wpn_lbl, text="Weapon:", font=("Segoe UI", 12, "bold")).pack(side="left", padx=4)
        self.wpn_selected_lbl = ctk.CTkLabel(wpn_lbl, text="None selected",
                                              font=("Segoe UI", 11), text_color=LIGHT)
        self.wpn_selected_lbl.pack(side="left", padx=4)

        self._wpn_scroll = ctk.CTkScrollableFrame(self.frame, orientation="horizontal", height=48)
        self._wpn_scroll.pack(fill="x", padx=8, pady=(2, 4))
        try: self._wpn_scroll._scrollbar.configure(button_color=SCROLL_C)
        except Exception: pass
        self._wpn_btns: dict[str, ctk.CTkButton] = {}

        # Challenge list
        self.challenge_frame = ctk.CTkScrollableFrame(self.frame, height=300)
        self.challenge_frame.pack(fill="both", expand=True, padx=8, pady=(0, 4))
        try: self.challenge_frame._scrollbar.configure(button_color=SCROLL_C)
        except Exception: pass

        # Progress bar + stats
        stats_row = ctk.CTkFrame(self.frame, fg_color="transparent")
        stats_row.pack(fill="x", padx=8, pady=(2, 2))
        self.progress_bar = ctk.CTkProgressBar(stats_row, progress_color=PRIMARY)
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", padx=4, pady=(0, 4))
        self.stats_label = ctk.CTkLabel(stats_row, text="",
                                        font=("Segoe UI", 11), text_color=LIGHT)
        self.stats_label.pack()

        # Mastery stats
        mastery_row = ctk.CTkFrame(self.frame, fg_color="transparent")
        mastery_row.pack(fill="x", padx=8, pady=(2, 8))
        ctk.CTkLabel(mastery_row, text="Final camo completed:",
                     font=("Segoe UI", 11, "bold")).pack(side="left", padx=4)
        self.mastery_label = ctk.CTkLabel(mastery_row, text="",
                                          font=("Segoe UI", 11), text_color=LIGHT)
        self.mastery_label.pack(side="left", padx=8)

        # Populate class buttons for default mode
        self._rebuild_class_buttons()
        self._update_mastery_stats()

    # ── profile switch ────────────────────────────────────────────────────────

    def switch_profile(self, profile_name: str):
        self.profile_name = profile_name
        if profile_name not in self.camo_profiles:
            self.camo_profiles[profile_name] = {}
            _save_camo_profiles(self.camo_profiles)
        self.current_weapon = None
        self.current_class  = None
        self._clear_challenges()
        self._clear_wpn_buttons()
        self._rebuild_class_buttons()
        self._update_mastery_stats()
        self.wpn_selected_lbl.configure(text="None selected")

    # ── mode ──────────────────────────────────────────────────────────────────

    def _select_mode(self, mode: str):
        for m, btn in self._mode_btns.items():
            btn.configure(fg_color=HOVER if m == mode else PRIMARY)
        self.current_mode   = mode
        self.current_class  = None
        self.current_weapon = None
        self._clear_challenges()
        self._clear_wpn_buttons()
        self._rebuild_class_buttons()
        self._update_mastery_stats()
        self._cls_lbl.configure(text="None selected")
        self.wpn_selected_lbl.configure(text="None selected")

    # ── class ──────────────────────────────────────────────────────────────────

    def _rebuild_class_buttons(self):
        for w in self._cls_scroll.winfo_children():
            w.destroy()
        self._cls_btns = {}
        classes = list(CAMO_DATA.get(self.current_mode, {})
                                .get("weapon_classes", {}).keys())
        if not classes:
            ctk.CTkLabel(self._cls_scroll,
                         text="No data. Check bo7_camos_full.json is in the script folder.",
                         text_color="#ff6666").grid(row=0, column=0, padx=8)
            return
        for i, cls in enumerate(classes):
            done, total = self._class_progress(cls)
            star = " ✅" if total and done == total else ""
            btn = ctk.CTkButton(self._cls_scroll,
                                text=f"{cls}{star}",
                                width=150, fg_color=PRIMARY, hover_color=HOVER,
                                command=lambda c=cls: self._select_class(c))
            btn.grid(row=0, column=i, padx=4, pady=4)
            self._cls_btns[cls] = btn

    def _select_class(self, cls: str):
        self.current_class  = cls
        self.current_weapon = None
        self._cls_lbl.configure(text=cls)
        self._clear_challenges()
        self._clear_wpn_buttons()
        self.wpn_selected_lbl.configure(text="None selected")

        weapons = (CAMO_DATA.get(self.current_mode, {})
                            .get("weapon_classes", {})
                            .get(cls, {}))
        for i, wpn_name in enumerate(weapons.keys()):
            done, total = self._weapon_progress(wpn_name)
            pct  = f" {done}/{total}" if total else ""
            star = " ✅" if total and done == total else ""
            btn  = ctk.CTkButton(self._wpn_scroll,
                                 text=f"{wpn_name}{pct}{star}",
                                 width=150, fg_color=PRIMARY, hover_color=HOVER,
                                 command=lambda w=wpn_name: self._select_weapon(w))
            btn.grid(row=0, column=i, padx=4, pady=4)
            self._wpn_btns[wpn_name] = btn

    # ── weapon ────────────────────────────────────────────────────────────────

    def _select_weapon(self, weapon_name: str):
        self.current_weapon = weapon_name
        self.wpn_selected_lbl.configure(text=weapon_name)
        self._render_challenges()

    def _clear_wpn_buttons(self):
        for w in self._wpn_scroll.winfo_children():
            w.destroy()
        self._wpn_btns = {}

    # ── render challenges ─────────────────────────────────────────────────────

    def _render_challenges(self):
        self._clear_challenges()
        if not self.current_weapon or not self.current_class:
            return

        wpn_data = (CAMO_DATA.get(self.current_mode, {})
                             .get("weapon_classes", {})
                             .get(self.current_class, {})
                             .get(self.current_weapon, {}))

        military = wpn_data.get("military", [])
        specials  = wpn_data.get("special",  [])
        mst_chals = wpn_data.get("mastery",  [])
        camo_list = CAMO_MASTERIES.get(self.current_mode, [])

        saved = self._get_weapon_data()
        self._vars = {}
        grid_r = 0

        def _sep(row, colour):
            f = ctk.CTkFrame(self.challenge_frame, fg_color=colour, height=2)
            f.grid(row=row, column=0, sticky="ew", padx=6, pady=(10, 2))
            return row + 1

        def _section_hdr(row, text):
            f = ctk.CTkFrame(self.challenge_frame, fg_color="transparent")
            f.grid(row=row, column=0, sticky="ew", padx=6, pady=(6, 2))
            ctk.CTkLabel(f, text=text, font=("Segoe UI", 11, "bold"),
                         text_color="#888888").pack(side="left", padx=10)
            return row + 1

        def _row(row, label, colour, save_key, bold=False):
            f = ctk.CTkFrame(self.challenge_frame)
            f.grid(row=row, column=0, sticky="ew", padx=6, pady=2)
            f.grid_columnconfigure(0, weight=1)
            f.grid_columnconfigure(1, minsize=70)
            w = "bold" if bold else "normal"
            ctk.CTkLabel(f, text=label, font=("Segoe UI", 12, w),
                         text_color=colour, anchor="w"
                         ).grid(row=0, column=0, sticky="w", padx=12, pady=6)
            var = ctk.BooleanVar(value=bool(saved.get(save_key, False)))
            ctk.CTkCheckBox(f, text="", variable=var, width=26, height=26,
                            checkmark_color=colour if colour not in ("#ffffff","white") else PRIMARY,
                            command=lambda v=var, k=save_key: self._on_toggle(k, v)
                            ).grid(row=0, column=1, pady=4)
            self._challenge_vars.append(var)
            self._vars[save_key] = var
            return row + 1

        # ── Column header ──
        hdr = ctk.CTkFrame(self.challenge_frame)
        hdr.grid(row=grid_r, column=0, sticky="ew", padx=6, pady=(6, 4))
        hdr.grid_columnconfigure(0, weight=1)
        hdr.grid_columnconfigure(1, minsize=70)
        ctk.CTkLabel(hdr, text=f"{self.current_weapon}  —  {self.current_mode}",
                     font=("Segoe UI", 12, "bold")
                     ).grid(row=0, column=0, sticky="w", padx=10)
        ctk.CTkLabel(hdr, text="Done?",
                     font=("Segoe UI", 12, "bold")).grid(row=0, column=1)
        grid_r += 1

        # ── Military (1 challenge) ──
        grid_r = _section_hdr(grid_r, "MILITARY")
        for i, ch in enumerate(military):
            grid_r = _row(grid_r, ch["display"], "#ffffff", f"mil_{i}")

        # ── Specials (3 challenges) ──
        grid_r = _sep(grid_r, "#555555")
        grid_r = _section_hdr(grid_r, "SPECIAL")
        for i, ch in enumerate(specials):
            grid_r = _row(grid_r, ch["display"], "#aaaaaa", f"spc_{i}", bold=True)

        # ── Mastery camos: first 3 each have a challenge from JSON, 4th has none ──
        grid_r = _sep(grid_r, PRIMARY)
        grid_r = _section_hdr(grid_r, "MASTERY CAMOS")
        for i, (camo_name, camo_col) in enumerate(camo_list):
            if i < len(mst_chals):
                # Show "Challenge • Camo Name" combined
                label = f"{mst_chals[i]['display']}  •  {camo_name}"
            else:
                # Final camo — no challenge required
                label = f"{camo_name}  (no challenge required)"
            grid_r = _row(grid_r, label, camo_col, f"camo_{i}", bold=True)

        self._refresh_progress()

    # ── toggle with cascade ───────────────────────────────────────────────────

    def _on_toggle(self, key: str, var: ctk.BooleanVar):
        value = bool(var.get())
        saved = self._get_weapon_data()
        saved[key] = value
        v = self._vars

        if value:
            # Any special ticked → auto-tick military
            if key.startswith("spc_"):
                saved["mil_0"] = True
                if "mil_0" in v: v["mil_0"].set(True)

            # Gold (camo_0) ticked → auto-tick military + all specials
            if key == "camo_0":
                saved["mil_0"] = True
                if "mil_0" in v: v["mil_0"].set(True)
                for k2 in [k for k in saved if k.startswith("spc_")]:
                    saved[k2] = True
                # also tick any spc_ vars present even if not yet in saved
                for k2 in [k for k in v if k.startswith("spc_")]:
                    saved[k2] = True
                    v[k2].set(True)

        else:
            # Military unticked → uncheck everything below
            if key == "mil_0":
                for k2 in list(v.keys()):
                    if k2 != "mil_0":
                        saved[k2] = False
                        v[k2].set(False)

        self._set_weapon_data(saved)
        self._refresh_progress()
        self._refresh_wpn_buttons()
        if key.startswith("camo_"):
            self._update_mastery_stats()
            self._refresh_cls_buttons()

    # ── progress ──────────────────────────────────────────────────────────────

    def _refresh_progress(self):
        if not self._challenge_vars:
            self.progress_bar.set(0)
            self.stats_label.configure(text="")
            return
        total = len(self._challenge_vars)
        done  = sum(1 for v in self._challenge_vars if v.get())
        self.progress_bar.set(done / total if total else 0)
        self.stats_label.configure(text=f"{done} / {total} challenges complete")

    def _refresh_wpn_buttons(self):
        for wpn, btn in self._wpn_btns.items():
            done, total = self._weapon_progress(wpn)
            pct  = f" {done}/{total}" if total else ""
            star = " ✅" if total and done == total else ""
            btn.configure(text=f"{wpn}{pct}{star}")

    def _refresh_cls_buttons(self):
        for cls, btn in self._cls_btns.items():
            done, total = self._class_progress(cls)
            star = " ✅" if total and done == total else ""
            btn.configure(text=f"{cls}{star}")

    def _update_mastery_stats(self):
        if not CAMO_DATA:
            self.mastery_label.configure(text="No data")
            return
        classes = CAMO_DATA.get(self.current_mode, {}).get("weapon_classes", {})
        total = sum(len(wpns) for wpns in classes.values())
        done  = 0
        profile = self.camo_profiles.get(self.profile_name, {})
        for cls, wpns in classes.items():
            for wpn in wpns:
                wpn_data = profile.get(self.current_mode, {}).get(wpn, {})
                if wpn_data.get("camo_3", False):   # final camo = camo_3
                    done += 1
        mastery_name = CAMO_DATA.get(self.current_mode, {}).get("mastery", "Mastery")
        self.mastery_label.configure(text=f"{mastery_name}: {done} / {total} weapons")

    # ── progress helpers ──────────────────────────────────────────────────────

    def _weapon_progress(self, weapon_name: str) -> tuple:
        """Count checked boxes vs total renderable rows for this weapon."""
        wpn_data = (CAMO_DATA.get(self.current_mode, {})
                             .get("weapon_classes", {})
                             .get(self.current_class or "", {})
                             .get(weapon_name, {}))
        n_mil  = len(wpn_data.get("military", []))
        n_spc  = len(wpn_data.get("special",  []))
        n_camo = len(CAMO_MASTERIES.get(self.current_mode, []))
        total  = n_mil + n_spc + n_camo
        if total == 0:
            return 0, 0
        saved = (self.camo_profiles.get(self.profile_name, {})
                                   .get(self.current_mode, {})
                                   .get(weapon_name, {}))
        done = 0
        for i in range(n_mil):
            if saved.get(f"mil_{i}", False): done += 1
        for i in range(n_spc):
            if saved.get(f"spc_{i}", False): done += 1
        for i in range(n_camo):
            if saved.get(f"camo_{i}", False): done += 1
        return done, total

    def _class_progress(self, cls: str) -> tuple:
        """All weapons in a class fully complete (camo_3 ticked)?"""
        weapons = (CAMO_DATA.get(self.current_mode, {})
                            .get("weapon_classes", {})
                            .get(cls, {}))
        total   = len(weapons)
        done    = 0
        profile = self.camo_profiles.get(self.profile_name, {})
        for wpn in weapons:
            if profile.get(self.current_mode, {}).get(wpn, {}).get("camo_3", False):
                done += 1
        return done, total

    # ── data helpers ──────────────────────────────────────────────────────────

    def _clear_challenges(self):
        for w in self.challenge_frame.winfo_children():
            w.destroy()
        self._challenge_vars = []
        self._vars = {}
        self.progress_bar.set(0)
        self.stats_label.configure(text="")

    def _get_weapon_data(self) -> dict:
        return (self.camo_profiles
                    .setdefault(self.profile_name, {})
                    .setdefault(self.current_mode, {})
                    .setdefault(self.current_weapon, {}))

    def _set_weapon_data(self, data: dict):
        (self.camo_profiles
             .setdefault(self.profile_name, {})
             .setdefault(self.current_mode, {})
             [self.current_weapon]) = data
        _save_camo_profiles(self.camo_profiles)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN APPLICATION
# ══════════════════════════════════════════════════════════════════════════════

_RANK_IMAGE_CACHE: dict = {}   # rank_name -> CTkImage or None

def _load_rank_image(rank: str, size: int = 28) -> object:
    """Load and cache a rank PNG scaled to size×size. Returns CTkImage or None."""
    key = (rank, size)
    if key in _RANK_IMAGE_CACHE:
        return _RANK_IMAGE_CACHE[key]
    path = _resource_path(f"{rank}.png")
    try:
        from PIL import Image
        from customtkinter import CTkImage as _CTkImage
        img = Image.open(path).convert("RGBA")
        img = img.resize((size, size), Image.LANCZOS)
        ctk_img = _CTkImage(light_image=img, dark_image=img, size=(size, size))
        _RANK_IMAGE_CACHE[key] = ctk_img
        return ctk_img
    except Exception:
        _RANK_IMAGE_CACHE[key] = None
        return None

class ProfileSaverApp:

    def __init__(self, root: ctk.CTk):
        self.root = root
        self.root.title("TKO'S PROFILE SAVER")
        self.root.geometry("1320x700")
        self.root.minsize(1100, 600)

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.current_profile: str | None = None
        self._suppress_autosave = False
        self._autosave_pending  = False
        self._email_real        = ""

        # Category state
        self._categories: dict      = _load_categories()
        self._current_category: str | None = None  # None = showing category view

        # Rank state — one selected rank per mode (or None)
        self._wz_rank: str | None = None
        self._mp_rank: str | None = None

        # Panel state
        self._tracker_open       = False
        self._camo_open          = False
        self._tracker_panel: WeaponTrackerPanel | None = None
        self._camo_panel:    CamoTrackerPanel   | None = None

        os.makedirs(PROFILES_DIR, exist_ok=True)

        self._build_sidebar()
        self._build_main()
        self.refresh_profile_list()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── sidebar ───────────────────────────────────────────────────────────────

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self.root, width=240)
        self.sidebar.pack(side="left", fill="y", padx=6, pady=6)
        self.sidebar.pack_propagate(False)

        ctk.CTkLabel(self.sidebar, text="TKO'S PROFILE SAVER",
                     font=("Helvetica", 16, "bold"),
                     text_color=PRIMARY).pack(pady=(14, 4))

        # Search bar (visible in profile view only)
        self.search_var = tk.StringVar()
        self._search_entry = ctk.CTkEntry(self.sidebar, placeholder_text="Search profiles...",
                                          textvariable=self.search_var)
        self._search_entry.bind("<KeyRelease>",
                                lambda e: self.refresh_profile_list(
                                    self.search_var.get().strip().lower() or None))

        # Back button (visible in profile view only)
        self._back_btn = ctk.CTkButton(self.sidebar, text="← Back to Categories",
                                       fg_color="#3d1a6b", hover_color="#2a0e4a",
                                       command=self._show_category_view)

        # Scrollable list — used for both categories and profiles
        self.profile_list = ctk.CTkScrollableFrame(self.sidebar)
        self.profile_list.pack(fill="both", expand=True, padx=10, pady=6)
        try: self.profile_list._scrollbar.configure(button_color=SCROLL_C)
        except Exception: pass

        # Bottom buttons
        self._new_cat_btn = ctk.CTkButton(self.sidebar, text="+ New Category",
                                          command=self._new_category,
                                          fg_color="#3d1a6b", hover_color="#2a0e4a")
        self._new_profile_btn = ctk.CTkButton(self.sidebar, text="+ New Profile",
                                              command=self.new_profile,
                                              fg_color=PRIMARY, hover_color=HOVER)

        # Start on category view
        self._show_category_view()

    # ── sidebar views ─────────────────────────────────────────────────────────

    def _show_category_view(self):
        """Switch sidebar to the category list."""
        self._current_category = None
        # Hide profile-only widgets
        self._search_entry.pack_forget()
        self._back_btn.pack_forget()
        self._new_profile_btn.pack_forget()
        # Show category-only widgets
        self._new_cat_btn.pack(fill="x", padx=10, pady=(0, 10))
        self._refresh_category_list()

    def _show_profile_view(self, category: str):
        """Switch sidebar into a specific category, showing its profiles."""
        self._current_category = category
        # Hide category-only widgets
        self._new_cat_btn.pack_forget()
        # Show profile-only widgets
        self._back_btn.pack(fill="x", padx=10, pady=(4, 2))
        self._search_entry.pack(fill="x", padx=10, pady=(2, 2))
        self._new_profile_btn.pack(fill="x", padx=10, pady=(0, 10))
        self.refresh_profile_list()

    def _refresh_category_list(self):
        for w in self.profile_list.winfo_children():
            w.destroy()

        # "All Profiles" shortcut
        all_row = ctk.CTkFrame(self.profile_list, fg_color="transparent")
        all_row.pack(fill="x", pady=2, padx=2)
        ctk.CTkButton(all_row, text="All Profiles", anchor="w",
                      fg_color="#333333", hover_color="#555555",
                      command=lambda: self._show_profile_view("__all__")
                      ).pack(side="left", fill="x", expand=True, padx=2, pady=2)

        # Uncategorised shortcut
        uncats = self._uncategorised_profiles()
        if uncats:
            uc_row = ctk.CTkFrame(self.profile_list, fg_color="transparent")
            uc_row.pack(fill="x", pady=2, padx=2)
            ctk.CTkButton(uc_row, text=f"Uncategorised  ({len(uncats)})", anchor="w",
                          fg_color="#444444", hover_color="#555555",
                          command=lambda: self._show_profile_view("__uncat__")
                          ).pack(side="left", fill="x", expand=True, padx=2, pady=2)

        if not self._categories:
            ctk.CTkLabel(self.profile_list, text="No categories yet.",
                         text_color="#888888").pack(pady=10)
            return

        for cat in sorted(self._categories.keys()):
            profiles_in_cat = [p for p in self._categories[cat]
                               if os.path.exists(os.path.join(PROFILES_DIR, p + ".json"))]
            row = ctk.CTkFrame(self.profile_list, fg_color="transparent")
            row.pack(fill="x", pady=2, padx=2)
            ctk.CTkButton(row, text=f"📁  {cat}  ({len(profiles_in_cat)})", anchor="w",
                          fg_color=PRIMARY, hover_color=HOVER,
                          command=lambda c=cat: self._show_profile_view(c)
                          ).pack(side="left", fill="x", expand=True, padx=2, pady=2)
            del_btn = ctk.CTkButton(row, text="x", width=28,
                                    fg_color="#6b0000", hover_color="#4a0000",
                                    command=lambda c=cat: self._delete_category(c))
            del_btn.pack(side="right", padx=2)
            ToolTip(del_btn, "Delete category (profiles kept)")

    def _uncategorised_profiles(self) -> list:
        all_files = [f[:-5] for f in os.listdir(PROFILES_DIR) if f.endswith(".json")]
        assigned  = {p for profiles in self._categories.values() for p in profiles}
        return [p for p in all_files if p not in assigned]

    # ── main area ─────────────────────────────────────────────────────────────

    def _build_main(self):
        self.main_area = ctk.CTkFrame(self.root)
        self.main_area.pack(side="right", fill="both", expand=True, padx=6, pady=6)

        # Top bar
        topbar = ctk.CTkFrame(self.main_area)
        topbar.pack(fill="x", padx=10, pady=(8, 4))

        self.profile_label = ctk.CTkLabel(topbar, text="No profile selected",
                                          font=("Helvetica", 14, "bold"),
                                          text_color="#888888")
        self.profile_label.pack(side="left", padx=8)

        ctk.CTkButton(topbar, text="ℹ  About", width=80,
                      fg_color="#2a2a2a", hover_color="#444444",
                      command=self._show_about).pack(side="left", padx=(4, 0))

        ctk.CTkButton(topbar, text="Delete Profile", width=110,
                      fg_color="#6b0000", hover_color="#4a0000",
                      command=self.delete_profile).pack(side="right", padx=6)

        ctk.CTkButton(topbar, text="Rename", width=80,
                      fg_color="#3d1a6b", hover_color="#2a0e4a",
                      command=self.rename_profile).pack(side="right", padx=4)

        # Camo tracker toggle
        self.camo_btn = ctk.CTkButton(topbar, text="Camo Tracker  v", width=155,
                                      fg_color=PRIMARY, hover_color=HOVER,
                                      command=self._toggle_camo)
        self.camo_btn.pack(side="right", padx=4)

        # Weapon prestige tracker toggle
        self.tracker_btn = ctk.CTkButton(topbar, text="Weapon Tracker  v", width=155,
                                         fg_color=HOVER, hover_color="#3d0d5e",
                                         command=self._toggle_tracker)
        self.tracker_btn.pack(side="right", padx=4)

        # Nexus banner
        self.nexus_frame = ctk.CTkFrame(self.main_area, fg_color=DARK_BG, height=32)
        self.nexus_frame.pack(fill="x", padx=10, pady=(0, 2))
        self.nexus_frame.pack_propagate(False)
        self.nexus_label = ctk.CTkLabel(self.nexus_frame, text="",
                                        font=("Helvetica", 13, "bold"), text_color="#FFD700")
        self.nexus_label.pack(expand=True)

        # Single unified scrollable canvas
        self.main_scroll = ctk.CTkScrollableFrame(self.main_area, fg_color="transparent")
        self.main_scroll.pack(fill="both", expand=True, padx=4, pady=4)
        try: self.main_scroll._scrollbar.configure(button_color=SCROLL_C)
        except Exception: pass

        self._build_info_fields(self.main_scroll)

        # Prestige tracker container (hidden until toggled)
        self.tracker_outer = ctk.CTkFrame(self.main_scroll,
                                          border_width=2, border_color=PRIMARY)

        # Camo tracker container (hidden until toggled)
        self.camo_outer = ctk.CTkFrame(self.main_scroll,
                                       border_width=2, border_color=LIGHT)

        # Status bar
        self.status_label = ctk.CTkLabel(self.main_area,
                                         text="Select or create a profile to begin.",
                                         text_color="#888888", font=("Helvetica", 11))
        self.status_label.pack(side="bottom", fill="x", padx=14, pady=(0, 6))

    # ── profile info fields ───────────────────────────────────────────────────

    def _build_info_fields(self, parent):
        content = parent

        # Level & Prestige
        row0 = ctk.CTkFrame(content, fg_color="transparent")
        row0.pack(fill="x", pady=(6, 4))
        self._sec(row0, "Overall Level")
        self.level_entry = ctk.CTkEntry(row0, placeholder_text="e.g. 55", width=100)
        self.level_entry.pack(side="left", padx=(0, 20))
        self.level_entry.bind("<KeyRelease>", self._schedule_autosave)

        self.prestige_var = tk.BooleanVar()
        ctk.CTkCheckBox(row0, text="Prestiged?", variable=self.prestige_var,
                        checkmark_color=PRIMARY,
                        command=self._on_prestige_toggle).pack(side="left", padx=(0, 8))
        self.prestige_frame = ctk.CTkFrame(row0, fg_color="transparent")
        self.prestige_option = ctk.CTkOptionMenu(self.prestige_frame, values=PRESTIGE_OPTIONS,
                                                 fg_color=PRIMARY, button_color=HOVER,
                                                 command=lambda _: (self._schedule_autosave(), self.refresh_profile_list()), width=160)
        self.prestige_option.set(PRESTIGE_OPTIONS[0])
        self.prestige_option.pack()

        # Unlocks
        flags_frame = ctk.CTkFrame(content, fg_color="transparent")
        flags_frame.pack(fill="x", pady=8)
        self._sec(flags_frame, "Unlocks", full=True)
        flags_inner = ctk.CTkFrame(flags_frame, fg_color="transparent")
        flags_inner.pack(fill="x")

        self.singularity_var = tk.BooleanVar()
        self.infestation_var = tk.BooleanVar()
        self.apocalypse_var  = tk.BooleanVar()
        self.genesis_var     = tk.BooleanVar()
        for label, var in [("Singularity?", self.singularity_var),
                            ("Infestation?", self.infestation_var),
                            ("Apocalypse?",  self.apocalypse_var),
                            ("Genesis?",     self.genesis_var)]:
            ctk.CTkCheckBox(flags_inner, text=label, variable=var,
                            checkmark_color=PRIMARY,
                            command=self._on_flags_changed).pack(side="left", padx=14, pady=4)

        # Ranks
        ranks_frame = ctk.CTkFrame(content)
        ranks_frame.pack(fill="x", pady=8, ipady=4)
        self._sec(ranks_frame, "Ranks", full=True)
        self._wz_rank_btns: dict[str, ctk.CTkButton] = {}
        self._mp_rank_btns: dict[str, ctk.CTkButton] = {}
        self._wz_rank_img_labels: dict[str, ctk.CTkLabel] = {}
        self._mp_rank_img_labels: dict[str, ctk.CTkLabel] = {}

        for mode_label, btn_dict, img_dict, getter, setter in [
            ("WZ Rank",  self._wz_rank_btns, self._wz_rank_img_labels,
             lambda: self._wz_rank, lambda r: setattr(self, "_wz_rank", r)),
            ("MP Rank",  self._mp_rank_btns, self._mp_rank_img_labels,
             lambda: self._mp_rank, lambda r: setattr(self, "_mp_rank", r)),
        ]:
            row = ctk.CTkFrame(ranks_frame, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=(2, 6))
            ctk.CTkLabel(row, text=f"Current Rank in {mode_label.split()[0]}:",
                         font=("Segoe UI", 12, "bold"), width=160, anchor="w").pack(side="left")
            for rank in RANKS:
                cell = ctk.CTkFrame(row, fg_color="transparent")
                cell.pack(side="left", padx=4)
                # Rank image (28px in the row; loaded lazily)
                img = _load_rank_image(rank, size=28)
                img_lbl = ctk.CTkLabel(cell, text="" if img else rank[0],
                                       image=img if img else None,
                                       width=28, height=28)
                img_lbl.pack()
                img_dict[rank] = img_lbl
                # Radio-style button (just the rank name, highlighted when selected)
                def _make_cmd(r=rank, g=getter, s=setter, bd=btn_dict):
                    def cmd():
                        cur = g()
                        new = None if cur == r else r   # toggle off if clicking same
                        s(new)
                        for rr, bb in bd.items():
                            bb.configure(fg_color=HOVER if rr == new else "#333333")
                        self._schedule_autosave()
                        self.refresh_profile_list()  # update sidebar rank icon immediately
                    return cmd
                btn = ctk.CTkButton(cell, text=rank, width=74, height=22,
                                    font=("Segoe UI", 9),
                                    fg_color="#333333", hover_color=HOVER,
                                    command=_make_cmd())
                btn.pack(pady=(2, 0))
                btn_dict[rank] = btn

        # Credentials
        creds_frame = ctk.CTkFrame(content)
        creds_frame.pack(fill="x", pady=8, ipady=6)
        self._sec(creds_frame, "Credentials", full=True)
        creds_inner = ctk.CTkFrame(creds_frame, fg_color="transparent")
        creds_inner.pack(fill="x", padx=14, pady=4)

        ctk.CTkLabel(creds_inner, text="Email:", width=70, anchor="w").grid(
            row=0, column=0, padx=(0, 6), pady=4, sticky="w")
        email_row = ctk.CTkFrame(creds_inner, fg_color="transparent")
        email_row.grid(row=0, column=1, padx=4, pady=4, sticky="w")
        self.email_entry = ctk.CTkEntry(email_row, placeholder_text="user@example.com", width=280)
        self.email_entry.pack(side="left")
        self.email_entry.bind("<KeyRelease>", self._on_email_keyrelease)
        self.show_email_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(email_row, text="Show", variable=self.show_email_var,
                        checkmark_color=PRIMARY,
                        command=self._toggle_email_visibility, width=60).pack(side="left", padx=6)

        ctk.CTkLabel(creds_inner, text="Password:", width=70, anchor="w").grid(
            row=1, column=0, padx=(0, 6), pady=4, sticky="w")
        pw_row = ctk.CTkFrame(creds_inner, fg_color="transparent")
        pw_row.grid(row=1, column=1, padx=4, pady=4, sticky="w")
        self.password_entry = ctk.CTkEntry(pw_row, placeholder_text="Password", width=280, show="*")
        self.password_entry.pack(side="left")
        self.password_entry.bind("<KeyRelease>", self._schedule_autosave)
        self.show_pw_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(pw_row, text="Show", variable=self.show_pw_var,
                        checkmark_color=PRIMARY,
                        command=self._toggle_pw_visibility, width=60).pack(side="left", padx=6)

        # Notes
        notes_frame = ctk.CTkFrame(content)
        notes_frame.pack(fill="both", expand=True, pady=8)
        self._sec(notes_frame, "Notes", full=True)
        self.notes_area = ctk.CTkTextbox(notes_frame, wrap="word", font=("Helvetica", 13), height=120)
        self.notes_area.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        self.notes_area.bind("<<Modified>>", self._on_textbox_modified)

    # ── toggle: prestige tracker ──────────────────────────────────────────────

    def _toggle_tracker(self):
        if not self.current_profile:
            messagebox.showinfo("No Profile", "Please select a profile first.")
            return
        if self._tracker_open:
            self.tracker_outer.pack_forget()
            self.tracker_btn.configure(text="Weapon Tracker  v")
            self._tracker_open = False
        else:
            self._tracker_open = True
            self.tracker_btn.configure(text="Weapon Tracker  ^")
            if self._tracker_panel is None:
                self._tracker_panel = WeaponTrackerPanel(self.tracker_outer, self.current_profile)
            else:
                self._tracker_panel.switch_profile(self.current_profile)
            # Pack tracker above camo (if camo is open, tracker goes before it)
            self.tracker_outer.pack(fill="x", padx=6, pady=(6, 4),
                                    before=self.camo_outer if self._camo_open else None)

    # ── toggle: camo tracker ──────────────────────────────────────────────────

    def _toggle_camo(self):
        if not self.current_profile:
            messagebox.showinfo("No Profile", "Please select a profile first.")
            return
        if self._camo_open:
            self.camo_outer.pack_forget()
            self.camo_btn.configure(text="Camo Tracker  v")
            self._camo_open = False
        else:
            self._camo_open = True
            self.camo_btn.configure(text="Camo Tracker  ^")
            if self._camo_panel is None:
                self._camo_panel = CamoTrackerPanel(self.camo_outer, self.current_profile)
            else:
                self._camo_panel.switch_profile(self.current_profile)
            self.camo_outer.pack(fill="x", padx=6, pady=(4, 10))

    def _ensure_panel_profiles(self):
        if self._tracker_open and self._tracker_panel and self.current_profile:
            self._tracker_panel.switch_profile(self.current_profile)
        if self._camo_open and self._camo_panel and self.current_profile:
            self._camo_panel.switch_profile(self.current_profile)

    # ── helpers ───────────────────────────────────────────────────────────────

    def _sec(self, parent, text, full=False):
        lbl = ctk.CTkLabel(parent, text=text, font=("Helvetica", 12, "bold"), text_color=PRIMARY)
        if full:
            lbl.pack(anchor="w", padx=12, pady=(6, 2))
        else:
            lbl.pack(side="left", padx=(12, 6))

    def _set_fields_state(self, state: str):
        for w in [self.level_entry, self.email_entry, self.password_entry]:
            w.configure(state=state)
        self.notes_area.configure(state=state)

    def _clear_fields(self):
        self._suppress_autosave = True
        self._email_real = ""
        self._wz_rank = None
        self._mp_rank = None
        self._apply_rank_highlights()
        self.level_entry.delete(0, "end")
        self.email_entry.delete(0, "end")
        self.password_entry.delete(0, "end")
        self.notes_area.delete("1.0", "end")
        self.prestige_var.set(False)
        self.singularity_var.set(False)
        self.infestation_var.set(False)
        self.apocalypse_var.set(False)
        self.genesis_var.set(False)
        self.prestige_option.set(PRESTIGE_OPTIONS[0])
        self._on_prestige_toggle()
        self._update_nexus()
        self._suppress_autosave = False

    # ── profile list ──────────────────────────────────────────────────────────

    def refresh_profile_list(self, keyword=None):
        """Rebuild the profile list for the current category view."""
        if self._current_category is None:
            # We're in category view — refresh that instead
            self._refresh_category_list()
            return

        for w in self.profile_list.winfo_children():
            w.destroy()

        all_files = sorted(f[:-5] for f in os.listdir(PROFILES_DIR) if f.endswith(".json"))

        if self._current_category == "__all__":
            names = all_files
        elif self._current_category == "__uncat__":
            names = self._uncategorised_profiles()
        else:
            cat_profiles = self._categories.get(self._current_category, [])
            names = [n for n in cat_profiles if n in all_files]

        # Category header label
        label = {"__all__": "All Profiles", "__uncat__": "Uncategorised"}.get(
            self._current_category, f"📁  {self._current_category}")
        ctk.CTkLabel(self.profile_list, text=label,
                     font=("Helvetica", 11, "bold"), text_color=LIGHT).pack(pady=(4, 6))

        if not names:
            ctk.CTkLabel(self.profile_list, text="No profiles here.",
                         text_color="#888888").pack(pady=8)
            return

        for name in names:
            if keyword and keyword not in name.lower():
                continue
            row = ctk.CTkFrame(self.profile_list, fg_color="transparent")
            row.pack(fill="x", pady=2, padx=2)
            color = HOVER if name == self.current_profile else PRIMARY

            # Icons to the left of the profile button
            data_peek     = self._read_profile(name) or {}
            prestige_rank = data_peek.get("prestige_rank", "") if data_peek.get("prestiged") else ""
            top_rank      = self._highest_rank_for(name)

            # Map prestige rank string → PNG filename
            # "Prestige 1" → "Prestige1", ..., "Prestige Master" → "PrestigeMaster"
            prestige_icon_name = None
            if prestige_rank:
                prestige_icon_name = prestige_rank.replace(" ", "")  # "Prestige 4" → "Prestige4"

            prestige_img = _load_rank_image(prestige_icon_name, size=22) if prestige_icon_name else None
            rank_img     = _load_rank_image(top_rank, size=22) if top_rank else None

            if prestige_img:
                p_lbl = ctk.CTkLabel(row, image=prestige_img, text="", width=24)
                p_lbl.pack(side="left", padx=(2, 0))
                ToolTip(p_lbl, prestige_rank)   # e.g. "Prestige 4" or "Prestige Master"

            if rank_img:
                # Work out which mode(s) the rank belongs to for the tooltip
                data_r  = self._read_profile(name) or {}
                wz_r    = data_r.get("wz_rank")
                mp_r    = data_r.get("mp_rank")
                if wz_r == top_rank and mp_r == top_rank:
                    rank_tip = f"{top_rank}  (WZ & MP)"
                elif wz_r == top_rank:
                    rank_tip = f"{top_rank}  (Warzone)"
                else:
                    rank_tip = f"{top_rank}  (Multiplayer)"
                r_lbl = ctk.CTkLabel(row, image=rank_img, text="", width=24)
                r_lbl.pack(side="left", padx=(2, 1))
                ToolTip(r_lbl, rank_tip)

            ctk.CTkButton(row, text=name, anchor="w",
                          fg_color=color, hover_color=HOVER,
                          command=lambda n=name: self.load_profile(n)
                          ).pack(side="left", fill="x", expand=True, padx=(1, 2), pady=2)
            mv = ctk.CTkButton(row, text="⇥", width=28,
                               fg_color="#3d1a6b", hover_color="#2a0e4a",
                               command=lambda n=name: self._move_profile_to_category(n))
            mv.pack(side="right", padx=1)
            ToolTip(mv, "Move to category")
            db = ctk.CTkButton(row, text="x", width=28,
                               fg_color="#6b0000", hover_color="#4a0000",
                               command=lambda n=name: self._quick_delete(n))
            db.pack(side="right", padx=1)
            ToolTip(db, "Delete this profile")

    # ── category CRUD ─────────────────────────────────────────────────────────

    def _new_category(self):
        dlg = ctk.CTkInputDialog(title="New Category", text="Enter category name:")
        name = dlg.get_input()
        if not name or not name.strip(): return
        name = name.strip()
        if name in self._categories:
            messagebox.showerror("Error", f"Category '{name}' already exists.")
            return
        self._categories[name] = []
        _save_categories(self._categories)
        self._refresh_category_list()

    def _delete_category(self, cat: str):
        if not messagebox.askyesno("Delete Category",
                                   f"Delete '{cat}'?\nProfiles inside will become uncategorised."):
            return
        self._categories.pop(cat, None)
        _save_categories(self._categories)
        self._refresh_category_list()

    def _move_profile_to_category(self, profile_name: str):
        """Show a dialog to assign a profile to a category."""
        cats = list(self._categories.keys())
        if not cats:
            messagebox.showinfo("No Categories", "Create a category first.")
            return
        # Build a simple popup with buttons for each category + Uncategorised
        popup = ctk.CTkToplevel(self.root)
        popup.title("Move to Category")
        popup.geometry("280x60")
        popup.grab_set()
        ctk.CTkLabel(popup, text=f"Move '{profile_name}' to:",
                     font=("Segoe UI", 12, "bold")).pack(pady=(10, 6))
        scroll = ctk.CTkScrollableFrame(popup, height=140)
        scroll.pack(fill="both", expand=True, padx=10, pady=(0, 6))

        def assign(cat):
            _set_profile_category(self._categories, profile_name, cat)
            _save_categories(self._categories)
            popup.destroy()
            self.refresh_profile_list()

        for cat in sorted(cats):
            ctk.CTkButton(scroll, text=f"📁  {cat}", anchor="w",
                          fg_color=PRIMARY, hover_color=HOVER,
                          command=lambda c=cat: assign(c)).pack(fill="x", pady=2)
        ctk.CTkButton(scroll, text="✕  Remove from all categories", anchor="w",
                      fg_color="#444444", hover_color="#555555",
                      command=lambda: assign(None)).pack(fill="x", pady=2)
        popup.geometry(f"280x{min(60 + 40 + (len(cats)+1)*36, 400)}")

    # ── profile CRUD ──────────────────────────────────────────────────────────

    def new_profile(self):
        dlg = ctk.CTkInputDialog(title="New Profile", text="Enter profile name:")
        name = dlg.get_input()
        if not name or not name.strip(): return
        name = name.strip()
        if os.path.exists(os.path.join(PROFILES_DIR, name + ".json")):
            messagebox.showerror("Error", f"Profile '{name}' already exists.")
            return
        self._write_profile(name, self._empty_data())
        # Auto-assign to current category if inside one
        if self._current_category and self._current_category not in ("__all__", "__uncat__"):
            _set_profile_category(self._categories, name, self._current_category)
            _save_categories(self._categories)
        self.refresh_profile_list()
        self.load_profile(name)

    def load_profile(self, name: str):
        self._suppress_autosave = True
        self.current_profile = name
        self.profile_label.configure(text=f"  {name}", text_color="#ffffff")
        data = self._read_profile(name) or self._empty_data()

        self.level_entry.delete(0, "end")
        self.level_entry.insert(0, data.get("level", ""))

        self.prestige_var.set(data.get("prestiged", False))
        self.prestige_option.set(data.get("prestige_rank", PRESTIGE_OPTIONS[0]))
        self._on_prestige_toggle()

        self.singularity_var.set(data.get("singularity", False))
        self.infestation_var.set(data.get("infestation",  False))
        self.apocalypse_var.set(data.get("apocalypse",   False))
        self.genesis_var.set(data.get("genesis",         False))

        self._email_real = data.get("email", "")
        self.show_email_var.set(False)
        self.email_entry.delete(0, "end")
        self.email_entry.insert(0, self._mask_email(self._email_real))

        self.password_entry.delete(0, "end")
        self.password_entry.insert(0, data.get("password", ""))

        self.notes_area.delete("1.0", "end")
        self.notes_area.insert("1.0", data.get("notes", ""))
        self.notes_area.edit_modified(False)

        # Ranks
        self._wz_rank = data.get("wz_rank", None)
        self._mp_rank = data.get("mp_rank", None)
        self._apply_rank_highlights()

        self._update_nexus()
        self._set_fields_state("normal")
        self._suppress_autosave = False
        self.refresh_profile_list()
        self._ensure_panel_profiles()
        self._set_status(f"Loaded: {name}")

    def rename_profile(self):
        if not self.current_profile: return
        dlg = ctk.CTkInputDialog(title="Rename Profile", text="Enter new name:")
        new = dlg.get_input()
        if not new or not new.strip(): return
        new = new.strip()
        old_path = os.path.join(PROFILES_DIR, self.current_profile + ".json")
        new_path = os.path.join(PROFILES_DIR, new + ".json")
        if os.path.exists(new_path):
            messagebox.showerror("Error", f"Profile '{new}' already exists.")
            return
        try:
            os.rename(old_path, new_path)
            self.current_profile = new
            self.profile_label.configure(text=f"  {new}")
            self.refresh_profile_list()
            self._set_status(f"Renamed to: {new}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def delete_profile(self):
        if not self.current_profile: return
        if messagebox.askyesno("Delete", f"Delete '{self.current_profile}' permanently?"):
            self._remove_profile_file(self.current_profile)

    def _quick_delete(self, name: str):
        if messagebox.askyesno("Delete", f"Delete '{name}' permanently?"):
            self._remove_profile_file(name)

    def _remove_profile_file(self, name: str):
        path = os.path.join(PROFILES_DIR, name + ".json")
        try:
            os.remove(path)
        except Exception as e:
            messagebox.showerror("Error", str(e)); return
        # Remove from any category
        _set_profile_category(self._categories, name, None)
        _save_categories(self._categories)
        if self.current_profile == name:
            self.current_profile = None
            self.profile_label.configure(text="No profile selected", text_color="#888888")
            self._clear_fields()
            self._set_fields_state("disabled")
        self.refresh_profile_list()
        self._set_status(f"Deleted: {name}")

    # ── data I/O ──────────────────────────────────────────────────────────────

    def _empty_data(self) -> dict:
        return {"level": "", "prestiged": False, "prestige_rank": PRESTIGE_OPTIONS[0],
                "singularity": False, "infestation": False, "apocalypse": False,
                "genesis": False, "wz_rank": None, "mp_rank": None,
                "email": "", "password": "", "notes": ""}

    def _read_profile(self, name: str):
        path = os.path.join(PROFILES_DIR, name + ".json")
        if not os.path.exists(path): return None
        try:
            with open(path, "r", encoding="utf-8") as f: return json.load(f)
        except Exception: return None

    def _write_profile(self, name: str, data: dict):
        path = os.path.join(PROFILES_DIR, name + ".json")
        try:
            with open(path, "w", encoding="utf-8") as f: json.dump(data, f, indent=2)
        except Exception as e: print("Save failed:", e)

    def _collect_data(self) -> dict:
        return {"level":         self.level_entry.get(),
                "prestiged":     self.prestige_var.get(),
                "prestige_rank": self.prestige_option.get(),
                "singularity":   self.singularity_var.get(),
                "infestation":   self.infestation_var.get(),
                "apocalypse":    self.apocalypse_var.get(),
                "genesis":       self.genesis_var.get(),
                "wz_rank":       self._wz_rank,
                "mp_rank":       self._mp_rank,
                "email":         getattr(self, "_email_real", self.email_entry.get()),
                "password":      self.password_entry.get(),
                "notes":         self.notes_area.get("1.0", "end-1c")}

    # ── auto-save ─────────────────────────────────────────────────────────────

    def _schedule_autosave(self, event=None):
        if self._suppress_autosave or not self.current_profile: return
        if not self._autosave_pending:
            self._autosave_pending = True
            self.root.after(800, self._do_autosave)

    def _do_autosave(self):
        self._autosave_pending = False
        if self.current_profile:
            self._write_profile(self.current_profile, self._collect_data())
            self._set_status(f"Auto-saved: {self.current_profile}")

    def _on_textbox_modified(self, event=None):
        if self.notes_area.edit_modified():
            self._schedule_autosave()
            self.notes_area.edit_modified(False)

    # ── checkbox / visibility ─────────────────────────────────────────────────

    def _on_prestige_toggle(self):
        if self.prestige_var.get():
            self.prestige_frame.pack(side="left", padx=4)
        else:
            self.prestige_frame.pack_forget()
        self._schedule_autosave()
        self.refresh_profile_list()

    def _on_flags_changed(self):
        self._update_nexus()
        self._schedule_autosave()

    def _update_nexus(self):
        all_on = all([self.singularity_var.get(), self.infestation_var.get(),
                      self.apocalypse_var.get(),  self.genesis_var.get()])
        if all_on and self.current_profile:
            self.nexus_label.configure(text="  NEXUS HORIZON UNLOCKED  ")
            self.nexus_frame.configure(fg_color=DARK_BG)
        else:
            self.nexus_label.configure(text="")
            self.nexus_frame.configure(fg_color="transparent")

    def _toggle_pw_visibility(self):
        self.password_entry.configure(show="" if self.show_pw_var.get() else "*")

    def _toggle_email_visibility(self):
        real = getattr(self, "_email_real", self.email_entry.get())
        self.email_entry.delete(0, "end")
        if self.show_email_var.get():
            self.email_entry.insert(0, real)
        else:
            self.email_entry.insert(0, self._mask_email(real))

    def _mask_email(self, email: str) -> str:
        if len(email) <= 6: return email
        return email[:6] + "*" * (len(email) - 6)

    def _on_email_keyrelease(self, event=None):
        if self.show_email_var.get():
            self._email_real = self.email_entry.get()
        self._schedule_autosave()

    # ── misc ──────────────────────────────────────────────────────────────────

    # ── rank helpers ──────────────────────────────────────────────────────────

    def _apply_rank_highlights(self):
        """Update rank button colours to reflect self._wz_rank / self._mp_rank."""
        for rank, btn in self._wz_rank_btns.items():
            btn.configure(fg_color=HOVER if rank == self._wz_rank else "#333333")
        for rank, btn in self._mp_rank_btns.items():
            btn.configure(fg_color=HOVER if rank == self._mp_rank else "#333333")

    def _highest_rank_for(self, profile_name: str) -> str | None:
        """Return the highest rank (WZ or MP) stored in a profile file, or None."""
        data = self._read_profile(profile_name)
        if not data:
            return None
        wz = data.get("wz_rank")
        mp = data.get("mp_rank")
        # Pick the higher of the two using RANK_ORDER; None = -1
        wz_i = RANK_ORDER.get(wz, -1)
        mp_i = RANK_ORDER.get(mp, -1)
        if wz_i == -1 and mp_i == -1:
            return None
        return wz if wz_i >= mp_i else mp

    # ── about window ─────────────────────────────────────────────────────────

    def _show_about(self):
        import webbrowser
        TKO_URL = "https://www.discord.gg/TKO1"

        win = ctk.CTkToplevel(self.root)
        win.title("About")
        win.geometry("380x400")
        win.resizable(False, False)
        win.grab_set()
        _apply_icon(win)

        # ── Title ──
        ctk.CTkLabel(win, text="TKO's PROFILE SAVER",
                     font=("Helvetica", 20, "bold"),
                     text_color=LIGHT).pack(pady=(28, 6))

        # ── Clickable logo ──
        logo_img = _load_rank_image("tko1", size=110)
        if logo_img:
            logo_lbl = ctk.CTkLabel(win, image=logo_img, text="",
                                    cursor="hand2")
            logo_lbl.pack(pady=(4, 8))
            logo_lbl.bind("<Button-1>", lambda e: webbrowser.open(TKO_URL))
        else:
            # fallback text link if image missing
            fb = ctk.CTkLabel(win, text="discord.gg/TKO1",
                              font=("Segoe UI", 12, "underline"),
                              text_color=LIGHT, cursor="hand2")
            fb.pack(pady=(4, 8))
            fb.bind("<Button-1>", lambda e: webbrowser.open(TKO_URL))

        # ── Credits ──
        ctk.CTkLabel(win, text="Brought to you by TRYPPY1",
                     font=("Segoe UI", 13, "bold"),
                     text_color=LIGHT).pack(pady=(2, 2))

        ctk.CTkLabel(win, text="Powered By AI",
                     font=("Segoe UI", 12, "bold"),
                     text_color="#4caf50").pack(pady=(2, 16))

        # ── Discord button ──
        ctk.CTkButton(win, text="Go to TKO!",
                      width=140, height=36,
                      fg_color=PRIMARY, hover_color=HOVER,
                      font=("Segoe UI", 13, "bold"),
                      command=lambda: webbrowser.open(TKO_URL)).pack(pady=(0, 16))

        # ── Close ──
        ctk.CTkButton(win, text="Close", width=80,
                      fg_color="#333333", hover_color="#555555",
                      command=win.destroy).pack()

    def _set_status(self, msg: str):
        self.status_label.configure(text=msg)

    def _on_close(self):
        if self.current_profile:
            self._write_profile(self.current_profile, self._collect_data())
        self.root.destroy()
        sys.exit()


# ══════════════════════════════════════════════════════════════════════════════
# SPLASH + ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def _apply_icon(window):
    """
    Apply tko1.ico / tko1.png as the window + taskbar icon.
    PyInstaller-safe: uses _resource_path() so assets are found in the temp bundle.

    CTkToplevel windows on Windows need a longer delay than the root window because
    they go through an extra internal init cycle before the HWND is ready.
    We schedule two attempts: after(0) for the root window case, and after(250) as a
    safety net for Toplevels — whichever fires when the handle is ready wins.
    """
    ico_path = _resource_path("tko1.ico")
    png_path = _resource_path("tko1.png")

    def _do_apply():
        try:
            if os.path.exists(ico_path):
                window.iconbitmap(ico_path)
                window.wm_iconbitmap(ico_path)
                # Force the underlying Tk window to also update — needed for CTkToplevel
                try:
                    window.update_idletasks()
                    window.iconbitmap(ico_path)
                except Exception:
                    pass
            elif os.path.exists(png_path):
                from PIL import Image, ImageTk
                img  = Image.open(png_path)
                icon = ImageTk.PhotoImage(img)
                window.iconphoto(True, icon)
                window._icon_ref = icon
        except Exception as e:
            print(f"Icon not applied: {e}")

    try:
        window.after(0,   _do_apply)   # first attempt — works for root window
        window.after(250, _do_apply)   # second attempt — catches CTkToplevel delay
    except Exception:
        _do_apply()


def show_splash_and_launch():
    root = ctk.CTk()
    root.withdraw()

    splash = ctk.CTkToplevel(root)
    splash.overrideredirect(True)
    _apply_icon(root)   # set on root early so Toplevel inherits it
    splash.geometry("380x300")
    splash.attributes("-alpha", 0.0)
    sw, sh = splash.winfo_screenwidth(), splash.winfo_screenheight()
    splash.geometry(f"380x300+{(sw-380)//2}+{(sh-300)//2}")

    # "TKO'S" heading
    ctk.CTkLabel(splash, text="TKO'S PROFILE SAVER",
                 font=("Helvetica", 22, "bold"), text_color=PRIMARY).pack(pady=(24, 4))

    # Logo image — load tko1.png if present, skip silently if not
    png_path = _resource_path("tko1.png")
    try:
        from PIL import Image
        from customtkinter import CTkImage
        logo_img  = Image.open(png_path)
        logo_img  = logo_img.resize((90, 90), Image.LANCZOS)
        ctk_logo  = CTkImage(light_image=logo_img, dark_image=logo_img, size=(90, 90))
        ctk.CTkLabel(splash, image=ctk_logo, text="").pack(pady=(0, 6))
        splash._logo_ref = ctk_logo          # prevent GC
    except Exception:
        pass                                 # image missing or Pillow not installed — skip

    ctk.CTkLabel(splash, text="Loading your profiles...",
                 font=("Helvetica", 12), text_color="#aaaaaa").pack(pady=(0, 4))

    bar = ctk.CTkProgressBar(splash, mode="determinate", width=280, progress_color=PRIMARY)
    bar.set(0)
    bar.pack(pady=(4, 16))

    def fade_in(step=0):
        splash.attributes("-alpha", step / 20)
        bar.set(step / 20)
        if step < 20: splash.after(50, fade_in, step + 1)
        else:         splash.after(900, fade_out)

    def fade_out(step=20):
        splash.attributes("-alpha", step / 20)
        if step > 0: splash.after(40, fade_out, step - 1)
        else:
            splash.destroy()
            root.deiconify()
            _apply_icon(root)
            app = ProfileSaverApp(root)
            app._set_fields_state("disabled")

    fade_in()
    root.mainloop()


if __name__ == "__main__":
    show_splash_and_launch()
