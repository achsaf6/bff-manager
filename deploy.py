"""
Deployment management for Google Cloud Platform.
"""

import os
from typing import Optional

from .config import ProjectConfig
from .docker_utils import DockerManager
from .gcp_utils import GCPManager
from .github_utils import GitHubManager
from .manifest import ManifestManager
from .service_account_manager import ServiceAccountManager


class DeployManager:
    """Manages deployment to Google Cloud Platform."""
    
    def __init__(self, config: ProjectConfig, manifest: ManifestManager):
        self.config = config
        self.manifest = manifest
        self.docker = DockerManager(config)
        self.gcp = GCPManager(config)
        self.github = GitHubManager(config)
        self.service_account = ServiceAccountManager(config, manifest)
    
    def confirm_deployment(self, region: str) -> bool:
        """Ask user to confirm deployment details."""
        print("")
        print("Deployment Configuration:")
        print(f"  Project ID: {self.config.gcp_project_id}")
        print(f"  Service Name: {self.config.project_name}")
        print(f"  Region: {region}")
        print(f"  Image URL: {self.config.image_url}")
        print(f"  Service Account: {self.config.service_account_email}")
        print("")
        print("This script will:")
        print("  1. Update CI/CD configuration")
        print("  2. Build and push Docker container")
        print("  3. Deploy to Cloud Run")
        print("  4. Create Service Account with necessary permissions")
        print("  5. Setup GitHub secrets")
        print("")
        
        response = input("Do you want to continue? (y/N): ")
        return response.lower() in ['y', 'yes']
    
    def update_cicd(self) -> bool:
        """Update CI/CD configuration."""
        print("")
        print("Updating CI/CD configuration...")
        
        if not self.github.update_cicd_config():
            return False
        
        self.manifest.log_operation("update_cicd", {
            "service_account": self.config.service_account_name,
            "image_url": self.config.image_url
        })
        
        return True
    
    def build_and_push_docker(self) -> bool:
        """Build and push Docker container."""
        print("")
        print("Building and pushing Docker container...")
        
        # Start Colima
        if not self.docker.start_colima():
            return False
        
        # Build image
        if not self.docker.build_image():
            self.docker.stop_colima()
            return False
        
        # Push image
        if not self.docker.push_image():
            self.docker.stop_colima()
            return False
        
        self.manifest.update_state("docker_built", True)
        self.manifest.log_operation("docker_build", {
            "image_url": self.config.image_url
        })
        
        return True
    
    def deploy_to_cloud_run(self, region: str) -> bool:
        """Deploy to Cloud Run."""
        print("")
        print("Deploying to Cloud Run...")
        
        if not self.gcp.deploy_to_cloud_run(region):
            return False
        
        self.manifest.update_state("deployed", True)
        self.manifest.update_config("region", region)
        self.manifest.log_operation("deploy_cloud_run", {
            "region": region,
            "service_name": self.config.project_name
        })
        
        return True
    
    def setup_service_account(self) -> bool:
        """Create and configure service account."""
        return self.service_account.setup()
    
    def setup_github_secrets(self) -> bool:
        """Create service account key and upload to GitHub."""
        print("")
        print("Setting up GitHub secrets...")
        
        key_file = "sa-key.json"
        
        try:
            # Create service account key
            if not self.service_account.create_key(key_file):
                return False
            
            # Upload to GitHub secrets
            if not self.github.set_secret(self.config.service_account_name, key_file):
                return False
            
            # Clean up key file
            if os.path.exists(key_file):
                os.remove(key_file)
                print(f"✓ Removed temporary key file: {key_file}")
            
            self.manifest.update_state("github_secrets_configured", True)
            self.manifest.log_operation("setup_github_secrets", {
                "secret_name": self.config.service_account_name
            })
            
            return True
        except Exception as e:
            print(f"Error setting up GitHub secrets: {e}")
            # Clean up key file on error
            if os.path.exists(key_file):
                os.remove(key_file)
            return False
    
    def deploy(self, region: Optional[str] = None) -> bool:
        """Run full deployment process."""
        region = region or self.config.default_region
        
        print(f"Starting deployment setup for: {self.config.project_name}")
        
        # Check if already deployed
        if self.manifest.get_state("deployed"):
            print("⚠️  Project is already deployed")
            response = input("Do you want to re-deploy? (y/N): ")
            if response.lower() not in ['y', 'yes']:
                return False
        
        # Confirm deployment
        if not self.confirm_deployment(region):
            print("Deployment cancelled")
            return False
        
        # Update CI/CD configuration
        if not self.update_cicd():
            print("✗ Failed to update CI/CD configuration")
            return False
        
        # Build and push Docker container
        if not self.build_and_push_docker():
            print("✗ Failed to build and push Docker container")
            return False
        
        # Deploy to Cloud Run
        if not self.deploy_to_cloud_run(region):
            print("✗ Failed to deploy to Cloud Run")
            self.docker.stop_colima()
            return False
        
        # Setup service account
        if not self.setup_service_account():
            print("✗ Failed to setup service account")
            self.docker.stop_colima()
            return False
        
        # Setup GitHub secrets
        if not self.setup_github_secrets():
            print("✗ Failed to setup GitHub secrets")
            self.docker.stop_colima()
            return False
        
        # Stop Colima
        self.docker.stop_colima()
        
        print("")
        print("=" * 60)
        print("Deployment setup complete!")
        print("=" * 60)
        print("")
        print("Next steps for production deployment:")
        print("")
        print("1. Configure backend service with Serverless NEG")
        print("2. Add IAP access for your domain")
        print("3. Update URL mapping if using a load balancer")
        print("")
        print(f"Your service is now deployed in region: {region}")
        print("")
        
        return True

