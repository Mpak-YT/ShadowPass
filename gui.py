import tkinter as tk
from tkinter import messagebox, ttk
from manager import VaultManager
import pygetwindow as gw
import threading
import time
import pyautogui
import pyperclip
import os
import random
import string
from datetime import datetime, timedelta
import keyboard as kb
import ctypes
from ctypes import windll
import settings_manager


def convert_to_tk(hk_string):
    """Превращает строку 'ctrl+alt+l' в формат Tkinter '<Control-Alt-l>'."""
    mapping = {
        "ctrl": "Control", "control": "Control",
        "alt": "Alt", "shift": "Shift",
        "win": "Meta", "cmd": "Meta", "command": "Meta"
    }
    # Очистка и разбивка
    parts = [p.strip().lower() for p in hk_string.split('+') if p.strip()]
    if not parts:
        return ""
        
    main = parts[-1]
    # Специальные клавиши
    special = {"enter": "Return", "esc": "Escape", "tab": "Tab", "space": "space"}
    main = special.get(main, main)
    if len(main) > 1:
        main = main.capitalize()

    mods = parts[:-1]
    res = ""
    for m in mods:
        res += mapping.get(m, m.capitalize()) + "-"
    
    return f"<{res}{main}>"


class SettingsDialog(tk.Toplevel):
    """Окно настроек горячих клавиш и системы."""
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Настройки")
        self.geometry("400x450")
        self.settings = settings_manager.load_settings()
        self.result = None
        
        self.transient(parent)
        self.grab_set()
        
        tk.Label(self, text="Горячие клавиши:", font=("Arial", 12, "bold")).pack(pady=10)
        
        self.entries = {}
        fields = [
            ("lock", "Блокировка (Lock)"),
            ("autofill", "Автозаполнение (Autofill)"),
            ("capture", "Захват (Capture)"),
            ("reset", "Сброс захвата (Reset)"),
            ("generate", "Генератор (Generate)")
        ]
        
        for key, label in fields:
            frame = tk.Frame(self)
            frame.pack(fill=tk.X, padx=30, pady=5)
            tk.Label(frame, text=label, width=20, anchor=tk.W).pack(side=tk.LEFT)
            ent = tk.Entry(frame, width=15)
            ent.insert(0, self.settings["hotkeys"].get(key, ""))
            ent.pack(side=tk.RIGHT, expand=True, fill=tk.X)
            self.entries[key] = ent

        tk.Label(self, text="Пример: alt+l, ctrl+shift+b", font=("Arial", 8), fg="gray").pack()
        
        # Настройки системы
        tk.Label(self, text="Система:", font=("Arial", 12, "bold")).pack(pady=(15, 10))
        
        # Выбор темы
        theme_frame = tk.Frame(self)
        theme_frame.pack(fill=tk.X, padx=30, pady=5)
        tk.Label(theme_frame, text="Тема оформления:", width=20, anchor=tk.W).pack(side=tk.LEFT)
        self.theme_var = tk.StringVar(value=self.settings.get("theme", "light"))
        theme_menu = ttk.Combobox(theme_frame, textvariable=self.theme_var, values=["light", "dark"], state="readonly", width=13)
        theme_menu.pack(side=tk.RIGHT, expand=True, fill=tk.X)

        # Таймаут блокировки
        timeout_frame = tk.Frame(self)
        timeout_frame.pack(fill=tk.X, padx=30, pady=5)
        tk.Label(timeout_frame, text="Автоблокировка (мин):", width=20, anchor=tk.W).pack(side=tk.LEFT)
        self.timeout_var = tk.StringVar(value=str(self.settings.get("lock_timeout", 5)))
        timeout_menu = ttk.Combobox(timeout_frame, textvariable=self.timeout_var, values=["1", "5", "10", "30", "60"], state="normal", width=13)
        timeout_menu.pack(side=tk.RIGHT, expand=True, fill=tk.X)

        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=20)
        
        tk.Button(btn_frame, text="Сохранить", command=self.on_save, bg="#4CAF50", fg="white", width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Отмена", command=self.destroy, width=10).pack(side=tk.LEFT, padx=5)

    def on_save(self):
        new_hotkeys = {k: v.get().strip().lower() for k, v in self.entries.items()}
        
        # Валидация хоткеев
        forbidden = ["ctrl+c", "ctrl+v", "ctrl+a", "control+c", "control+v", "control+a"]
        for key, value in new_hotkeys.items():
            if not value:
                messagebox.showwarning("Ошибка", f"Поле {key} не может быть пустым!")
                return
            
            if value in forbidden:
                messagebox.showerror("Конфликт клавиш", f"Комбинация '{value}' зарезервирована для системы (копирование/вставка).\nПожалуйста, выберите другую.")
                return

            modifiers = ["ctrl", "alt", "shift", "win", "cmd"]
            if not any(mod in value for mod in modifiers):
                messagebox.showerror("Ошибка безопасности", f"Комбинация для '{key}' должна содержать модификатор.")
                return

        # Валидация таймаута
        try:
            timeout_val = int(self.timeout_var.get())
            if timeout_val < 1: raise ValueError
        except ValueError:
            messagebox.showerror("Ошибка", "Таймаут должен быть числом больше 0!")
            return

        self.settings["hotkeys"] = new_hotkeys
        self.settings["theme"] = self.theme_var.get()
        self.settings["lock_timeout"] = timeout_val
        settings_manager.save_settings(self.settings)
        self.result = self.settings
        self.destroy()


class EntryDialog(tk.Toplevel):
    """Единое окно для создания/редактирования записи."""
    def __init__(self, parent, title_text, initial_data=None):
        super().__init__(parent)
        self.title(title_text)
        self.geometry("400x500")
        self.result = None
        
        # Делаем окно модальным (не уходит назад)
        self.transient(parent)
        self.grab_set()
        
        fields =[
            ("title", "Название*"), ("username", "Логин"), 
            ("password", "Пароль*"), ("url", "URL"),
            ("category", "Категория"), ("tags", "Теги (через запятую)")
        ]
        
        self.inputs = {}
        self.show_password_var = tk.BooleanVar(value=False) # Переменная для чекбокса

        for field, label in fields:
            frame = tk.Frame(self)
            frame.pack(fill=tk.X, padx=20, pady=5)
            tk.Label(frame, text=label).pack(side=tk.LEFT)
            
            # Если поле - пароль, скрываем его по умолчанию
            if field == "password":
                ent = tk.Entry(frame, show="*")
            else:
                ent = tk.Entry(frame)
                
            if initial_data:
                val = initial_data.get(field, "")
                ent.insert(0, ",".join(val) if field == "tags" else val)
            ent.pack(side=tk.RIGHT, expand=True, fill=tk.X)
            self.inputs[field] = ent
            
            # Добавляем чекбокс прямо под полем пароля
            if field == "password":
                cb_frame = tk.Frame(self)
                cb_frame.pack(fill=tk.X, padx=20)
                tk.Checkbutton(cb_frame, text="Показать пароль", 
                               variable=self.show_password_var, 
                               command=self.toggle_password).pack(side=tk.RIGHT)

        # Поле выбора срока годности
        expiry_frame = tk.Frame(self)
        expiry_frame.pack(fill=tk.X, padx=20, pady=5)
        tk.Label(expiry_frame, text="Срок действия:").pack(side=tk.LEFT)
        self.expiry_var = tk.StringVar(value="Не ограничено")
        expiry_options = ["Не ограничено", "30 дней", "60 дней", "90 дней", "180 дней", "365 дней"]
        self.expiry_menu = ttk.Combobox(expiry_frame, textvariable=self.expiry_var, values=expiry_options, state="readonly")
        self.expiry_menu.pack(side=tk.RIGHT, expand=True, fill=tk.X)
        
        if initial_data:
            # Пытаемся восстановить кол-во дней, если оно было сохранено
            days = initial_data.get('expiry_days', 0)
            if days > 0: 
                self.expiry_var.set(f"{days} дней")
            
            if initial_data.get('expires_at'):
                tk.Label(self, text=f"Текущий срок до: {(initial_data.get('expires_at') or '')[:10]}", fg="blue").pack(padx=20, anchor=tk.W)

        tk.Label(self, text="Заметки:").pack(padx=20, anchor=tk.W)
        self.notes_text = tk.Text(self, height=5)
        if initial_data: self.notes_text.insert("1.0", initial_data.get("notes", ""))
        self.notes_text.pack(fill=tk.BOTH, padx=20, pady=5)

        # Устанавливаем фокус на первое поле
        if "title" in self.inputs:
            self.inputs["title"].focus_set()

        # Принудительно включаем стандартные сочетания клавиш (Ctrl+C, V, A)
        self.bind_standard_shortcuts()

        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="Сохранить", command=self.on_save, bg="#4CAF50", fg="white", width=12).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Отмена", command=self.destroy, width=12).pack(side=tk.LEFT, padx=5)

    def toggle_password(self):
        char = "" if self.show_password_var.get() else "*"
        self.inputs["password"].config(show=char)

    def bind_standard_shortcuts(self):
        for widget in self.inputs.values():
            widget.bind("<Control-v>", lambda e: self.paste_text(e.widget))
            widget.bind("<Control-c>", lambda e: self.copy_text(e.widget))
            widget.bind("<Control-a>", lambda e: self.select_all(e.widget))
        
        # Для Text виджета (Заметки)
        self.notes_text.bind("<Control-v>", lambda e: self.paste_text(e.widget))
        self.notes_text.bind("<Control-c>", lambda e: self.copy_text(e.widget))
        self.notes_text.bind("<Control-a>", lambda e: self.select_all(e.widget))

    def paste_text(self, widget):
        try:
            if isinstance(widget, tk.Entry):
                widget.insert(tk.INSERT, self.clipboard_get())
            elif isinstance(widget, tk.Text):
                widget.insert(tk.INSERT, self.clipboard_get())
        except: pass
        return "break"

    def copy_text(self, widget):
        try:
            if isinstance(widget, tk.Entry):
                selection = widget.selection_get()
            elif isinstance(widget, tk.Text):
                selection = widget.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.clipboard_clear()
            self.clipboard_append(selection)
        except: pass
        return "break"

    def select_all(self, widget):
        if isinstance(widget, tk.Entry):
            widget.selection_range(0, tk.END)
            widget.icursor(tk.END)
        elif isinstance(widget, tk.Text):
            widget.tag_add(tk.SEL, "1.0", tk.END)
        return "break"

    def on_save(self):
        data = {k: v.get() for k, v in self.inputs.items()}
        data['tags'] = [t.strip() for t in (data.get('tags') or "").split(",") if t.strip()]
        data['notes'] = self.notes_text.get("1.0", tk.END).strip()
        
        # Получаем количество дней из выбора
        expiry_text = self.expiry_var.get()
        if expiry_text == "Не ограничено":
            data['expiry_days'] = 0
        else:
            data['expiry_days'] = int(expiry_text.split()[0])

        if not data['title'] or not data['password']:
            messagebox.showwarning("Ошибка", "Поля Название и Пароль обязательны!")
            return
        
        self.result = data
        self.destroy()


