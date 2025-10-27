"""
Project cleanup and teardown.
"""

import shutil
import subprocess
from pathlib import Path

from .config import ProjectConfig
from .docker_utils import DockerManager
from .gcp_utils import GCPManager
from .github_utils import GitHubManager
from .manifest import ManifestManager
from .service_account_manager import ServiceAccountManager


class CleanManager:
    """Manages project cleanup and teardown."""
    
    def __init__(self, config: ProjectConfig, manifest: ManifestManager):
        self.config = config
        self.manifest = manifest
        self.docker = DockerManager(config)
        self.gcp = GCPManager(config)
        self.github = GitHubManager(config)
        self.service_account = ServiceAccountManager(config, manifest)
    
    def confirm_cleanup(self) -> bool:
        """Ask user to confirm cleanup with project name verification."""
        print("")
        print("⚠️  WARNING: This will delete the entire project, including:")
        print("  - GitHub repository")
        print("  - Docker images and containers")
        print("  - GCP Service Account")
        print("  - GCP Cloud Run service")
        print("  - Local repository")
        print("")
        print(f"To confirm, please type the project name: {self.config.project_name}")
        print("Type 'q' or 'x' to abort.")
        print("")
        
        while True:
            confirmation = input("Project name: ").strip()
            
            if confirmation in ['q', 'x', 'Q', 'X']:
                print("Aborted by user.")
                return False
            
            if confirmation == self.config.project_name:
                return True
            
            print(f"Project name does not match. Try again or type 'q' or 'x' to abort.")
    
    def cleanup_github(self) -> bool:
        """Delete GitHub repository."""
        print("")
        print("Deleting GitHub repository...")
        
        if self.github.delete_repository():
            print("✓ GitHub repository deleted")
            return True
        else:
            print("✗ Failed to delete GitHub repository (continuing anyway)")
            return False
    
    def cleanup_docker(self) -> bool:
        """Remove Docker images and containers."""
        print("")
        print("Removing Docker resources...")
        
        self.docker.cleanup()
        print("✓ Docker resources cleaned up")
        return True
    
    def cleanup_gcp(self) -> bool:
        """Remove GCP resources."""
        print("")
        print("Removing GCP resources...")
        
        # Get region from manifest or use default
        region = self.manifest.get_config("region", self.config.default_region)
        
        # Delete Cloud Run service
        if self.manifest.get_state("deployed"):
            self.gcp.delete_cloud_run_service(region)
            print("✓ Cloud Run service deleted")
        
        # Delete Service Account
        if self.manifest.get_state("service_account_created"):
            self.service_account.delete()
            print("✓ Service Account deleted")
        
        return True
    
    def create_template_from_git(self, parent_dir: Path, project_name: str) -> bool:
        """Clone a fresh template from the bff-template repository."""
        print("")
        print("Creating new template from GitHub...")
        
        template_url = "https://github.com/achsaf6/bff-template.git"
        target_path = parent_dir / project_name
        
        try:
            # Clone the repository
            subprocess.run(
                ["git", "clone", template_url, str(target_path)],
                check=True,
                capture_output=True,
                text=True
            )
            print(f"✓ Template cloned to {target_path}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"✗ Error cloning template: {e.stderr}")
            return False
        except FileNotFoundError:
            print("✗ Git is not installed or not available in PATH")
            return False
    
    def cleanup_local(self) -> bool:
        """Remove local repository and create a fresh template."""
        print("")
        print("Removing local repository...")
        
        # Get parent directory
        parent_dir = self.config.project_root.parent
        current_dir = self.config.project_root
        project_name = self.config.project_name
        
        print(f"⚠️  This will delete: {current_dir}")
        print("This action cannot be undone!")
        print("")
        
        response = input("Are you absolutely sure? (yes/N): ")
        if response.lower() != 'yes':
            print("Local cleanup skipped")
            return False
        
        try:
            # Remove the entire directory
            shutil.rmtree(current_dir)
            print("✓ Local repository deleted")
            
            # Create fresh template
            self.create_template_from_git(parent_dir, project_name)
            
            return True
        except Exception as e:
            print(f"✗ Error deleting local repository: {e}")
            return False
    
    def clean(self, skip_local: bool = False) -> bool:
        """Run full cleanup process."""
        print(f"Starting cleanup process for: {self.config.project_name}")
        
        # Confirm cleanup
        if not self.confirm_cleanup():
            return False
        
        print("")
        print("Starting cleanup...")
        
        # Log cleanup operation
        self.manifest.log_operation("cleanup", {"type": "full"})
        
        # Cleanup GitHub
        self.cleanup_github()
        
        # Cleanup Docker
        self.cleanup_docker()
        
        # Cleanup GCP
        self.cleanup_gcp()
        
        # Cleanup local (if not skipped)
        if not skip_local:
            self.cleanup_local()
        else:
            print("")
            print("Local cleanup skipped")
            # Reset manifest
            self.manifest.reset_manifest()
            print("✓ Manifest reset")
        
        print("")
        print("=" * 50)
        print("Cleanup completed successfully!")
        print("=" * 50)
        print("")
        
        return True

