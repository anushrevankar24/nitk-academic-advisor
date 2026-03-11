"""Secrets management for sensitive credentials."""

import os
from pathlib import Path
from typing import Optional


class SecretsManager:
    """Manage sensitive credentials from various sources."""
    
    @staticmethod
    def get_secret(
        env_var: str,
        secret_file: Optional[Path] = None,
        required: bool = False
    ) -> Optional[str]:
        """
        Get a secret from multiple sources in priority order:
        1. Environment variable
        2. Docker secret file
        3. Specified secret file
        4. Return None or raise if required
        
        Args:
            env_var: Environment variable name
            secret_file: Optional path to secret file
            required: If True, raise error if secret not found
            
        Returns:
            Secret value or None
            
        Raises:
            ValueError: If required and secret not found
        """
        # 1. Try environment variable (without whitespace)
        if env_var in os.environ:
            secret = os.environ[env_var].strip()
            if secret:
                return secret
        
        # 2. Try Docker secret (standard location)
        docker_secret_path = Path(f"/run/secrets/{env_var.lower()}")
        if docker_secret_path.exists():
            try:
                secret = docker_secret_path.read_text().strip()
                if secret:
                    return secret
            except Exception:
                pass
        
        # 3. Try specified file path
        if secret_file and secret_file.exists():
            try:
                secret = secret_file.read_text().strip()
                if secret:
                    return secret
            except Exception:
                pass
        
        # 4. If required, raise error
        if required:
            raise ValueError(
                f"Required secret '{env_var}' not found in environment, "
                f"Docker secrets, or specified file."
            )
        
        return None
    
    @staticmethod
    def validate_api_key(api_key: Optional[str], key_name: str = "API_KEY") -> bool:
        """
        Validate that an API key has proper format.
        
        Args:
            api_key: API key to validate
            key_name: Name for error messages
            
        Returns:
            True if valid, False otherwise
        """
        if not api_key:
            return False
        
        # Check minimum length (Google API keys are typically 39+ chars)
        if len(api_key) < 20:
            return False
        
        # Check it's not a placeholder
        if api_key.upper() in ["YOUR_API_KEY", "YOUR_GEMINI_API_KEY", "PLACEHOLDER"]:
            return False
        
        return True
