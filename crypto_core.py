import os
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Hash import SHA512
from Crypto.Random import get_random_bytes

# Итерации для PBKDF2
KDF_ITERATIONS = 100000

def derive_key(password: str, salt: bytes) -> bytes:
    """Генерация 32-байтного ключа из пароля."""
    return PBKDF2(password, salt, dkLen=32, count=KDF_ITERATIONS, hmac_hash_module=SHA512)

def encrypt_data(plaintext: str, password: str) -> bytes:
    """Шифрует строку и возвращает байтовый пакет (Salt + Nonce + Tag + Ciphertext)."""
    salt = get_random_bytes(16)
    key = derive_key(password, salt)
    cipher = AES.new(key, AES.MODE_GCM)
    
    ciphertext, tag = cipher.encrypt_and_digest(plaintext.encode('utf-8'))
    
    # Склеиваем всё в один бинарный блок
    return salt + cipher.nonce + tag + ciphertext

def decrypt_data(encrypted_blob: bytes, password: str) -> str:
    """Расшифровывает байтовый пакет. Возвращает строку или None при ошибке."""
    try:
        # Извлечение компонентов (строго по оффсетам)
        salt = encrypted_blob[:16]
        nonce = encrypted_blob[16:32]
        tag = encrypted_blob[32:48]
        ciphertext = encrypted_blob[48:]
        
        key = derive_key(password, salt)
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        
        decrypted_data = cipher.decrypt_and_verify(ciphertext, tag)
        return decrypted_data.decode('utf-8')
    except Exception:
        # Ошибка будет если пароль неверный или данные изменены
        return None