"""
Password Security with Argon2

Uses Argon2id algorithm (resistant to GPU/ASIC attacks).
Better security than PBKDF2 with similar performance.
"""

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError

# Argon2 configuration
# Time cost: higher = slower but more secure (3-4 typical)
# Memory cost: in KB (65536 = 64MB typical)
# Parallelism: number of threads
hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,  # 64 MB
    parallelism=4,
    hash_len=32,
    salt_len=16,
)


def hash_password(password: str) -> str:
    """
    Hash password using Argon2id.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password string
        
    Raises:
        ValueError: If password is too long or invalid
    """
    if not password or len(password) > 1024:
        raise ValueError("Invalid password")
    
    try:
        return hasher.hash(password)
    except Exception as e:
        raise ValueError(f"Password hashing failed: {str(e)}")


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify password against hash.
    Automatically checks for hash updates (key stretching).
    
    Args:
        password: Plain text password to verify
        password_hash: Stored hash to verify against
        
    Returns:
        True if password matches, False otherwise
    """
    if not password or not password_hash:
        return False
    
    try:
        hasher.verify(password_hash, password)
        
        # Check if hash needs update
        if hasher.check_needs_rehash(password_hash):
            # Signal to application that password should be rehashed
            return True
        
        return True
    except (VerifyMismatchError, InvalidHashError):
        return False


def needs_password_rehash(password_hash: str) -> bool:
    """
    Check if password hash needs updating due to algorithm changes.
    
    Args:
        password_hash: Hash to check
        
    Returns:
        True if hash should be updated, False otherwise
    """
    try:
        return hasher.check_needs_rehash(password_hash)
    except (InvalidHashError, ValueError):
        return True
