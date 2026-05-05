import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

ENCRYPTION_KEY_B64 = os.getenv('ENCRYPTION_KEY')
if not ENCRYPTION_KEY_B64:
    raise ValueError("ENCRYPTION_KEY must be set in .env for Sabiha Ashraf Care Center")


def _build_aes_key(key_b64: str) -> bytes:
    """Derive a stable 32-byte AES key from the configured string."""
    try:
        key_bytes = base64.urlsafe_b64decode(key_b64)
        if len(key_bytes) != 32:
            import hashlib
            key_bytes = hashlib.sha256(key_bytes).digest()
    except Exception:
        import hashlib
        key_bytes = hashlib.sha256(key_b64.encode()).digest()
    return key_bytes


def _iter_legacy_key_strings() -> list[str]:
    """Return current + legacy Fernet keys for backward-compatible decryption."""
    seen = set()
    keys = []
    for key in [ENCRYPTION_KEY_B64, *os.getenv('LEGACY_ENCRYPTION_KEYS', '').split(',')]:
        key = (key or '').strip()
        if key and key not in seen:
            seen.add(key)
            keys.append(key)
    return keys


aesgcm = AESGCM(_build_aes_key(ENCRYPTION_KEY_B64))
legacy_ciphers = []
legacy_aesgcm = []
for key_b64 in _iter_legacy_key_strings():
    try:
        legacy_ciphers.append(Fernet(key_b64.encode()))
    except Exception:
        continue
    try:
        legacy_aesgcm.append(AESGCM(_build_aes_key(key_b64)))
    except Exception:
        continue

def encrypt_data(data: str) -> str:
    """
    Encrypt a string using the primary AES-256-GCM key.
    Returns a base64 encoded string with a 'v2:' prefix for identification.
    """
    if not data:
        return ""
    
    nonce = os.urandom(12)  # GCM recommended nonce size is 12 bytes
    ciphertext = aesgcm.encrypt(nonce, data.encode(), None)
    
    # Combine nonce + ciphertext and encode
    combined = nonce + ciphertext
    return "v2:" + base64.b64encode(combined).decode()

def decrypt_data(encrypted_data: str) -> str:
    """
    Decrypts a base64 encoded string.
    Supports both 'v2:' (AES-256-GCM) and legacy Fernet formats.
    Also tries any keys listed in LEGACY_ENCRYPTION_KEYS.
    """
    if not encrypted_data:
        return ""
    
    # Check for v2 prefix
    if isinstance(encrypted_data, str) and encrypted_data.startswith("v2:"):
        try:
            raw_data = base64.b64decode(encrypted_data[3:])
            nonce = raw_data[:12]
            ciphertext = raw_data[12:]
            for cipher in legacy_aesgcm:
                try:
                    return cipher.decrypt(nonce, ciphertext, None).decode()
                except Exception:
                    continue
        except Exception as e:
            print(f"[Encryption] AES-256-GCM decode failed: {e}")
        return encrypted_data

    # Try legacy Fernet decryption across current + configured legacy keys.
    raw_value = encrypted_data.encode() if isinstance(encrypted_data, str) else encrypted_data
    for cipher in legacy_ciphers:
        try:
            return cipher.decrypt(raw_value).decode()
        except Exception:
            continue

    # If decryption fails (e.g., data wasn't encrypted), return as-is.
    return encrypted_data