class ChangePasswordDialog(tk.Toplevel):
    """Диалог смены мастер-пароля."""
    def __init__(self, parent, current_password):
        super().__init__(parent)
        self.title("Смена мастер-пароля")
        self.geometry("380x350")
        self.current_password = current_password
        self.result = None
        self.show_pw = tk.BooleanVar(value=False)
        
        self.transient(parent)
        self.grab_set()
        
        tk.Label(self, text="Смена мастер-пароля", font=("Arial", 12, "bold")).pack(pady=10)
        
        self.entries = []
        
        tk.Label(self, text="Старый пароль:").pack()
        self.old_pw = tk.Entry(self, show="*", width=35)
        self.old_pw.pack(pady=2)
        self.entries.append(self.old_pw)
        
        tk.Label(self, text="Новый пароль:").pack()
        self.new_pw = tk.Entry(self, show="*", width=35)
        self.new_pw.pack(pady=2)
        self.entries.append(self.new_pw)
        
        tk.Label(self, text="Повторите новый пароль:").pack()
        self.confirm_pw = tk.Entry(self, show="*", width=35)
        self.confirm_pw.pack(pady=2)
        self.entries.append(self.confirm_pw)

        tk.Checkbutton(self, text="Показать пароли", variable=self.show_pw, command=self.toggle_visibility).pack()
        
        tk.Button(self, text="Сменить", command=self.on_save, bg="#FF9800", fg="white", width=15).pack(pady=20)

    def toggle_visibility(self):
        char = "" if self.show_pw.get() else "*"
        for e in self.entries:
            e.config(show=char)

    def on_save(self):
        old = self.old_pw.get()
        new = self.new_pw.get()
        conf = self.confirm_pw.get()
        
        if old != self.current_password:
            messagebox.showerror("Ошибка", "Старый пароль введен неверно!")
            return
        if not new or len(new) < 4:
            messagebox.showwarning("Внимание", "Новый пароль слишком короткий!")
            return
        if new != conf:
            messagebox.showerror("Ошибка", "Новые пароли не совпадают!")
            return
            
        self.result = new
        self.destroy()


