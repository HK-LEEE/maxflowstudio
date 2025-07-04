"""
Encryption Service
Handles encryption and decryption of sensitive data using Fernet symmetric encryption
"""

import base64
import os
from typing import Optional, Union
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from src.config.settings import get_settings


class EncryptionService:
    """Service for encrypting and decrypting sensitive data"""
    
    def __init__(self):
        self._fernet: Optional[Fernet] = None
        self._encryption_key: Optional[bytes] = None
        
    def _get_encryption_key(self) -> bytes:
        """Get or generate encryption key from settings"""
        if self._encryption_key is not None:
            return self._encryption_key
            
        settings = get_settings()
        
        # Use JWT secret as base for encryption key
        password = settings.JWT_SECRET_KEY.encode()
        
        # Use a fixed salt for deterministic key generation
        # In production, consider storing salt separately
        salt = b"MAX_FLOWSTUDIO_SALT_2024"
        
        # Derive key using PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(password))
        self._encryption_key = key
        return key
    
    def _get_fernet(self) -> Fernet:
        """Get or create Fernet instance"""
        if self._fernet is None:
            key = self._get_encryption_key()
            self._fernet = Fernet(key)
        return self._fernet
    
    def encrypt(self, data: Union[str, bytes]) -> str:
        """
        Encrypt data and return base64 encoded string
        
        Args:
            data: String or bytes to encrypt
            
        Returns:
            Base64 encoded encrypted data
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        fernet = self._get_fernet()
        encrypted_data = fernet.encrypt(data)
        return base64.b64encode(encrypted_data).decode('utf-8')
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt base64 encoded encrypted data
        
        Args:
            encrypted_data: Base64 encoded encrypted string
            
        Returns:
            Decrypted string
            
        Raises:
            ValueError: If decryption fails
        """
        try:
            # Decode from base64
            encrypted_bytes = base64.b64decode(encrypted_data.encode('utf-8'))
            
            # Decrypt
            fernet = self._get_fernet()
            decrypted_data = fernet.decrypt(encrypted_bytes)
            
            return decrypted_data.decode('utf-8')
        except Exception as e:
            raise ValueError(f"Decryption failed: {str(e)}")
    
    def is_encrypted(self, data: str) -> bool:
        """
        Check if data appears to be encrypted
        
        Args:
            data: String to check
            
        Returns:
            True if data appears to be encrypted
        """
        if not data:
            return False
            
        try:
            # Try to decode as base64
            decoded = base64.b64decode(data.encode('utf-8'))
            
            # Encrypted data should be at least 45 bytes (Fernet minimum)
            if len(decoded) < 45:
                return False
                
            # Try to decrypt to verify
            fernet = self._get_fernet()
            fernet.decrypt(decoded)
            return True
        except Exception:
            return False
    
    def encrypt_if_needed(self, data: str, should_encrypt: bool = True) -> tuple[str, bool]:
        """
        Encrypt data if needed and not already encrypted
        
        Args:
            data: Data to potentially encrypt
            should_encrypt: Whether encryption should be applied
            
        Returns:
            Tuple of (processed_data, is_encrypted)
        """
        if not data:
            return data, False
            
        if not should_encrypt:
            return data, False
            
        # Don't encrypt if already encrypted
        if self.is_encrypted(data):
            return data, True
            
        encrypted_data = self.encrypt(data)
        return encrypted_data, True
    
    def decrypt_if_needed(self, data: str) -> str:
        """
        Decrypt data if it's encrypted, otherwise return as-is
        
        Args:
            data: Data to potentially decrypt
            
        Returns:
            Decrypted or original data
        """
        if not data:
            return data
            
        if self.is_encrypted(data):
            try:
                return self.decrypt(data)
            except ValueError:
                # If decryption fails, return original data
                return data
        
        return data
    
    def get_encrypted_length_estimate(self, data: str) -> int:
        """
        Estimate the length of data after encryption
        
        Args:
            data: Original data
            
        Returns:
            Estimated encrypted length (base64 encoded)
        """
        if not data:
            return 0
            
        # Fernet adds ~45 bytes overhead, then base64 encoding adds ~33% overhead
        original_length = len(data.encode('utf-8'))
        fernet_length = original_length + 45
        base64_length = int(fernet_length * 4 / 3) + 4  # base64 overhead
        
        return base64_length


# Create singleton instance
encryption_service = EncryptionService()