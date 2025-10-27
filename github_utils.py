"""
GitHub utilities for repository and secrets management.
"""

import subprocess
from pathlib import Path
from typing import Optional

from .config import ProjectConfig


class GitHubManager:
    """Manages GitHub operations."""
    
    def __init__(self, config: ProjectConfig):
        self.config = config
    
    def get_repo_name(self) -> Optional[str]:
        """Get the current repository name with owner."""
        try:
            result = subprocess.run(
                ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"Error getting repository name: {e}")
            return None
    
    def set_secret(self, secret_name: str, secret_file: str) -> bool:
        """Set a GitHub secret from a file."""
        try:
            print(f"Setting GitHub secret: {secret_name}")
            with open(secret_file, 'r') as f:
                subprocess.run(
                    ["gh", "secret", "set", secret_name],
                    stdin=f,
                    check=True
                )
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error setting GitHub secret: {e}")
            return False
    
    def delete_repository(self) -> bool:
        """Delete the GitHub repository."""
        repo_name = self.get_repo_name()
        
        if not repo_name:
            print("Could not determine repository name")
            return False
        
        try:
            print(f"Deleting GitHub repository: {repo_name}")
            result = subprocess.run(
                ["gh", "repo", "delete", repo_name, "--yes"],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0:
                print(f"✓ Repository deleted successfully")
                return True
            else:
                print(f"✗ Error deleting repository: {result.stderr}")
                return False
        except subprocess.CalledProcessError as e:
            print(f"✗ Error deleting GitHub repository: {e}")
            return False
    
    def update_cicd_config(self) -> bool:
        """Update CI/CD configuration file with project-specific values."""
        if not self.config.cicd_file.exists():
            print(f"CI/CD file not found: {self.config.cicd_file}")
            return False
        
        try:
            content = self.config.cicd_file.read_text()
            
            # Update service account name
            content = content.replace(
                'name = "BFF_TEMPLATE_SA"',
                f'name = "{self.config.service_account_name}"'
            )
            
            # Update service name
            content = content.replace(
                'name = "bff-template-service-name"',
                f'name = "{self.config.project_name}"'
            )
            
            # Update image URL
            content = content.replace(
                'name = "bff-template-image-url"',
                f'name = "{self.config.image_url}"'
            )
            
            # Activate CI/CD (remove the if: false condition)
            content = content.replace('name = "  if: false"', 'name = ""')
            
            self.config.cicd_file.write_text(content)
            print("CI/CD configuration updated")
            return True
        except Exception as e:
            print(f"Error updating CI/CD config: {e}")
            return False

