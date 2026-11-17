"""TrackMyEmissions - Carbon Emission Management System - Python + Tkinter + MySQL."""
import calendar
import csv
import hashlib
import os
import tkinter as tk
from datetime import date
from tkinter import ttk, messagebox, filedialog

import mysql.connector

# ---------- Database ----------
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "carbon_db"),
}

# category -> (unit, kg CO2 per unit)
FACTORS = {
    "Electricity": ("kWh", 0.82),
    "Diesel": ("litre", 2.68),
    "Petrol": ("litre", 2.31),
    "LPG": ("kg", 2.98),
    "Flights": ("km", 0.15),
    "Waste": ("kg", 0.50),
}
DEPARTMENTS = ["Admin", "Production", "IT", "Logistics", "Canteen"]
HIGH = 1000  # entries above this many kg CO2 are highlighted


def init_db():
    """First run: if the database doesn't exist yet, create it from schema.sql."""
    server = {k: v for k, v in DB_CONFIG.items() if k != "database"}
    conn = mysql.connector.connect(**server)
    try:
        cur = conn.cursor()
        cur.execute("SHOW DATABASES LIKE %s", (DB_CONFIG["database"],))
        if cur.fetchone():
            return  # already set up, keep existing data
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql"), encoding="utf-8") as f:
            for statement in f.read().split(";"):
                if statement.strip():
                    cur.execute(statement)
        conn.commit()
    finally:
        conn.close()


def run(sql, params=(), fetch=False):
    """Execute one query. Returns rows when fetch=True."""
    conn = mysql.connector.connect(**DB_CONFIG)
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        if fetch:
            return cur.fetchall()
        conn.commit()
    finally:
        conn.close()


# ---------- Styling: 2005-2015 era colours (Web 2.0 / Metro tiles) ----------
NAVY, SIDEBAR, BG, CARD = "#1f4e79", "#2d2d30", "#ececec", "#ffffff"
BLUE, GREEN, ORANGE, MAGENTA = "#1ba1e2", "#60a917", "#fa6800", "#d80073"
YELLOW, PURPLE, TEAL, RED = "#f0a30a", "#6a00ff", "#00aba9", "#e51400"
CAT_COLORS = dict(zip(FACTORS, [BLUE, ORANGE, MAGENTA, YELLOW, PURPLE, GREEN]))
FONT = "Verdana"


def setup_styles(root):
    s = ttk.Style(root)
    s.theme_use("clam")  # clam lets us colour buttons on every OS
    s.configure("TFrame", background=BG)
    s.configure("Card.TFrame", background=CARD, relief="solid", borderwidth=1, bordercolor="#c8c8c8")
    s.configure("Side.TFrame", background=SIDEBAR)
    s.configure("TLabel", background=BG, font=(FONT, 10))
    s.configure("Card.TLabel", background=CARD, font=(FONT, 11, "bold"), foreground="#333")
    s.configure("Page.TLabel", background=BG, font=(FONT, 16, "bold"), foreground="#333")
    s.configure("Header.TLabel", background=NAVY, foreground="white", font=(FONT, 16, "bold"))
    s.configure("TLabelframe", background=BG)
    s.configure("TLabelframe.Label", background=BG, font=(FONT, 11, "bold"), foreground=NAVY)
    s.configure("TRadiobutton", background=BG)
    s.configure("TCheckbutton", background=BG)
    s.configure("Treeview.Heading", font=(FONT, 9, "bold"), background="#dcdcdc")
    s.configure("Treeview", rowheight=24, font=(FONT, 9))
    # Sidebar buttons: normal and selected
    s.configure("Nav.TButton", background=SIDEBAR, foreground="#dddddd", font=(FONT, 11),
                anchor="w", padding=(18, 12), borderwidth=0)
    s.map("Nav.TButton", background=[("active", "#3e3e42")])
    s.configure("NavOn.TButton", background=GREEN, foreground="white", font=(FONT, 11, "bold"),
                anchor="w", padding=(18, 12), borderwidth=0)
    s.map("NavOn.TButton", background=[("active", GREEN)])
    for name, color in [("Green", GREEN), ("Orange", ORANGE), ("Red", RED),
                        ("Blue", BLUE), ("Grey", "#647687")]:
        s.configure(f"{name}.TButton", background=color, foreground="white",
                    font=(FONT, 10, "bold"), padding=6)
        s.map(f"{name}.TButton", background=[("active", color)])


