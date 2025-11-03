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
    
    def set_secret_value(self, secret_name: str, secret_value: str) -> bool:
        """Set a GitHub secret from a string value."""
        try:
            print(f"Setting GitHub secret: {secret_name}")
            result = subprocess.run(
                ["gh", "secret", "set", secret_name],
                input=secret_value,
                text=True,
                check=True,
                capture_output=True
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
            # Try with --yes flag first (for newer versions of gh CLI)
            result = subprocess.run(
                ["gh", "repo", "delete", "--yes"],
                capture_output=True,
                text=True,
                check=False
            )
            
            # If that fails, try with --confirm flag (for older versions)
            if result.returncode != 0:
                print(f"Retrying with --confirm flag...")
                result = subprocess.run(
                    ["gh", "repo", "delete", repo_name, "--confirm"],
                    capture_output=True,
                    text=True,
                    check=False
                )
            
            if result.returncode == 0:
                print(f"✓ Repository deleted successfully")
                return True
            else:
                error_msg = result.stderr if result.stderr else result.stdout
                print(f"✗ Error deleting repository: {error_msg}")
                # Print full output for debugging
                if result.stdout:
                    print(f"  stdout: {result.stdout}")
                return False
        except FileNotFoundError:
            print("✗ GitHub CLI (gh) is not installed or not available in PATH")
            return False
        except Exception as e:
            print(f"✗ Error deleting GitHub repository: {e}")
            return False
    
    def update_cicd_config(self) -> bool:
        """Update CI/CD configuration file with project-specific values."""
        if not self.config.cicd_file.exists():
            print(f"CI/CD file not found: {self.config.cicd_file}")
            return False
        
        try:
            content = self.config.cicd_file.read_text()
            
            # Update service name
            content = content.replace(
                'SERVICE_NAME: bff-template-service-name',
                f'SERVICE_NAME: {self.config.project_name}'
            )
            
            # Update project ID (should already be correct but ensure it)
            content = content.replace(
                'PROJECT_ID: marketing-innovation-450013',
                f'PROJECT_ID: {self.config.gcp_project_id}'
            )
            
            # Update image URL
            content = content.replace(
                'DOCKER_IMAGE_URL: bff-template-image-url',
                f'DOCKER_IMAGE_URL: {self.config.image_url}'
            )
            
            # Update secret name in the credentials line
            content = content.replace(
                'credentials_json: ${{ secrets.BFF_TEMPLATE_SA }}',
                f'credentials_json: ${{{{ secrets.{self.config.service_account_name} }}}}'
            )
            
            # Update region references
            content = content.replace(
                'IMAGE_REGION: europe-west4',
                f'IMAGE_REGION: {self.config.default_region}'
            )
            content = content.replace(
                'CONTAINER_REGION: europe-west4',
                f'CONTAINER_REGION: {self.config.default_region}'
            )
            
            # Activate CI/CD 
            content = content.replace('    if: false\n', '')
            
            self.config.cicd_file.write_text(content)
            print("CI/CD configuration updated")
            return True
        except Exception as e:
            print(f"Error updating CI/CD config: {e}")
            return False
