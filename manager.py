import json
import os
import uuid
from datetime import datetime
import crypto_core

DB_FILE = "vault.bin"
MAGIC_HEADER = b"PWSV0001" # Сигнатура нашего формата

class VaultManager:
    def __init__(self, master_password):
        self.master_password = master_password
        self.entries = []

    def load(self) -> bool:
        """Загрузка и дешифровка файла. Возвращает False при ошибке пароля."""
        if not os.path.exists(DB_FILE):
            return True # Файла нет, просто начнем с пустой базы

        with open(DB_FILE, "rb") as f:
            header = f.read(len(MAGIC_HEADER))
            if header != MAGIC_HEADER:
                return False
            encrypted_blob = f.read()

        decrypted_json = crypto_core.decrypt_data(encrypted_blob, self.master_password)
        if decrypted_json is None:
            return False

        self.entries = json.loads(decrypted_json)
        return True

    def save(self):
        """Сериализация и шифрование всей базы в файл."""
        json_data = json.dumps(self.entries, ensure_ascii=False)
        encrypted_blob = crypto_core.encrypt_data(json_data, self.master_password)
        
        with open(DB_FILE, "wb") as f:
            f.write(MAGIC_HEADER)
            f.write(encrypted_blob)

    def add_entry(self, title, username, password, url):
        entry = {
            "id": str(uuid.uuid4())[:8],
            "title": title,
            "username": username,
            "password": password,
            "url": url,
            "updated": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        self.entries.append(entry)
        self.save()

    def delete_entry(self, entry_id):
        self.entries = [e for e in self.entries if e['id'] != entry_id]
        self.save()