# ---------- Login screen ----------
class LoginFrame(ttk.Frame):
    def __init__(self, root, on_success):
        super().__init__(root, padding=30)
        self.on_success = on_success
        ttk.Label(self, text="🌿 TrackMyEmissions Login", style="Header.TLabel",
                  anchor="center").grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 20), ipady=8)

        ttk.Label(self, text="Username").grid(row=1, column=0, sticky="w", pady=5)
        self.user = ttk.Entry(self, width=25)
        self.user.grid(row=1, column=1, pady=5)

        ttk.Label(self, text="Password").grid(row=2, column=0, sticky="w", pady=5)
        self.pwd = ttk.Entry(self, width=25, show="*")
        self.pwd.grid(row=2, column=1, pady=5)

        self.show = tk.BooleanVar()
        ttk.Checkbutton(self, text="Show password", variable=self.show,
                        command=lambda: self.pwd.config(show="" if self.show.get() else "*")
                        ).grid(row=3, column=1, sticky="w")

        ttk.Button(self, text="Login", style="Green.TButton", command=self.login
                   ).grid(row=4, column=0, columnspan=2, sticky="ew", pady=15)
        ttk.Label(self, text="Default: admin / admin123", foreground="grey").grid(row=5, column=0, columnspan=2)

        self.user.focus()
        root.bind("<Return>", lambda e: self.login())

    def login(self):
        hashed = hashlib.sha256(self.pwd.get().encode()).hexdigest()
        try:
            rows = run("SELECT id FROM users WHERE username=%s AND password=%s",
                       (self.user.get(), hashed), fetch=True)
        except mysql.connector.Error as e:
            return messagebox.showerror("Database Error", str(e))
        if rows:
            self.master.unbind("<Return>")
            self.on_success(self.user.get())
        else:
            messagebox.showerror("Login Failed", "Invalid username or password")


