import json
import os
import uuid
from datetime import datetime, timedelta
import crypto_core

DB_FILE = "vault.bin"
MAGIC_HEADER = b"PWSV0002"

class VaultManager:
    def __init__(self, master_password):
        self.master_password = master_password
        self.entries = []
        self.index = {} # Хеш-таблица по ID для быстрого доступа

    def load(self):
        if not os.path.exists(DB_FILE): return True
        with open(DB_FILE, "rb") as f:
            if f.read(len(MAGIC_HEADER)) != MAGIC_HEADER: return False
            encrypted_blob = f.read()
        
        decrypted_json = crypto_core.decrypt_data(encrypted_blob, self.master_password)
        if decrypted_json is None: return False
        
        self.entries = json.loads(decrypted_json)
        self._rebuild_index()
        return True

    def _rebuild_index(self):
        """Строит индекс по ID."""
        self.index = {e['id']: e for e in self.entries}

    def save(self):
        json_data = json.dumps(self.entries, ensure_ascii=False)
        encrypted_blob = crypto_core.encrypt_data(json_data, self.master_password)
        with open(DB_FILE, "wb") as f:
            f.write(MAGIC_HEADER)
            f.write(encrypted_blob)

    def upsert_entry(self, data, entry_id=None):
        """Создание или обновление записи (CRUD)."""
        now = datetime.now()
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")
        
        # Расчет даты истечения
        days = data.get('expiry_days', 0)
        expires_at = None
        if days > 0:
            expires_at = (now + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")

        if entry_id and str(entry_id) in self.index:
            target = self.index[str(entry_id)]
            changes = []
            
            # Проверяем, изменился ли пароль
            pw_changed = target.get('password') != data.get('password')
            
            if pw_changed:
                changes.append(f"Пароль изменен")
            if target.get('username') != data.get('username'):
                changes.append(f"Логин изменен")
            if target.get('title') != data.get('title'):
                changes.append(f"Название изменено")

            if changes:
                history_item = {
                    "date": now_str,
                    "old_password": target.get('password'),
                    "old_username": target.get('username'),
                    "info": ", ".join(changes)
                }
                if 'history' not in target: target['history'] = []
                target['history'].append(history_item)

            target.update(data)
            target['updated_at'] = now_str
            
            # Если пароль изменен ИЛИ переданы дни (из диалога), обновляем срок
            if pw_changed or 'expiry_days' in data:
                # Если выбрали "Не ограничено" (days=0), expires_at будет None
                target['expires_at'] = expires_at
        else:
            new_entry = {
                "id": str(uuid.uuid4())[:8],
                **data,
                "expires_at": expires_at,
                "history": [],
                "created_at": now_str,
                "updated_at": now_str
            }
            self.entries.append(new_entry)
        
        self._rebuild_index()
        self.save()

    def delete_entry(self, entry_id):
        self.entries = [e for e in self.entries if e['id'] != entry_id]
        self._rebuild_index()
        self.save()

    def search(self, query):
        """Полнотекстовый поиск по всем полям (Задача 4)."""
        q = query.lower()
        if not q: return self.entries
        
        def safe_match(val):
            return q in str(val).lower() if val is not None else False

        return [e for e in self.entries if 
                safe_match(e.get('title')) or 
                safe_match(e.get('username')) or 
                safe_match(e.get('url')) or 
                safe_match(e.get('category')) or 
                safe_match(e.get('notes')) or
                any(safe_match(t) for t in e.get('tags', []))]

    def export_data(self, export_path):
        """Экспорт всех записей в новый зашифрованный файл."""
        json_data = json.dumps(self.entries, ensure_ascii=False)
        encrypted_blob = crypto_core.encrypt_data(json_data, self.master_password)
        with open(export_path, "wb") as f:
            f.write(MAGIC_HEADER)
            f.write(encrypted_blob)
        return True

    def change_password(self, new_password):
        """Смена мастер-пароля и перешифровка базы."""
        self.master_password = new_password
        self.save()
        return True
