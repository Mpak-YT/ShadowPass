import tkinter as tk
from tkinter import messagebox, ttk, simpledialog
from manager import VaultManager

class PasswordApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Python Safe Pass")
        self.root.geometry("700x450")
        self.manager = None
        self.show_login()

    def clear_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def show_login(self):
        self.clear_screen()
        frame = tk.Frame(self.root)
        frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        tk.Label(frame, text="Введите Мастер-Пароль", font=("Arial", 12)).pack()
        self.pw_entry = tk.Entry(frame, show="*", width=30)
        self.pw_entry.pack(pady=10)
        self.pw_entry.bind('<Return>', lambda e: self.login())
        
        tk.Button(frame, text="Войти / Создать базу", command=self.login, width=20).pack()

    def login(self):
        password = self.pw_entry.get()
        if not password: return
        
        self.manager = VaultManager(password)
        if self.manager.load():
            self.show_main()
        else:
            messagebox.showerror("Ошибка", "Неверный пароль или файл поврежден")

    def show_main(self):
        self.clear_screen()
        
        # Панель управления
        toolbar = tk.Frame(self.root)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        tk.Button(toolbar, text="+ Добавить", command=self.add_dialog).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="Удалить", command=self.delete_selected).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="Сменить Мастер-Пароль", command=self.change_master).pack(side=tk.RIGHT, padx=2)

        # Таблица
        cols = ("ID", "Название", "Логин", "Пароль", "URL")
        self.tree = ttk.Treeview(self.root, columns=cols, show='headings')
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100)
        
        self.tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.refresh_table()

    def refresh_table(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        for e in self.manager.entries:
            self.tree.insert("", tk.END, values=(e['id'], e['title'], e['username'], e['password'], e['url']))

    def add_dialog(self):
        title = simpledialog.askstring("Ввод", "Название (например, Google):")
        if not title: return
        user = simpledialog.askstring("Ввод", "Логин:")
        pw = simpledialog.askstring("Ввод", "Пароль:")
        url = simpledialog.askstring("Ввод", "URL:")
        
        self.manager.add_entry(title, user or "", pw or "", url or "")
        self.refresh_table()

    def delete_selected(self):
        selected = self.tree.selection()
        if not selected: return
        item_id = self.tree.item(selected[0])['values'][0]
        if messagebox.askyesno("Удаление", "Удалить выбранную запись?"):
            self.manager.delete_entry(str(item_id))
            self.refresh_table()

    def change_master(self):
        new_pw = simpledialog.askstring("Пароль", "Введите новый мастер-пароль:", show='*')
        if new_pw:
            self.manager.master_password = new_pw
            self.manager.save()
            messagebox.showinfo("Успех", "База перешифрована новым паролем")

if __name__ == "__main__":
    root = tk.Tk()
    app = PasswordApp(root)
    root.mainloop()