# ---------- Main application ----------
class CarbonApp(ttk.Frame):
    def __init__(self, root, username, on_logout):
        super().__init__(root)
        self.on_logout = on_logout
        self.monthly, self.by_cat, self.rows = [], [], {}
        self.build_menu(root)
        self.build_header(username)
        self.status = ttk.Label(self, text="Ready", relief="sunken", anchor="w")
        self.status.pack(side="bottom", fill="x")
        main = ttk.Frame(self)
        main.pack(fill="both", expand=True)
        self.build_sidebar(main)
        pages = ttk.Frame(main, padding=12)
        pages.pack(side="left", fill="both", expand=True)
        self.pages = {"dashboard": self.build_dashboard(pages), "records": self.build_records(pages)}
        self.show("dashboard")

    # --- UI builders ---
    def build_menu(self, root):
        menubar = tk.Menu(root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Dashboard", command=lambda: self.show("dashboard"))
        file_menu.add_command(label="Records", command=lambda: self.show("records"))
        file_menu.add_command(label="Export to CSV", command=self.export_csv)
        file_menu.add_separator()
        file_menu.add_command(label="Logout", command=self.on_logout)
        file_menu.add_command(label="Exit", command=root.quit)
        menubar.add_cascade(label="File", menu=file_menu)
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Emission Factors", command=lambda: messagebox.showinfo(
            "Emission Factors", "\n".join(f"{c}: {f} kg CO₂ per {u}" for c, (u, f) in FACTORS.items())))
        help_menu.add_command(label="About", command=lambda: messagebox.showinfo(
            "About", "TrackMyEmissions\nCarbon Emission Management System\nPython | Tkinter | MySQL"))
        menubar.add_cascade(label="Help", menu=help_menu)
        root.config(menu=menubar)

    def build_header(self, username):
        bar = tk.Frame(self, bg=NAVY)
        bar.pack(fill="x")
        tk.Label(bar, text="🌿 TrackMyEmissions", bg=NAVY, fg="white", font=(FONT, 18, "bold")
                 ).pack(side="left", padx=15, pady=10)
        tk.Label(bar, text="Carbon Emission Management System", bg=NAVY, fg="#9fc5e8",
                 font=(FONT, 10)).pack(side="left")
        tk.Label(bar, text=f"👤 {username}", bg=NAVY, fg="white", font=(FONT, 10)).pack(side="right", padx=15)
        tk.Frame(self, bg=GREEN, height=4).pack(fill="x")  # classic accent stripe

    def build_sidebar(self, parent):
        side = ttk.Frame(parent, style="Side.TFrame", width=180)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        self.nav = {}
        for key, text in [("dashboard", "📊  Dashboard"), ("records", "📋  Records")]:
            self.nav[key] = ttk.Button(side, text=text, style="Nav.TButton", command=lambda k=key: self.show(k))
            self.nav[key].pack(fill="x")
        ttk.Button(side, text="💾  Export CSV", style="Nav.TButton", command=self.export_csv).pack(fill="x")
        ttk.Button(side, text="🚪  Logout", style="Nav.TButton", command=self.on_logout).pack(side="bottom", fill="x")

    def build_dashboard(self, parent):
        page = ttk.Frame(parent)
        ttk.Label(page, text="Emissions Overview", style="Page.TLabel").pack(anchor="w")
        ttk.Label(page, text="All departments · values in kg CO₂e", foreground="grey").pack(anchor="w", pady=(0, 10))

        # Metro-style coloured tiles
        tiles = ttk.Frame(page)
        tiles.pack(fill="x")
        self.tiles = {}
        for i, (key, title, color) in enumerate([("total", "TOTAL EMISSIONS", BLUE), ("month", "THIS MONTH", ORANGE),
                                                 ("entries", "ENTRIES", GREEN), ("top", "TOP SOURCE", MAGENTA)]):
            tile = tk.Frame(tiles, bg=color, padx=15, pady=10)
            tile.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 10, 0))
            tk.Label(tile, text=title, bg=color, fg="white", font=(FONT, 9, "bold")).pack(anchor="w")
            self.tiles[key] = tk.Label(tile, bg=color, fg="white", font=(FONT, 20, "bold"))
            self.tiles[key].pack(anchor="w")
            tiles.columnconfigure(i, weight=1)

        # Charts drawn on Canvas widgets
        charts = ttk.Frame(page)
        charts.pack(fill="x", pady=12)
        self.bar = self.card(charts, "📈 Monthly Emissions (last 6 months)", side="left", expand=True)
        self.donut = self.card(charts, "🍩 By Category", side="left", width=340, padx=(12, 0))
        for canvas in (self.bar, self.donut):
            canvas.bind("<Configure>", lambda e: self.draw_charts())

        # Top emitters table
        box = ttk.Frame(page, style="Card.TFrame", padding=10)
        box.pack(fill="both", expand=True)
        ttk.Label(box, text="🔥 Top Emitting Entries", style="Card.TLabel").pack(anchor="w", pady=(0, 6))
        cols = ("date", "department", "category", "quantity", "co2", "status")
        self.top_tree = ttk.Treeview(box, columns=cols, show="headings", height=6)
        for col in cols:
            self.top_tree.heading(col, text=col.title() if col != "co2" else "CO₂ (kg)")
            self.top_tree.column(col, anchor="center", width=120)
        self.top_tree.tag_configure("high", foreground=RED)
        self.top_tree.pack(fill="both", expand=True)
        return page

    def card(self, parent, title, side, width=None, expand=False, padx=0):
        """White bordered box with a title and a Canvas. Returns the canvas."""
        box = ttk.Frame(parent, style="Card.TFrame", padding=10)
        box.pack(side=side, fill="both", expand=expand, padx=padx)
        ttk.Label(box, text=title, style="Card.TLabel").pack(anchor="w")
        canvas = tk.Canvas(box, height=220, bg=CARD, highlightthickness=0, **({"width": width} if width else {}))
        canvas.pack(fill="both", expand=True)
        return canvas

    def build_records(self, parent):
        page = ttk.Frame(parent)
        form = ttk.LabelFrame(page, text="✏️ Emission Entry", padding=10)
        form.pack(side="left", fill="y", padx=(0, 10))

        self.v = {k: tk.StringVar() for k in ("id", "date", "dept", "cat", "qty")}
        fields = [("Entry ID", ttk.Entry(form, textvariable=self.v["id"], state="readonly")),
                  ("Date", ttk.Entry(form, textvariable=self.v["date"])),
                  ("Department", ttk.Combobox(form, textvariable=self.v["dept"], values=DEPARTMENTS, state="readonly")),
                  ("Category", ttk.Combobox(form, textvariable=self.v["cat"], values=list(FACTORS), state="readonly")),
                  ("Quantity", ttk.Spinbox(form, textvariable=self.v["qty"], from_=0, to=100000, increment=10))]
        for i, (label, widget) in enumerate(fields):
            ttk.Label(form, text=label).grid(row=i, column=0, sticky="w", pady=4)
            widget.grid(row=i, column=1, pady=4, sticky="ew")
        self.unit_lbl = ttk.Label(form, foreground="grey")
        self.unit_lbl.grid(row=5, column=1, sticky="w")

        # Live CO2 preview: updates whenever category or quantity changes
        self.co2_lbl = tk.Label(form, bg=TEAL, fg="white", font=(FONT, 12, "bold"), pady=8)
        self.co2_lbl.grid(row=6, column=0, columnspan=2, sticky="ew", pady=8)
        self.v["cat"].trace_add("write", self.preview)
        self.v["qty"].trace_add("write", self.preview)

        ttk.Label(form, text="Notes").grid(row=7, column=0, sticky="nw", pady=4)
        self.notes = tk.Text(form, width=22, height=4, font=(FONT, 10),
                             bg="white", fg="black", insertbackground="black")
        self.notes.grid(row=7, column=1, pady=4)

        btns = ttk.Frame(form)
        btns.grid(row=8, column=0, columnspan=2, pady=10, sticky="ew")
        for i, (text, style, cmd) in enumerate([
                ("Add", "Green", self.add), ("Update", "Orange", self.update),
                ("Delete", "Red", self.delete), ("Clear", "Grey", self.clear)]):
            ttk.Button(btns, text=text, style=f"{style}.TButton", command=cmd
                       ).grid(row=i // 2, column=i % 2, sticky="ew", padx=3, pady=3)
        btns.columnconfigure((0, 1), weight=1)

        right = ttk.Frame(page)
        right.pack(side="left", fill="both", expand=True)
        search = ttk.LabelFrame(right, text="🔍 Search", padding=8)
        search.pack(fill="x")
        self.search_by = tk.StringVar(value="department")
        ttk.Radiobutton(search, text="Department", variable=self.search_by, value="department").pack(side="left")
        ttk.Radiobutton(search, text="Category", variable=self.search_by, value="category").pack(side="left", padx=8)
        self.search_text = tk.StringVar()
        ttk.Entry(search, textvariable=self.search_text, width=25).pack(side="left", padx=5)
        ttk.Button(search, text="Search", style="Blue.TButton", command=self.search).pack(side="left", padx=3)
        ttk.Button(search, text="Show All", style="Grey.TButton", command=self.refresh).pack(side="left", padx=3)

        table = ttk.Frame(right)
        table.pack(fill="both", expand=True, pady=(8, 0))
        cols = ("id", "date", "department", "category", "quantity", "co2", "notes")
        self.tree = ttk.Treeview(table, columns=cols, show="headings")
        for col, w in zip(cols, [45, 95, 100, 95, 100, 90, 180]):
            self.tree.heading(col, text=col.title() if col != "co2" else "CO₂ (kg)")
            self.tree.column(col, width=w, anchor="center")
        ys = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=ys.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        ys.grid(row=0, column=1, sticky="ns")
        table.rowconfigure(0, weight=1)
        table.columnconfigure(0, weight=1)
        self.tree.tag_configure("odd", background="#f2f6fa")  # zebra rows
        self.tree.tag_configure("high", background="#ffe0b2")
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        ttk.Label(right, text=f"🟧 High emission (≥ {HIGH} kg CO₂)", foreground="grey").pack(anchor="w", pady=4)
        self.clear()
        return page

    # --- Navigation ---
    def show(self, name):
        for key, frame in self.pages.items():
            frame.pack_forget()
            self.nav[key].configure(style="Nav.TButton")
        self.pages[name].pack(fill="both", expand=True)
        self.nav[name].configure(style="NavOn.TButton")
        self.refresh()

    # --- Data loading ---
    def refresh(self):
        try:
            self.load_rows(run("SELECT * FROM emissions ORDER BY entry_date DESC", fetch=True))
            self.load_dashboard()
        except mysql.connector.Error as e:
            messagebox.showerror("Database Error", str(e))

    def load_rows(self, rows):
        self.tree.delete(*self.tree.get_children())
        self.rows = {}
        for i, (rid, day, dept, cat, qty, co2, notes) in enumerate(rows):
            self.rows[str(rid)] = (rid, day, dept, cat, qty, co2, notes)
            unit = FACTORS.get(cat, ("", 0))[0]
            tag = "high" if co2 >= HIGH else "odd" if i % 2 else ""
            self.tree.insert("", "end", iid=str(rid), tags=(tag,),
                             values=(rid, day, dept, cat, f"{float(qty):g} {unit}", f"{co2:,.2f}", notes or ""))
        self.status.config(text=f"{len(rows)} record(s) shown")

    def load_dashboard(self):
        total, count = run("SELECT COALESCE(SUM(co2_kg), 0), COUNT(*) FROM emissions", fetch=True)[0]
        month = run("SELECT COALESCE(SUM(co2_kg), 0) FROM emissions WHERE YEAR(entry_date) = YEAR(CURDATE()) "
                    "AND MONTH(entry_date) = MONTH(CURDATE())", fetch=True)[0][0]
        self.by_cat = [(c, float(v)) for c, v in run(
            "SELECT category, SUM(co2_kg) FROM emissions GROUP BY category ORDER BY 2 DESC", fetch=True)]
        monthly = run("SELECT YEAR(entry_date), MONTH(entry_date), SUM(co2_kg) FROM emissions "
                      "GROUP BY 1, 2 ORDER BY 1, 2", fetch=True)[-6:]
        self.monthly = [(calendar.month_abbr[m], float(v)) for _, m, v in monthly]

        self.tiles["total"].config(text=f"{total / 1000:,.1f} t")
        self.tiles["month"].config(text=f"{month / 1000:,.1f} t")
        self.tiles["entries"].config(text=count)
        self.tiles["top"].config(text=self.by_cat[0][0] if self.by_cat else "-")

        self.top_tree.delete(*self.top_tree.get_children())
        for day, dept, cat, qty, co2 in run("SELECT entry_date, department, category, quantity, co2_kg "
                                            "FROM emissions ORDER BY co2_kg DESC LIMIT 6", fetch=True):
            high = co2 >= HIGH
            self.top_tree.insert("", "end", tags=("high",) if high else (), values=(
                day, dept, cat, f"{float(qty):g} {FACTORS.get(cat, ('', 0))[0]}", f"{co2:,.2f}",
                "▲ High" if high else "Normal"))
        self.draw_charts()

    # --- Charts ---
    def draw_charts(self):
        self.draw_bars()
        self.draw_donut()

    def draw_bars(self):
        c = self.bar
        c.delete("all")
        w, h = c.winfo_width(), c.winfo_height()
        if not self.monthly:
            return c.create_text(w / 2, h / 2, text="No data", fill="grey")
        top = max(v for _, v in self.monthly) or 1
        slot = (w - 20) / len(self.monthly)
        base = h - 25
        c.create_line(10, base, w - 10, base, fill="#999")
        for i, (label, val) in enumerate(self.monthly):
            x0 = 10 + i * slot + slot * 0.25
            x1 = x0 + slot * 0.5
            y0 = base - (h - 55) * val / top
            c.create_rectangle(x0, y0, x1, base, fill=GREEN, outline="#4a8a10")
            c.create_rectangle(x0 + 1, y0 + 1, x1, (y0 + base) / 2, fill="#8fd14f", outline="")  # glossy top
            c.create_text((x0 + x1) / 2, y0 - 10, text=f"{val:,.0f}", font=(FONT, 8), fill="#333")
            c.create_text((x0 + x1) / 2, base + 12, text=label, font=(FONT, 9), fill="#555")

    def draw_donut(self):
        c = self.donut
        c.delete("all")
        total = sum(v for _, v in self.by_cat)
        if not total:
            return
        cx, cy, r = 95, c.winfo_height() / 2, 85
        start = 90
        for cat, val in self.by_cat:
            extent = -359.99 * val / total
            c.create_arc(cx - r, cy - r, cx + r, cy + r, start=start, extent=extent,
                         fill=CAT_COLORS.get(cat, "grey"), outline="white", width=2)
            start += extent
        c.create_oval(cx - 48, cy - 48, cx + 48, cy + 48, fill=CARD, outline="")
        c.create_text(cx, cy - 8, text=f"{total / 1000:,.1f} t", font=(FONT, 14, "bold"), fill="#333")
        c.create_text(cx, cy + 14, text="CO₂e", font=(FONT, 9), fill="grey")
        for i, (cat, val) in enumerate(self.by_cat):  # legend
            y = cy - len(self.by_cat) * 13 + i * 26 + 13
            c.create_rectangle(200, y - 6, 212, y + 6, fill=CAT_COLORS.get(cat, "grey"), outline="")
            c.create_text(220, y, text=f"{cat}  {val / total:.0%}", anchor="w", font=(FONT, 9), fill="#333")

    # --- Form helpers ---
    def preview(self, *_):
        unit, factor = FACTORS.get(self.v["cat"].get(), ("", 0))
        try:
            qty = float(self.v["qty"].get() or 0)
        except ValueError:
            qty = 0
        self.unit_lbl.config(text=f"in {unit}  (× {factor} kg CO₂)" if unit else "")
        self.co2_lbl.config(text=f"= {qty * factor:,.2f} kg CO₂e")

    def form_values(self):
        """Return [date, dept, category, qty, co2, notes] or None if invalid."""
        cat, dept = self.v["cat"].get(), self.v["dept"].get()
        if not (self.v["date"].get() and dept and cat in FACTORS):
            return messagebox.showwarning("Missing", "Date, Department and Category are required")
        try:
            qty = float(self.v["qty"].get())
        except ValueError:
            return messagebox.showwarning("Invalid", "Quantity must be a number")
        co2 = round(qty * FACTORS[cat][1], 2)
        return [self.v["date"].get().strip(), dept, cat, qty, co2, self.notes.get("1.0", "end").strip() or None]

    def safe(self, action, success_msg):
        """Run a DB action, show errors nicely, then refresh."""
        try:
            action()
            messagebox.showinfo("Success", success_msg)
            self.refresh()
            self.clear()
        except mysql.connector.Error as e:
            messagebox.showerror("Database Error", str(e))

    # --- CRUD ---
    def add(self):
        v = self.form_values()
        if v:
            self.safe(lambda: run("INSERT INTO emissions (entry_date, department, category, quantity, co2_kg, notes) "
                                  "VALUES (%s, %s, %s, %s, %s, %s)", v), "Entry added")

    def update(self):
        if not self.v["id"].get():
            return messagebox.showwarning("Select", "Select an entry to update")
        v = self.form_values()
        if v:
            self.safe(lambda: run("UPDATE emissions SET entry_date=%s, department=%s, category=%s, quantity=%s, "
                                  "co2_kg=%s, notes=%s WHERE id=%s", v + [self.v["id"].get()]), "Entry updated")

    def delete(self):
        rid = self.v["id"].get()
        if not rid:
            return messagebox.showwarning("Select", "Select an entry to delete")
        if messagebox.askyesno("Confirm", f"Delete entry #{rid}?"):
            self.safe(lambda: run("DELETE FROM emissions WHERE id=%s", (rid,)), "Entry deleted")

    def search(self):
        col = self.search_by.get()  # only "department" or "category" from the radio buttons
        try:
            self.load_rows(run(f"SELECT * FROM emissions WHERE {col} LIKE %s ORDER BY entry_date DESC",
                               (f"%{self.search_text.get()}%",), fetch=True))
        except mysql.connector.Error as e:
            messagebox.showerror("Database Error", str(e))

    def clear(self):
        for var in self.v.values():
            var.set("")
        self.v["date"].set(date.today().isoformat())
        self.notes.delete("1.0", "end")
        self.tree.selection_remove(self.tree.selection())

    def on_select(self, _event):
        sel = self.tree.selection()
        if not sel:
            return
        rid, day, dept, cat, qty, _co2, notes = self.rows[sel[0]]
        for key, val in zip(("id", "date", "dept", "cat", "qty"), (rid, day, dept, cat, f"{float(qty):g}")):
            self.v[key].set(val)
        self.notes.delete("1.0", "end")
        self.notes.insert("1.0", notes or "")

    def export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if path:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f)
                w.writerow(("id", "entry_date", "department", "category", "quantity", "co2_kg", "notes"))
                w.writerows(self.rows.values())
            messagebox.showinfo("Exported", f"Saved to {path}")


# ---------- Entry point ----------
def main():
    root = tk.Tk()
    root.title("TrackMyEmissions - Carbon Emission Management System")
    root.configure(bg=BG)
    setup_styles(root)
    try:
        init_db()
    except mysql.connector.Error as e:
        messagebox.showerror("Database Error", f"Is MySQL running?\n\n{e}")
        return root.destroy()

    def show_login():
        for w in root.winfo_children():
            w.destroy()
        root.config(menu="")
        root.geometry("400x330")
        LoginFrame(root, show_app).pack(expand=True)

    def show_app(username):
        for w in root.winfo_children():
            w.destroy()
        root.geometry("1280x780")
        CarbonApp(root, username, show_login).pack(fill="both", expand=True)

    show_login()
    root.mainloop()


if __name__ == "__main__":
    main()