class PasswordGeneratorDialog(tk.Toplevel):
    """Окно настройки и генерации паролей."""
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Генератор паролей")
        self.geometry("450x550")
        self.settings = settings_manager.load_settings()
        self.gen_settings = self.settings.get("generator", {})
        self.result = None
        
        self.transient(parent)
        self.grab_set()
        
        tk.Label(self, text="Настройка генерации", font=("Arial", 12, "bold")).pack(pady=10)
        
        # Длина
        len_frame = tk.Frame(self)
        len_frame.pack(fill=tk.X, padx=30, pady=5)
        tk.Label(len_frame, text="Длина (8-64):", width=20, anchor=tk.W).pack(side=tk.LEFT)
        self.len_var = tk.IntVar(value=self.gen_settings.get("length", 16))
        tk.Scale(len_frame, from_=8, to=64, orient=tk.HORIZONTAL, variable=self.len_var).pack(side=tk.RIGHT, expand=True, fill=tk.X)

        # Опции символов
        self.upper_var = tk.BooleanVar(value=self.gen_settings.get("use_upper", True))
        self.lower_var = tk.BooleanVar(value=self.gen_settings.get("use_lower", True))
        self.digits_var = tk.BooleanVar(value=self.gen_settings.get("use_digits", True))
        self.special_var = tk.BooleanVar(value=self.gen_settings.get("use_special", True))
        self.mnemonic_var = tk.BooleanVar(value=self.gen_settings.get("mnemonic", False))

        opts_frame = tk.LabelFrame(self, text="Параметры", padx=10, pady=10)
        opts_frame.pack(fill=tk.X, padx=30, pady=10)

        tk.Checkbutton(opts_frame, text="Буквы (A-Z)", variable=self.upper_var).pack(anchor=tk.W)
        tk.Checkbutton(opts_frame, text="Буквы (a-z)", variable=self.lower_var).pack(anchor=tk.W)
        tk.Checkbutton(opts_frame, text="Цифры (0-9)", variable=self.digits_var).pack(anchor=tk.W)
        tk.Checkbutton(opts_frame, text="Спецсимволы (!@#$)", variable=self.special_var).pack(anchor=tk.W)
        tk.Checkbutton(opts_frame, text="Мнемонический (из слов)", variable=self.mnemonic_var).pack(anchor=tk.W)

        # Результат
        tk.Label(self, text="Результат:").pack(pady=(10, 0))
        self.res_entry = tk.Entry(self, font=("Consolas", 12), justify=tk.CENTER)
        self.res_entry.pack(fill=tk.X, padx=30, pady=5)

        # Кнопки
        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=20)
        tk.Button(btn_frame, text="Сгенерировать", command=self.generate, bg="#2196F3", fg="white", width=15).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Копировать", command=self.copy_to_clip, width=12).pack(side=tk.LEFT, padx=5)
        
        save_btn = tk.Button(self, text="Сохранить настройки", command=self.save_cfg, bg="#4CAF50", fg="white")
        save_btn.pack(pady=5)

        self.generate() # Сразу генерируем один

    def generate(self):
        length = self.len_var.get()
        
        if self.mnemonic_var.get():
            password = self._gen_mnemonic(length)
        else:
            chars = ""
            if self.upper_var.get(): chars += string.ascii_uppercase
            if self.lower_var.get(): chars += string.ascii_lowercase
            if self.digits_var.get(): chars += string.digits
            if self.special_var.get(): chars += "!@#$%^&*()_+-=[]{}|;:,.<>?"
            
            if not chars:
                messagebox.showwarning("Ошибка", "Выберите хотя бы один тип символов!")
                return
            
            password = "".join(random.choice(chars) for _ in range(length))

        self.res_entry.delete(0, tk.END)
        self.res_entry.insert(0, password)

    def _gen_mnemonic(self, target_len):
        words = ["apple", "bird", "cloud", "dark", "eagle", "forest", "green", "happy", "iron", "jump", 
                 "king", "light", "moon", "night", "ocean", "paper", "queen", "river", "stone", "tree", 
                 "under", "voice", "water", "xenon", "yellow", "zebra", "active", "brave", "clear", "dream"]
        
        res_words = []
        curr_len = 0
        while curr_len < target_len:
            w = random.choice(words).capitalize()
            res_words.append(w)
            curr_len += len(w)
            if curr_len < target_len:
                res_words.append(str(random.randint(0, 9)))
                curr_len += 1
        
        return "".join(res_words)[:target_len]

    def copy_to_clip(self):
        pyperclip.copy(self.res_entry.get())
        messagebox.showinfo("Инфо", "Пароль скопирован в буфер!")

    def save_cfg(self):
        self.gen_settings = {
            "length": self.len_var.get(),
            "use_upper": self.upper_var.get(),
            "use_lower": self.lower_var.get(),
            "use_digits": self.digits_var.get(),
            "use_special": self.special_var.get(),
            "mnemonic": self.mnemonic_var.get()
        }
        self.settings["generator"] = self.gen_settings
        settings_manager.save_settings(self.settings)
        messagebox.showinfo("Успех", "Настройки генератора сохранены!")
        self.destroy()


class SelectionDialog(tk.Toplevel):
    """Окно выбора аккаунта при наличии нескольких совпадений."""
    def __init__(self, parent, matches):
        super().__init__(parent)
        self.title("Выберите аккаунт")
        self.geometry("550x350")
        self.result = None
        
        self.transient(parent)
        self.grab_set()
        
        # Центрируем окно
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'+{x}+{y}')
        
        tk.Label(self, text="Найдено несколько совпадений:", font=("Arial", 11, "bold")).pack(pady=10)
        
        self.listbox = tk.Listbox(self, font=("Consolas", 10), selectmode=tk.SINGLE, borderwidth=1, relief="solid")
        self.listbox.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)
        
        for m in matches:
            title = (m.get('title') or 'Без названия').ljust(25)
            user = m.get('username') or 'Нет логина'
            display_text = f"{title} | Логин: {user}"
            self.listbox.insert(tk.END, display_text)
        
        self.listbox.bind("<Double-1>", lambda e: self.on_select())
        self.listbox.focus_set()
        if self.listbox.size() > 0:
            self.listbox.selection_set(0)

        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="Выбрать", command=self.on_select, bg="#4CAF50", fg="white", width=12).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Отмена", command=self.destroy, width=12).pack(side=tk.LEFT, padx=5)

    def on_select(self):
        selection = self.listbox.curselection()
        if selection:
            self.result = selection[0]
            self.destroy()


