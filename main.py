import os
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Hash import SHA512
from Crypto.Random import get_random_bytes

# Пока что хардкодим мастер-пароль
MASTER_PASSWORD = "my-super-secret-master-password"

def derive_key(password: str, salt: bytes) -> bytes:
    """
    Функция генерации ключа из пароля и соли (KDF).
    Генерирует 32-байтный ключ для AES-256.
    """
    # 100,000 итераций — хороший баланс между скоростью и защитой от перебора
    return PBKDF2(password, salt, dkLen=32, count=100000, hmac_hash_module=SHA512)

def encrypt_data(plaintext: str, password: str) -> bytes:
    """
    1. Принимает данные и ключ (пароль), шифрует их.
    Возвращает связку: соль + нонс + тег + шифртекст.
    """
    # Генерируем случайную соль (16 байт)
    salt = get_random_bytes(16)
    
    # Получаем ключ из пароля
    key = derive_key(password, salt)
    
    # Создаем объект шифра AES в режиме GCM
    cipher = AES.new(key, AES.MODE_GCM)
    
    # Шифруем данные
    # digest() возвращает MAC-тег для проверки целостности при расшифровке
    ciphertext, tag = cipher.encrypt_and_digest(plaintext.encode('utf-8'))
    
    # Склеиваем всё в один байтовый объект для удобства хранения
    # Нам понадобятся соль, нонс и тег, чтобы расшифровать это позже
    return salt + cipher.nonce + tag + ciphertext

def decrypt_data(encrypted_blob: bytes, password: str) -> str:
    """
    2. Принимает зашифрованные данные и ключ (пароль), расшифровывает их.
    """
    try:
        # Извлекаем компоненты из байтового потока (порядок должен быть как при шифровании)
        salt = encrypted_blob[:16]
        nonce = encrypted_blob[16:32]
        tag = encrypted_blob[32:48]
        ciphertext = encrypted_blob[48:]
        
        # Заново генерируем тот же ключ, используя соль из архива
        key = derive_key(password, salt)
        
        # Создаем объект шифра для расшифровки
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        
        # Расшифровываем и проверяем целостность (tag)
        decrypted_data = cipher.decrypt_and_verify(ciphertext, tag)
        
        return decrypted_data.decode('utf-8')
    except (ValueError, KeyError) as e:
        return "Ошибка расшифровки: неверный пароль или данные повреждены"

# --- Пример работы ---
if __name__ == "__main__":
    secret_site_pass = "vk.com: my_password_123"
    
    print(f"Исходные данные: {secret_site_pass}")
    
    # Шифруем
    encrypted = encrypt_data(secret_site_pass, MASTER_PASSWORD)
    print(f"Зашифрованный пакет (hex): {encrypted.hex()}")
    
    # Расшифровываем
    decrypted = decrypt_data(encrypted, MASTER_PASSWORD)
    print(f"Расшифрованные данные: {decrypted}")