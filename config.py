"""
Configuration management for the project.
"""

import os
from pathlib import Path
from typing import Optional


class ProjectConfig:
    """Manages project configuration and environment."""
    
    def __init__(self):
        self.project_root = Path.cwd()
        self.project_name = self._get_project_name()
        self.gcp_project_id = "marketing-innovation-450013"
        self.default_region = "europe-west4"
    
    def _get_project_name(self) -> str:
        """Get the project name from the current directory."""
        return self.project_root.name.lower()
    
    @property
    def service_account_email(self) -> str:
        """Get the service account email."""
        return f"{self.project_name}-sa@{self.gcp_project_id}.iam.gserviceaccount.com"
    
    @property
    def service_account_name(self) -> str:
        """Get the service account name for GitHub secrets."""
        return self.project_name.upper().replace('-', '_') + '_SA'
    
    @property
    def image_url(self) -> str:
        """Get the Docker image URL."""
        return f"gcr.io/{self.gcp_project_id}/{self.project_name}"
    
    @property
    def cicd_file(self) -> Path:
        """Get the CI/CD workflow file path."""
        return self.project_root / ".github" / "workflows" / "cicd.yaml"
    
    @property
    def pyproject_file(self) -> Path:
        """Get the pyproject.toml file path."""
        return self.project_root / "pyproject.toml"
    
    @property
    def makefile(self) -> Path:
        """Get the Makefile path."""
        return self.project_root / "makefile"
    
    @property
    def frontend_dir(self) -> Path:
        """Get the frontend directory path."""
        return self.project_root / "frontend"
    
    @property
    def backend_dir(self) -> Path:
        """Get the backend directory path."""
        return self.project_root / "backend"
    
    @property
    def env_file(self) -> Path:
        """Get the .env file path."""
        return self.project_root / ".env"
    
    def get_region(self, default: Optional[str] = None) -> str:
        """Get the deployment region."""
        return default or self.default_region
    
    def ensure_env_file(self) -> None:
        """Ensure .env file exists."""
        if not self.env_file.exists():
            self.env_file.touch()