class PasswordApp:

    def __init__(self, root):
        self.root = root
        self.root.title("Python Password Manager Pro")
        self.root.geometry("900x550")
        self.manager = None
        self.capture_temp = None
        self.capture_stage = 0
        self.last_matches = []
        self.tracker_started = False
        self.last_activity = time.time()
        self.auto_lock_timer = None
        
        self.settings = settings_manager.load_settings()
        self.apply_theme()
        self.reload_hotkeys()
        self.show_login()
        
        # Отслеживание активности пользователя внутри приложения
        self.root.bind_all("<Any-KeyPress>", self.reset_inactivity_timer)
        self.root.bind_all("<Any-Button>", self.reset_inactivity_timer)
        self.root.bind_all("<Motion>", self.reset_inactivity_timer)

    def reset_inactivity_timer(self, event=None):
        """Сбрасывает таймер бездействия при любом действии в окне."""
        self.last_activity = time.time()

    def start_auto_lock_checker(self):
        """Запускает циклическую проверку времени бездействия."""
        if self.auto_lock_timer:
            self.root.after_cancel(self.auto_lock_timer)
        
        def check():
            if not self.manager:
                return # Если уже заблокировано, останавливаем

            timeout_mins = self.settings.get("lock_timeout", 5)
            idle_time = time.time() - self.last_activity
            
            if idle_time > (timeout_mins * 60):
                self._tk_lock()
                self.show_toast(f"🔒 Автоблокировка ({timeout_mins} мин)")
            else:
                self.auto_lock_timer = self.root.after(10000, check) # Проверка каждые 10 сек

        self.auto_lock_timer = self.root.after(10000, check)

    def apply_theme(self):
        """Применяет выбранную тему оформления."""
        theme = self.settings.get("theme", "light")
        if theme == "dark":
            self.colors = {
                "bg": "#2B2B2B",
                "fg": "#FFFFFF",
                "entry_bg": "#3C3F41",
                "btn_bg": "#45494A",
                "btn_fg": "#FFFFFF",
                "tree_bg": "#313335",
                "tree_fg": "#AFB1B3",
                "tree_sel": "#214283"
            }
        else:
            self.colors = {
                "bg": "#F0F0F0",
                "fg": "#000000",
                "entry_bg": "#FFFFFF",
                "btn_bg": "#E1E1E1",
                "btn_fg": "#000000",
                "tree_bg": "#FFFFFF",
                "tree_fg": "#000000",
                "tree_sel": "#3399FF"
            }
        
        self.root.configure(bg=self.colors["bg"])
        
        # Настройка стилей ttk
        style = ttk.Style()
        if theme == "dark":
            style.theme_use('clam')
            style.configure("Treeview", background=self.colors["tree_bg"], 
                            foreground=self.colors["tree_fg"], fieldbackground=self.colors["tree_bg"])
            style.map("Treeview", background=[('selected', self.colors["tree_sel"])])
            style.configure("Treeview.Heading", background="#3C3F41", foreground="#FFFFFF")
            style.configure("TCombobox", fieldbackground=self.colors["entry_bg"], background=self.colors["btn_bg"])
        else:
            style.theme_use('vista' if os.name == 'nt' else 'default')
            style.configure("Treeview", background="#FFFFFF", foreground="#000000", fieldbackground="#FFFFFF")
            style.map("Treeview", background=[('selected', "#3399FF")])

        self.update_widget_theme(self.root)

    def update_widget_theme(self, parent):
        """Рекурсивно обновляет тему виджетов."""
        # Сначала красим сам родительский элемент (окно или фрейм)
        try:
            if isinstance(parent, (tk.Tk, tk.Toplevel, tk.Frame, tk.LabelFrame)):
                parent.configure(bg=self.colors["bg"])
        except:
            pass

        for child in parent.winfo_children():
            try:
                if isinstance(child, (tk.Frame, tk.LabelFrame)):
                    child.configure(bg=self.colors["bg"])
                    self.update_widget_theme(child)
                elif isinstance(child, tk.Toplevel):
                    child.configure(bg=self.colors["bg"])
                    self.update_widget_theme(child)
                elif isinstance(child, tk.Label):
                    child.configure(bg=self.colors["bg"], fg=self.colors["fg"])
                elif isinstance(child, tk.Button):
                    # Не меняем кнопки с явно заданным ярким фоном
                    curr_bg = str(child.cget("bg")).upper()
                    if curr_bg not in ["#4CAF50", "#FF5252", "#FF9800", "#FFF9C4", "#FFEBEE", "GREEN", "RED"]:
                        child.configure(bg=self.colors["btn_bg"], fg=self.colors["btn_fg"])
                elif isinstance(child, tk.Entry):
                    child.configure(bg=self.colors["entry_bg"], fg=self.colors["fg"], insertbackground=self.colors["fg"])
                elif isinstance(child, tk.Text):
                    child.configure(bg=self.colors["entry_bg"], fg=self.colors["fg"], insertbackground=self.colors["fg"])
                elif isinstance(child, tk.Checkbutton):
                    child.configure(bg=self.colors["bg"], fg=self.colors["fg"], selectcolor=self.colors["entry_bg"], activebackground=self.colors["bg"], activeforeground=self.colors["fg"])
                elif isinstance(child, tk.Listbox):
                    child.configure(bg=self.colors["entry_bg"], fg=self.colors["fg"], selectbackground=self.colors["tree_sel"])
            except:
                pass

    def reload_hotkeys(self):
        """Обновляет локальные и глобальные хоткеи."""
        self.settings = settings_manager.load_settings()
        h = self.settings["hotkeys"]
        
        # Local TK hotkeys
        def _local_wrap(fn):
            return lambda e: fn() if (self.manager and not self.root.grab_current()) else None

        for func, hk in [("lock", self._tk_lock), ("autofill", self._tk_autofill), 
                         ("capture", self._tk_capture), ("reset", self._tk_reset),
                         ("generate", self._tk_generate)]:
            try:
                tk_seq = convert_to_tk(h[func])
                self.root.bind_all(tk_seq, _local_wrap(hk))
            except Exception: pass
        
        # Перезапуск глобальных хоткеев
        start_hotkey_listener(self)

    def autofill_active_window(self):
        """Автозаполнение: выбор аккаунта и автоматический ввод данных."""
        # 1. СРАЗУ запоминаем целевое окно, пока оно активно
        target_win = gw.getActiveWindow()
        if not target_win or "Python Password Manager Pro" in (target_win.title or ""):
            # Если активное окно - наш менеджер, пытаемся найти последнее "настоящее" окно
            # (но обычно хоткей нажимается в браузере, так что target_win будет верным)
            pass

        time.sleep(0.2) 
        
        # 2. Ищем подходящие аккаунты по заголовку целевого окна
        matches = []
        if target_win and target_win.title:
            title_lower = target_win.title.lower()
            for entry in self.manager.index.values():
                e_title = (entry.get('title') or "").lower()
                e_url = (entry.get('url') or "").lower()
                if (e_title and e_title in title_lower) or (e_url and e_url in title_lower) or \
                   (e_title and title_lower in e_title):
                    matches.append(entry)

        if not matches:
            self.root.after(0, lambda: self.show_toast("❌ Совпадение не найдено."))
            return

        matched_entry = None
        if len(matches) > 1:
            # 3. Если совпадений много — показываем выбор
            self.root.deiconify() 
            self.root.attributes("-topmost", True)
            dialog = SelectionDialog(self.root, matches)
            self.update_widget_theme(dialog)
            self.root.wait_window(dialog)
            self.root.attributes("-topmost", False)
            
            if dialog.result is not None:
                matched_entry = matches[dialog.result]
            else:
                return # Отмена пользователем
        else:
            matched_entry = matches[0]

        if matched_entry:
            # 4. ФИНАЛЬНЫЙ ЭТАП: Возвращаем фокус и вводим данные
            self.root.iconify() # Сворачиваем менеджер, чтобы не мешал
            time.sleep(0.4)
            
            if target_win:
                try:
                    target_win.activate() # Принудительно возвращаем фокус в браузер
                except:
                    pass
            
            time.sleep(0.8) # Ждем, пока ОС гарантированно переключит фокус
            
            self.root.after(0, lambda: self.show_toast(f"🚀 Ввод данных: {matched_entry['title']}"))
            
            # Ввод ЛОГИНА с очисткой поля
            pyautogui.hotkey('ctrl', 'a')
            pyautogui.press('backspace')
            time.sleep(0.1)
            self._type_securely(matched_entry.get('username', ''))
            
            pyautogui.press('tab')
            time.sleep(0.5) 
            
            # Ввод ПАРОЛЯ с очисткой поля
            pyautogui.hotkey('ctrl', 'a')
            pyautogui.press('backspace')
            time.sleep(0.1)
            self._type_securely(matched_entry.get('password', ''))
            
            pyautogui.press('enter')
            

    def open_settings(self):
        dialog = SettingsDialog(self.root)
        self.update_widget_theme(dialog)
        self.root.wait_window(dialog)
        if dialog.result:
            self.settings = settings_manager.load_settings()
            self.apply_theme()
            self.reload_hotkeys()
            messagebox.showinfo("Успех", "Настройки обновлены!")

    def open_generator(self):
        dialog = PasswordGeneratorDialog(self.root)
        self.update_widget_theme(dialog)
        self.root.wait_window(dialog)

    def change_master_password(self):
        """Вызывает диалог смены пароля и обновляет его в менеджере."""
        if not self.manager: return
        dialog = ChangePasswordDialog(self.root, self.manager.master_password)
        self.update_widget_theme(dialog)
        self.root.wait_window(dialog)
        if dialog.result:
            if self.manager.change_password(dialog.result):
                messagebox.showinfo("Успех", "Мастер-пароль успешно изменен!")

    def _secure_paste(self, text: str):
        """Усиленная версия: минимум времени + двойная жёсткая очистка после каждой вставки"""
        if not text:
            return

        old_clip = self._get_clipboard_text()

        # Вставляем
        pyperclip.copy(text)
        time.sleep(0.18)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(0.40)        # даём время на вставку

        # === АГРЕССИВНАЯ ОЧИСТКА ===
        for _ in range(3):                     # три прохода очистки
            self._clear_clipboard_hard()
            time.sleep(0.06)

        # Восстанавливаем оригинальный текст пользователя
        if old_clip and old_clip.strip():
            self.root.after(280, lambda: pyperclip.copy(old_clip))

    def _restore_clipboard(self):
        """Финальное восстановление + очистка"""
        if hasattr(self, '_clipboard_backup') and self._clipboard_backup is not None:
            original = self._clipboard_backup
            self._clipboard_backup = None
            self._clear_clipboard_hard()
            if original and original.strip():
                pyperclip.copy(original)

    def show_login(self):
        self.clear_screen()
        frame = tk.Frame(self.root)
        frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        tk.Label(frame, text="МАСТЕР-ПАРОЛЬ", font=("Arial", 14, "bold")).pack()
        self.pw_entry = tk.Entry(frame, show="*", width=30, font=("Arial", 12))
        self.pw_entry.pack(pady=10)
        self.pw_entry.focus_set()
        self.pw_entry.bind('<Return>', lambda e: self.login())
        tk.Button(frame, text="ВОЙТИ", command=self.login, bg="#4CAF50", fg="white", width=20).pack()
        self.apply_theme()

    def login(self):
        pw = self.pw_entry.get()
        temp_manager = VaultManager(pw)
        if temp_manager.load():
            self.manager = temp_manager
            self.reload_hotkeys() # Перезагружаем хоткеи ПРИ ВХОДЕ
            self.show_main()
            
            # Проверка на истекшие пароли
            expired_count = 0
            now = datetime.now()
            for e in self.manager.entries:
                if e.get('expires_at'):
                    exp = datetime.strptime(e['expires_at'], "%Y-%m-%d %H:%M:%S")
                    if now > exp:
                        expired_count += 1
            
            if expired_count > 0:
                messagebox.showwarning("Внимание", 
                    f"У вас есть истекшие пароли ({expired_count}).\n"
                    "Рекомендуем их обновить для безопасности.")
        else:
            self.manager = None
            messagebox.showerror("Ошибка", "Неверный пароль")

    def show_main(self):
        self.clear_screen()
        # Разворачиваем окно на весь экран
        try:
            self.root.state('zoomed') 
        except:
            # Резервный вариант, если zoomed не поддерживается (например, на некоторых версиях Linux)
            w, h = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
            self.root.geometry(f"{w}x{h}+0+0")

        self.start_window_tracker()
        self.init_capture_state()
        self.create_weekly_backup() # Запускаем автоматический бэкап
        self.start_auto_lock_checker() # Запускаем таймер бездействия
        
        # Панель поиска и кнопок
        top_bar = tk.Frame(self.root, pady=10)
        top_bar.pack(side=tk.TOP, fill=tk.X)
        
        tk.Button(top_bar, text="➕ Новая запись", command=self.add_entry).pack(side=tk.LEFT, padx=10)
        tk.Button(top_bar, text="💾 Экспорт", command=self.export_vault).pack(side=tk.LEFT, padx=5)
        tk.Button(top_bar, text="🎲 Генератор", command=self.open_generator, bg="#E3F2FD").pack(side=tk.LEFT, padx=5)
        tk.Button(top_bar, text="⚙️ Настройки", command=self.open_settings).pack(side=tk.LEFT, padx=5)
        tk.Button(top_bar, text="🔑 Мастер-Ключ", command=self.change_master_password).pack(side=tk.LEFT, padx=5)
        tk.Button(top_bar, text="⏳ Истекающие", command=self.show_expiring_soon, bg="#FFF9C4").pack(side=tk.LEFT, padx=5)
        tk.Button(top_bar, text="⚠️ Повторы", command=self.show_reused_passwords, bg="#E8F5E9").pack(side=tk.LEFT, padx=5)
        
        tk.Label(top_bar, text="Поиск:").pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.refresh_table())
        tk.Entry(top_bar, textvariable=self.search_var, width=30).pack(side=tk.LEFT, padx=5)

        tk.Label(top_bar, text="Сортировка:").pack(side=tk.LEFT, padx=5)
        self.sort_var = tk.StringVar(value="По названию")
        sort_options = ["По названию", "Сначала новые", "Сначала старые", "По тегам"]
        self.sort_menu = ttk.Combobox(top_bar, textvariable=self.sort_var, values=sort_options, state="readonly", width=15)
        self.sort_menu.pack(side=tk.LEFT, padx=5)
        self.sort_menu.bind("<<ComboboxSelected>>", lambda e: self.refresh_table())

        tk.Button(top_bar, text="История", command=self.show_history).pack(side=tk.RIGHT, padx=10)
        tk.Button(top_bar, text="Удалить", command=self.delete_entry, bg="#FF5252", fg="white").pack(side=tk.RIGHT)

        # Таблица
        cols = ("ID", "Название", "Категория", "Логин", "Пароль", "Создан", "Истекает", "Статус", "URL", "Теги")
        self.tree = ttk.Treeview(self.root, columns=cols, show='headings')
        for c in cols: 
            self.tree.heading(c, text=c)
            self.tree.column(c, width=100)
        
        # Настройка цветов для тегов
        self.tree.tag_configure("expired", background="#FFEBEE", foreground="#C62828")
        self.tree.tag_configure("reused", background="#E8F5E9", foreground="#2E7D32")
        
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.tree.bind("<Double-1>", self.edit_entry)
        
        self.refresh_table()
        self.apply_theme()

    def create_weekly_backup(self):
        """Создает автоматический зашифрованный бекап базы раз в неделю."""
        try:
            backup_dir = "backups"
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
            
            backups =[f for f in os.listdir(backup_dir) if f.endswith('.bin')]
            needs_backup = True
            now = datetime.now()
            
            if backups:
                latest = max(backups, key=lambda b: os.path.getmtime(os.path.join(backup_dir, b)))
                mtime = datetime.fromtimestamp(os.path.getmtime(os.path.join(backup_dir, latest)))
                if now - mtime < timedelta(days=7):
                    needs_backup = False
                    
            if needs_backup:
                backup_name = f"backup_{now.strftime('%Y-%m-%d_%H-%M-%S')}.bin"
                backup_path = os.path.join(backup_dir, backup_name)
                if self.manager.export_data(backup_path):
                    print(f"Weekly backup created: {backup_path}")
        except Exception as e:
            print(f"Backup failed: {e}")

    def refresh_table(self):
        for i in self.tree.get_children(): 
            self.tree.delete(i)
        
        query = self.search_var.get()
        now = datetime.now()
        
        # Получаем отфильтрованные записи
        entries = self.manager.search(query)
        
        # Подсчет повторов паролей для выделения цветом
        password_counts = {}
        for e in self.manager.entries:
            pw = e.get('password')
            if pw:
                password_counts[pw] = password_counts.get(pw, 0) + 1

        # Логика сортировки
        sort_type = self.sort_var.get()
        if sort_type == "По названию":
            entries.sort(key=lambda x: (x.get('title') or "").lower())
        elif sort_type == "Сначала новые":
            entries.sort(key=lambda x: (x.get('created_at') or ""), reverse=True)
        elif sort_type == "Сначала старые":
            entries.sort(key=lambda x: (x.get('created_at') or ""))
        elif sort_type == "По тегам":
            entries.sort(key=lambda x: ",".join(x.get('tags', [])).lower())

        for e in entries:
            # Пароль показываем звёздочками
            hidden_password = "••••••••" if e.get('password') else ""
            
            # Логика статуса
            status = "OK"
            tags = []
            expires_at_raw = e.get('expires_at')
            expires_at_str = expires_at_raw or "-"
            
            if expires_at_raw:
                try:
                    exp = datetime.strptime(expires_at_raw, "%Y-%m-%d %H:%M:%S")
                    if now > exp:
                        status = "⚠️ ИСТЕК"
                        tags.append("expired")
                    else:
                        days_left = (exp - now).days
                        status = f"{days_left} дн."
                except (ValueError, TypeError):
                    status = "Error"
            
            # Проверка на повторное использование пароля
            pw = e.get('password')
            if pw and password_counts.get(pw, 0) > 1:
                tags.append("reused")

            self.tree.insert("", tk.END, values=(
                e.get('id', ''), 
                e.get('title', ''), 
                e.get('category', ''), 
                e.get('username', ''), 
                hidden_password,
                (e.get('created_at') or "-")[:10], # Показываем только дату
                expires_at_str[:10] if expires_at_str != "-" else "-",
                status,
                e.get('url', '')
            ), tags=tags)

    def show_expiring_soon(self):
        """Окно со списком паролей, которые скоро истекают."""
        if not self.manager: return
        
        now = datetime.now()
        expiring_entries = []
        
        for e in self.manager.entries:
            if e.get('expires_at'):
                try:
                    exp_date = datetime.strptime(e['expires_at'], "%Y-%m-%d %H:%M:%S")
                    days_left = (exp_date - now).days
                    expiring_entries.append((days_left, e))
                except: continue
        
        # Сортировка: сначала те, у кого меньше всего дней
        expiring_entries.sort(key=lambda x: x[0])
        
        exp_win = tk.Toplevel(self.root)
        exp_win.title("Пароли с ограниченным сроком")
        exp_win.geometry("600x400")
        exp_win.grab_set()
        
        tk.Label(exp_win, text="Пароли, требующие внимания", font=("Arial", 12, "bold")).pack(pady=10)
        
        cols = ("Название", "Логин", "Осталось дней", "Дата истечения")
        tree = ttk.Treeview(exp_win, columns=cols, show='headings')
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=120)
        
        tree.tag_configure("critical", background="#FFEBEE", foreground="#C62828")
        
        for days, e in expiring_entries:
            tag = "critical" if days < 7 else ""
            tree.insert("", tk.END, values=(
                e['title'],
                e['username'],
                f"{days} дн." if days >= 0 else "ИСТЕК",
                e['expires_at'][:10]
            ), tags=(tag,))
        
        tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        tk.Button(exp_win, text="Закрыть", command=exp_win.destroy, width=15).pack(pady=10)
        self.update_widget_theme(exp_win)

    def show_reused_passwords(self):
        """Окно со списком всех повторяющихся паролей."""
        if not self.manager: return
        
        # Группируем записи по паролям
        pw_groups = {}
        for e in self.manager.entries:
            pw = e.get('password')
            if pw:
                if pw not in pw_groups:
                    pw_groups[pw] = []
                pw_groups[pw].append(e)
        
        # Оставляем только те, где больше одной записи
        reused_groups = {pw: entries for pw, entries in pw_groups.items() if len(entries) > 1}
        
        if not reused_groups:
            messagebox.showinfo("Инфо", "Повторяющихся паролей не найдено. Отличная работа!")
            return

        reused_win = tk.Toplevel(self.root)
        reused_win.title("Повторяющиеся пароли")
        reused_win.geometry("700x500")
        reused_win.grab_set()
        
        tk.Label(reused_win, text="Найдены дубликаты паролей", font=("Arial", 12, "bold")).pack(pady=10)
        
        cols = ("Пароль", "Кол-во", "Где используется (Названия)")
        tree = ttk.Treeview(reused_win, columns=cols, show='headings')
        for c in cols:
            tree.heading(c, text=c)
        
        tree.column("Пароль", width=150)
        tree.column("Кол-во", width=80, anchor=tk.CENTER)
        tree.column("Где используется (Названия)", width=400)
        
        for pw, entries in reused_groups.items():
            titles = ", ".join([e['title'] for e in entries])
            # Показываем пароль частично для безопасности
            display_pw = pw[:2] + "*" * (len(pw)-4) + pw[-2:] if len(pw) > 4 else "****"
            tree.insert("", tk.END, values=(display_pw, len(entries), titles))
            
        tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        tk.Button(reused_win, text="Закрыть", command=reused_win.destroy, width=15).pack(pady=10)
        self.update_widget_theme(reused_win)

    def add_entry(self):
        dialog = EntryDialog(self.root, "Новая запись")
        self.update_widget_theme(dialog)
        self.root.wait_window(dialog)
        if dialog.result:
            self.manager.upsert_entry(dialog.result)
            self.refresh_table()

    def export_vault(self):
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            defaultextension=".bin",
            filetypes=[("Binary Vault", "*.bin")],
            title="Экспорт базы данных"
        )
        if path:
            if self.manager.export_data(path):
                messagebox.showinfo("Успех", f"База данных успешно экспортирована в {path}")

    def edit_entry(self, event):
        item = self.tree.selection()[0]
        entry_id = self.tree.item(item)['values'][0]
        entry_data = self.manager.index[str(entry_id)]
        
        dialog = EntryDialog(self.root, "Редактирование", entry_data)
        self.update_widget_theme(dialog)
        self.root.wait_window(dialog)
        if dialog.result:
            self.manager.upsert_entry(dialog.result, entry_id)
            self.refresh_table()

    def show_history(self):
        selected = self.tree.selection()
        if not selected: 
            messagebox.showinfo("Инфо", "Выберите запись для просмотра истории")
            return
            
        entry_id = self.tree.item(selected[0])['values'][0]
        entry = self.manager.index[str(entry_id)]
        
        hist_win = tk.Toplevel(self.root)
        hist_win.title(f"История изменений: {entry['title']}")
        hist_win.geometry("450x300")
        hist_win.grab_set() 
        
        txt = tk.Text(hist_win, width=55, height=15, font=("Consolas", 10))
        txt.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        history_list = entry.get('history',[])
        
        if not history_list:
            txt.insert(tk.END, "История изменений пуста.\n")
            txt.insert(tk.END, "История пополняется только при изменении пароля или логина.")
        else:
            for h in reversed(history_list): 
                txt.insert(tk.END, f"Дата: {h.get('date', '-')}\n")
                txt.insert(tk.END, f"Событие: {h.get('info', 'Изменение данных')}\n")
                txt.insert(tk.END, f"Старый пароль: {h.get('old_password', '-')}\n")
                txt.insert(tk.END, f"Старый логин: {h.get('old_username', '-')}\n")
                txt.insert(tk.END, "-"*40 + "\n")
        
        txt.config(state=tk.DISABLED) 
        tk.Button(hist_win, text="Закрыть", command=hist_win.destroy).pack(pady=5)
        self.update_widget_theme(hist_win)

    def delete_entry(self):
        selected = self.tree.selection()
        if not selected: return
        if messagebox.askyesno("Удаление", "Удалить запись навсегда?"):
            entry_id = self.tree.item(selected[0])['values'][0]
            self.manager.delete_entry(str(entry_id))
            self.refresh_table()

    def is_browser_window(self, title):
        """Определяет, является ли активное окно браузером по его заголовку."""
        if not title: return False
        title_lower = title.lower()
        # Список популярных браузеров. Если в названии окна есть эти слова - это браузер
        browsers =['chrome', 'firefox', 'edge', 'opera', 'yandex', 'brave', 'browser', 'safari']
        return any(b in title_lower for b in browsers)
    
    def clear_screen(self):
        for w in self.root.winfo_children(): w.destroy()

    def start_window_tracker(self):
        def track():
            last_window = None
            while True:
                try:
                    active_window = gw.getActiveWindow()
                    if active_window and active_window.title:
                        title = active_window.title
                        if "Python Password Manager Pro" in title:
                            time.sleep(1)
                            continue
                            
                        if title != last_window:
                            last_window = title
                            self.match_window_to_vault(title)
                except Exception:
                    pass
                time.sleep(2)
        
        threading.Thread(target=track, daemon=True).start()

    def match_window_to_vault(self, window_title):
        if not self.manager: return
        
        self.last_matches =[]
        window_title_lower = (window_title or "").lower()
        
        for entry in self.manager.index.values():
            e_title = (entry.get('title') or "").lower()
            e_url = (entry.get('url') or "").lower()
            
            if (e_title and e_title in window_title_lower) or \
               (e_url and e_url in window_title_lower) or \
               (e_title and window_title_lower in e_title):
                self.last_matches.append(entry)

    def _tk_lock(self):
        if not self.manager:
            return
        try:
            self.manager = None # ОЧИЩАЕМ СЕССИЮ
            self.init_capture_state()
            self.clear_screen()
            self.show_login()
        except Exception as e:
            pass

    def _tk_autofill(self):
        try:
            self.autofill_active_window()
        except Exception as e:
            pass

    def _tk_capture(self):
        try:
            self.capture_selection_and_advance()
        except Exception as e:
            messagebox.showerror("Ошибка захвата", f"Произошла ошибка: {e}")

    def _tk_reset(self):
        try:
            self.reset_capture()
        except Exception as e:
            pass

    def _tk_generate(self):
        """Хоткей: генерирует пароль по настройкам и вводит его в активное поле."""
        target_win = gw.getActiveWindow()
        if not target_win: return

        # Загружаем настройки генератора
        gs = self.settings.get("generator", {})
        length = gs.get("length", 16)
        
        # Логика генерации (дублируем из диалога для независимости)
        if gs.get("mnemonic"):
            # Короткая версия для хоткея
            words = ["apple", "bird", "cloud", "dark", "eagle", "forest", "green", "happy", "iron", "jump", 
                     "king", "light", "moon", "night", "ocean", "paper", "queen", "river", "stone", "tree"]
            res = []
            curr = 0
            while curr < length:
                w = random.choice(words).capitalize()
                res.append(w)
                curr += len(w)
                if curr < length:
                    res.append(str(random.randint(0, 9)))
                    curr += 1
            password = "".join(res)[:length]
        else:
            chars = ""
            if gs.get("use_upper"): chars += string.ascii_uppercase
            if gs.get("use_lower"): chars += string.ascii_lowercase
            if gs.get("use_digits"): chars += string.digits
            if gs.get("use_special"): chars += "!@#$%^&*()_+-="
            if not chars: chars = string.ascii_lowercase + string.digits
            password = "".join(random.choice(chars) for _ in range(length))

        # Ввод
        self.root.after(0, lambda: self.show_toast(f"🔑 Генерация и ввод..."))
        time.sleep(0.5)
        self._type_securely(password)

    def init_capture_state(self):
        self.capture_temp = {"title": "", "username": "", "password": "", "url": "", "category": "", "tags":[]}
        self.capture_stage = 0

    def reset_capture(self):
        self.init_capture_state()
        self.root.after(0, lambda: self.show_toast("Промежуточные данные удалены"))

    def _get_clipboard_text(self):
        try:
            return pyperclip.paste()
        except Exception:
            try:
                return self.root.clipboard_get()
            except Exception:
                return ""
            
    def _get_current_layout(self):
        """Возвращает текущую раскладку (например, 1033 = English US, 1049 = Russian)"""
        try:
            user32 = windll.user32
            hwnd = user32.GetForegroundWindow()
            thread_id = user32.GetWindowThreadProcessId(hwnd, 0)
            layout = user32.GetKeyboardLayout(thread_id)
            return layout & 0xFFFF  # низкие 16 бит = язык
        except:
            return 1033  # по умолчанию English US

    def _type_securely(self, text: str):
        """Посимвольный ввод без буфера обмена + автоматическое переключение раскладки"""
        if not text:
            return

        current_layout = self._get_current_layout()
        english_layout = 1033   # English (US)
        russian_layout = 1049   # Russian

        for char in text:
            # Определяем, какая раскладка нужна для текущего символа
            if char.isascii() and char.isalpha():           # Латиница (A-Z, a-z)
                needed_layout = english_layout
            elif '\u0400' <= char <= '\u04FF':              # Кириллица
                needed_layout = russian_layout
            else:
                needed_layout = current_layout              # цифры, символы и т.д. — не меняем

            # Переключаем раскладку, если нужно
            if needed_layout != current_layout:
                try:
                    pyautogui.hotkey('alt', 'shift')
                    time.sleep(0.22)                        # задержка на переключение
                    current_layout = needed_layout
                except:
                    pass

            # Вводим символ
            pyautogui.write(char, interval=0.018)
            time.sleep(0.010)                               # небольшая пауза между символами

        time.sleep(0.15)
            
    def _clear_clipboard_hard(self):
        """Жёсткая очистка буфера через Windows API (лучше всего убирает из истории)"""
        try:
            if windll.user32.OpenClipboard(None):
                windll.user32.EmptyClipboard()
                windll.user32.CloseClipboard()
            pyperclip.copy('')  # дополнительная страховка
        except Exception:
            pass  # если что-то пойдёт не так — не падаем

    def show_toast(self, message):
        """Всплывающее уведомление, которое не блокирует фокус ввода."""
        try:
            toast = tk.Toplevel(self.root)
            toast.overrideredirect(True)
            toast.attributes("-topmost", True)
            
            x = self.root.winfo_pointerx() + 20
            y = self.root.winfo_pointery() + 20
            toast.geometry(f"+{x}+{y}")
            
            tk.Label(toast, text=message, bg="#333333", fg="white", padx=10, pady=5, font=("Arial", 10)).pack()
            self.root.after(2500, toast.destroy)
        except Exception:
            pass

    def capture_selection_and_advance(self):
        """Запуск процесса захвата в фоновом потоке, чтобы не блокировать интерфейс."""
        threading.Thread(target=self._capture_thread_logic, daemon=True).start()

    def _capture_thread_logic(self):
        """Фоновая логика захвата: ожидание, копирование и вызов UI-элементов."""
        target_window = gw.getActiveWindow()
        if not target_window: return
            
        target_title = target_window.title
        if "Python Password Manager Pro" in target_title and self.capture_stage == 0:
            return

        is_browser = self.is_browser_window(target_title)
        self._clipboard_backup = self._get_clipboard_text()

        try:
            # 1. Даем пользователю время отпустить клавиши
            time.sleep(0.5)
            
            # 2. Пытаемся скопировать выделенное
            captured_text = ""
            pyperclip.copy('') 
            
            pyautogui.keyDown('ctrl')
            pyautogui.press('c')
            time.sleep(0.1)
            pyautogui.keyUp('ctrl')
            
            for _ in range(10):
                time.sleep(0.1)
                captured_text = pyperclip.paste().strip()
                if captured_text: break
            
            # 3. Обработка результата
            if not captured_text:
                self.root.after(0, lambda: self._handle_manual_capture(target_title, is_browser))
            else:
                self.root.after(0, lambda: self._process_captured_text(captured_text, target_title, is_browser))

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Ошибка", f"Сбой захвата: {e}"))
        finally:
            # ГАРАНТИРОВАННО отпускаем клавиши и возвращаем буфер
            try:
                pyautogui.keyUp('ctrl')
                pyautogui.keyUp('alt')
                pyautogui.keyUp('shift')
            except: pass
            time.sleep(0.2)
            self._restore_clipboard()

    def _handle_manual_capture(self, target_title, is_browser):
        """Вызов окна ручного ввода."""
        self.root.deiconify() 
        self.root.attributes("-topmost", True)
        self.root.focus_force()
        
        prompts = {0: "Введите ЛОГИН:", 1: "Введите ПАРОЛЬ:", 2: "Введите URL:"}
        msg = prompts.get(self.capture_stage, "Введите данные:")
        
        from tkinter import simpledialog
        text = simpledialog.askstring("Захват", msg, parent=self.root)
        self.root.attributes("-topmost", False)

        if text is None:
            self.show_toast("Захват отменен")
            self.init_capture_state()
        else:
            self._process_captured_text(text, target_title, is_browser)

    def _process_captured_text(self, text, target_title, is_browser):
        """Распределение полученных данных по стадиям."""
        if self.capture_stage == 0:
            self.capture_temp['username'] = text
            self.capture_stage = 1
            self.show_toast(f"✅ Логин сохранен\nТеперь выделите ПАРОЛЬ")
        elif self.capture_stage == 1:
            self.capture_temp['password'] = text
            if is_browser:
                self.capture_stage = 2
                self.show_toast("✅ Пароль сохранен\nТеперь выделите URL")
            else:
                self.capture_temp['title'] = target_title
                self.capture_temp['url'] = "Приложение"
                self._finalize_and_save_capture()
        elif self.capture_stage == 2:
            self.capture_temp['url'] = text
            self.capture_temp['title'] = target_title
            self._finalize_and_save_capture()

    def _finalize_and_save_capture(self):
        """Открывает диалог редактирования перед финальным сохранением захваченных данных."""
        try:
            title = self.capture_temp.get('title') or "Новая запись"
            data = {
                "title": title,
                "username": self.capture_temp['username'],
                "password": self.capture_temp['password'],
                "url": self.capture_temp['url'],
                "category": "Автозахват",
                "tags": ["auto"]
            }

            self.root.deiconify()
            self.root.attributes("-topmost", True)
            self.root.focus_force()
            
            dialog = EntryDialog(self.root, "Подтверждение захвата", data)
            self.update_widget_theme(dialog)
            self.root.wait_window(dialog)
            self.root.attributes("-topmost", False)

            if dialog.result:
                self.manager.upsert_entry(dialog.result)
                self.refresh_table()
                self.show_toast(f"💾 СОХРАНЕНО: {dialog.result['title']}")
            else:
                self.show_toast("Сохранение отменено")

        except Exception as e:
            self.show_toast(f"❌ Ошибка: {e}")
        finally:
            self.init_capture_state()

def on_hotkey_lock(app_instance):
    if not app_instance.manager: return
    app_instance.root.after(0, app_instance._tk_lock)

def start_hotkey_listener(app_instance):
    """Регистрирует глобальные хоткеи с защитой от сбоев."""
    try:
        kb.unhook_all()
        h = app_instance.settings["hotkeys"]
        
        # Обертка для безопасного вызова из другого потока
        def safe_call(fn):
            if app_instance.manager:
                app_instance.root.after(0, fn)

        kb.add_hotkey(h["lock"], lambda: on_hotkey_lock(app_instance))
        kb.add_hotkey(h["autofill"], lambda: safe_call(app_instance.autofill_active_window))
        kb.add_hotkey(h["capture"], lambda: safe_call(app_instance.capture_selection_and_advance))
        kb.add_hotkey(h["reset"], lambda: safe_call(app_instance.reset_capture))
        kb.add_hotkey(h["generate"], lambda: safe_call(app_instance._tk_generate))
        
        print(f"Горячие клавиши активны: {h}")
    except Exception as e:
        print(f"Ошибка Hotkeys: {e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = PasswordApp(root)
    
    # Запуск прослушивателя глобальных хоткеев
    start_hotkey_listener(app)
    
    root.mainloop()