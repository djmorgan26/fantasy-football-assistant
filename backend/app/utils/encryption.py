import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from app.core.config import settings
from typing import Optional


def _get_encryption_key() -> bytes:
    password = settings.secret_key.encode()
    salt = b'fantasy_football_salt'  # In production, use a random salt stored securely
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password))
    return key


def encrypt_data(data: str) -> str:
    if not data:
        return ""
    
    key = _get_encryption_key()
    f = Fernet(key)
    encrypted_data = f.encrypt(data.encode())
    return base64.urlsafe_b64encode(encrypted_data).decode()


def decrypt_data(encrypted_data: str) -> Optional[str]:
    if not encrypted_data:
        return None
    
    try:
        key = _get_encryption_key()
        f = Fernet(key)
        decoded_data = base64.urlsafe_b64decode(encrypted_data.encode())
        decrypted_data = f.decrypt(decoded_data)
        return decrypted_data.decode()
    except Exception:
        return None


class ESPNCredentialManager:
    @staticmethod
    def encrypt_espn_s2(espn_s2: str) -> str:
        return encrypt_data(espn_s2)
    
    @staticmethod
    def encrypt_espn_swid(espn_swid: str) -> str:
        return encrypt_data(espn_swid)
    
    @staticmethod
    def decrypt_espn_s2(encrypted_s2: str) -> Optional[str]:
        return decrypt_data(encrypted_s2)
    
    @staticmethod
    def decrypt_espn_swid(encrypted_swid: str) -> Optional[str]:
        return decrypt_data(encrypted_swid)
    
    @staticmethod
    def get_espn_cookies_for_user(user) -> Optional[dict]:
        if not user.espn_s2_encrypted and not user.espn_swid_encrypted:
            return None
        
        cookies = {}
        
        if user.espn_s2_encrypted:
            s2 = ESPNCredentialManager.decrypt_espn_s2(user.espn_s2_encrypted)
            if s2:
                cookies["espn_s2"] = s2
        
        if user.espn_swid_encrypted:
            swid = ESPNCredentialManager.decrypt_espn_swid(user.espn_swid_encrypted)
            if swid:
                cookies["SWID"] = swid
        
        return cookies if cookies else None