"""
Load balancer management for Google Cloud Platform.
"""

import json
import subprocess
from typing import Optional, List

from .config import ProjectConfig
from .manifest import ManifestManager


class LoadBalancerManager:
    """Manages load balancer configuration for Cloud Run services."""
    
    # Hardcoded values based on existing infrastructure
    URL_MAP_NAME = "marketing-ai-url-map"
    DOMAIN = "marketing-ai.lightricks.com"
    BRAND_NAME = "projects/924389117365/brands/924389117365"
    IAP_DOMAIN = "lightricks.com"
    
    def __init__(self, config: ProjectConfig, manifest: ManifestManager):
        self.config = config
        self.manifest = manifest
    
    def create_serverless_neg(self, region: str, cloud_run_service: str) -> bool:
        """Create a serverless Network Endpoint Group for Cloud Run."""
        neg_name = f"{self.config.project_name}-neg"
        
        try:
            # Check if NEG already exists
            check_result = subprocess.run([
                "gcloud", "compute", "network-endpoint-groups", "describe", neg_name,
                f"--region={region}",
                f"--project={self.config.gcp_project_id}"
            ], capture_output=True, text=True)
            
            if check_result.returncode == 0:
                print(f"✓ NEG already exists: {neg_name}")
                return True
            
            # Create the NEG
            print(f"Creating serverless NEG: {neg_name}")
            subprocess.run([
                "gcloud", "compute", "network-endpoint-groups", "create", neg_name,
                f"--region={region}",
                "--network-endpoint-type=SERVERLESS",
                f"--cloud-run-service={cloud_run_service}",
                f"--project={self.config.gcp_project_id}"
            ], check=True)
            print(f"✓ Created NEG: {neg_name}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error creating NEG: {e}")
            return False
    
    def create_iap_oauth_client(self) -> Optional[dict]:
        """Create an IAP OAuth client for the backend service."""
        client_name = f"IAP-{self.config.project_name}-backend"
        
        try:
            print(f"Creating IAP OAuth client: {client_name}")
            result = subprocess.run([
                "gcloud", "iap", "oauth-clients", "create",
                self.BRAND_NAME,
                f"--display_name={client_name}"
            ], check=True, capture_output=True, text=True)
            
            # Parse the output to get client ID and secret
            output = result.stdout
            client_id = None
            client_secret = None
            
            for line in output.split('\n'):
                if 'name:' in line:
                    # Extract client ID from the full path
                    full_path = line.split('name:')[1].strip()
                    client_id = full_path.split('/')[-1]
                elif 'secret:' in line:
                    client_secret = line.split('secret:')[1].strip()
            
            if client_id and client_secret:
                print(f"✓ Created OAuth client: {client_name}")
                return {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "display_name": client_name
                }
            else:
                print("Error: Could not parse OAuth client credentials")
                return None
                
        except subprocess.CalledProcessError as e:
            print(f"Error creating OAuth client: {e}")
            return None
    
    def create_security_policy(self) -> bool:
        """Create a Cloud Armor security policy with rate limiting."""
        policy_name = f"default-security-policy-for-backend-service-{self.config.project_name}-backend"
        
        try:
            # Check if policy already exists
            check_result = subprocess.run([
                "gcloud", "compute", "security-policies", "describe", policy_name,
                f"--project={self.config.gcp_project_id}"
            ], capture_output=True, text=True)
            
            if check_result.returncode == 0:
                print(f"✓ Security policy already exists: {policy_name}")
                return True
            
            print(f"Creating security policy: {policy_name}")
            
            # Create the policy
            subprocess.run([
                "gcloud", "compute", "security-policies", "create", policy_name,
                f"--description=Default security policy for: {self.config.project_name}-backend",
                f"--project={self.config.gcp_project_id}"
            ], check=True)
            
            # Add rate limiting rule
            subprocess.run([
                "gcloud", "compute", "security-policies", "rules", "create", "2147483646",
                f"--security-policy={policy_name}",
                "--action=throttle",
                "--description=Default rate limiting rule",
                "--src-ip-ranges=*",
                "--rate-limit-threshold-count=500",
                "--rate-limit-threshold-interval-sec=60",
                "--conform-action=allow",
                "--exceed-action=deny-403",
                "--enforce-on-key=IP",
                f"--project={self.config.gcp_project_id}"
            ], check=True)
            
            print(f"✓ Created security policy with rate limiting (500 req/60s)")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"Error creating security policy: {e}")
            return False
    
    def create_backend_service(self, region: str, oauth_client: dict) -> bool:
        """Create a backend service with IAP enabled."""
        backend_name = f"{self.config.project_name}-backend"
        neg_name = f"{self.config.project_name}-neg"
        policy_name = f"default-security-policy-for-backend-service-{backend_name}"
        
        try:
            # Check if backend service already exists
            check_result = subprocess.run([
                "gcloud", "compute", "backend-services", "describe", backend_name,
                "--global",
                f"--project={self.config.gcp_project_id}"
            ], capture_output=True, text=True)
            
            if check_result.returncode == 0:
                print(f"✓ Backend service already exists: {backend_name}")
                # Check if it has backends attached
                import json
                try:
                    backend_info = json.loads(check_result.stdout)
                    has_backends = "backends" in backend_info and len(backend_info.get("backends", [])) > 0
                    
                    if not has_backends:
                        print(f"  → Backend service has no NEG attached, adding it now...")
                        
                        # Check if there's a problematic portName set
                        port_name = backend_info.get("portName")
                        if port_name:
                            print(f"  → Detected portName '{port_name}', need to recreate backend service...")
                            print(f"  → Deleting broken backend service...")
                            subprocess.run([
                                "gcloud", "compute", "backend-services", "delete", backend_name,
                                "--global",
                                "--quiet",
                                f"--project={self.config.gcp_project_id}"
                            ], check=True)
                            print(f"  ✓ Deleted, will recreate below...")
                            # Fall through to creation code below
                        else:
                            # No portName issue, try to add NEG
                            add_result = subprocess.run([
                                "gcloud", "compute", "backend-services", "add-backend", backend_name,
                                "--global",
                                f"--network-endpoint-group={neg_name}",
                                f"--network-endpoint-group-region={region}",
                                f"--project={self.config.gcp_project_id}"
                            ], capture_output=True, text=True)
                            
                            if add_result.returncode != 0:
                                print(f"  ✗ Failed to add NEG: {add_result.stderr}")
                                return False
                            else:
                                print(f"  ✓ Added NEG to existing backend service")
                                return True
                    else:
                        # Has backends, just ensure security policy is attached
                        subprocess.run([
                            "gcloud", "compute", "backend-services", "update", backend_name,
                            "--global",
                            f"--security-policy={policy_name}",
                            f"--project={self.config.gcp_project_id}"
                        ], check=False, capture_output=True)
                        return True
                        
                except Exception as e:
                    print(f"  Warning: Could not check/update existing backend: {e}")
                    return False
            
            print(f"Creating backend service: {backend_name}")
            
            # Create the backend service with IAP and CORS (no protocol to avoid port_name issues)
            subprocess.run([
                "gcloud", "compute", "backend-services", "create", backend_name,
                "--global",
                "--load-balancing-scheme=EXTERNAL_MANAGED",
                f"--iap=enabled,oauth2-client-id={oauth_client['client_id']},oauth2-client-secret={oauth_client['client_secret']}",
                f"--custom-response-header=Access-Control-Allow-Methods: GET,POST,OPTIONS",
                f"--custom-response-header=Access-Control-Allow-Origin: https://{self.DOMAIN}",
                f"--custom-response-header=Access-Control-Allow-Headers: *",
                f"--custom-response-header=Access-Control-Allow-Credentials: true",
                f"--project={self.config.gcp_project_id}"
            ], check=True)
            
            # Add the NEG as a backend (serverless NEGs don't need protocol set)
            subprocess.run([
                "gcloud", "compute", "backend-services", "add-backend", backend_name,
                "--global",
                f"--network-endpoint-group={neg_name}",
                f"--network-endpoint-group-region={region}",
                f"--project={self.config.gcp_project_id}"
            ], check=True)
            
            # Attach security policy to the backend service
            print(f"Attaching security policy to backend service...")
            subprocess.run([
                "gcloud", "compute", "backend-services", "update", backend_name,
                "--global",
                f"--security-policy={policy_name}",
                f"--project={self.config.gcp_project_id}"
            ], check=True)
            
            print(f"✓ Created backend service with IAP enabled")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"Error creating backend service: {e}")
            return False
    
    def grant_iap_access(self, backend_name: str) -> bool:
        """Grant IAP access to the lightricks.com domain."""
        try:
            print(f"Granting IAP access to {self.IAP_DOMAIN} domain")
            subprocess.run([
                "gcloud", "iap", "web", "add-iam-policy-binding",
                "--resource-type=backend-services",
                f"--service={backend_name}",
                f"--member=domain:{self.IAP_DOMAIN}",
                "--role=roles/iap.httpsResourceAccessor",
                f"--project={self.config.gcp_project_id}"
            ], check=False)  # Use check=False since adding existing binding is not an error
            print(f"✓ Granted IAP access to domain: {self.IAP_DOMAIN}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error granting IAP access: {e}")
            return False
    
    def add_path_rule(self, path: str, backend_name: str, cloud_run_url: Optional[str] = None) -> bool:
        """Add a path rule to the URL map."""
        try:
            print(f"Adding path rule for: {path}")
            
            # Get current URL map
            result = subprocess.run([
                "gcloud", "compute", "url-maps", "describe", self.URL_MAP_NAME,
                "--format=json",
                f"--project={self.config.gcp_project_id}"
            ], check=True, capture_output=True, text=True)
            
            url_map = json.loads(result.stdout)
            
            # Build the new path rule
            new_rule = {
                "paths": [
                    path,
                    f"{path}/",
                    f"{path}/*"
                ],
                "routeAction": {
                    "urlRewrite": {
                        "pathPrefixRewrite": "/"
                    }
                },
                "service": f"https://www.googleapis.com/compute/v1/projects/{self.config.gcp_project_id}/global/backendServices/{backend_name}"
            }
            
            # Add hostRewrite if Cloud Run URL is provided
            if cloud_run_url:
                new_rule["routeAction"]["urlRewrite"]["hostRewrite"] = cloud_run_url
            
            # Find the path matcher and add the rule
            for matcher in url_map.get("pathMatchers", []):
                if matcher["name"] == "path-matcher-1":
                    if "pathRules" not in matcher:
                        matcher["pathRules"] = []
                    matcher["pathRules"].append(new_rule)
                    break
            
            # Clean up output-only fields that cause import issues
            # Convert id from string to int, or remove it
            if "id" in url_map:
                try:
                    url_map["id"] = int(url_map["id"])
                except (ValueError, TypeError):
                    del url_map["id"]
            
            # Remove other output-only fields
            for field in ["creationTimestamp", "selfLink", "fingerprint", "kind"]:
                if field in url_map:
                    del url_map[field]
            
            # Clean up nested output-only fields in pathMatchers
            for matcher in url_map.get("pathMatchers", []):
                for field in ["kind"]:
                    if field in matcher:
                        del matcher[field]
            
            # Write the updated URL map to a temp file
            temp_file = "/tmp/url-map-update.json"
            with open(temp_file, 'w') as f:
                json.dump(url_map, f, indent=2)
            
            # Update the URL map
            subprocess.run([
                "gcloud", "compute", "url-maps", "import", self.URL_MAP_NAME,
                f"--source={temp_file}",
                "--quiet",
                f"--project={self.config.gcp_project_id}"
            ], check=True)
            
            print(f"✓ Added path rule: {path}/* -> {backend_name}")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"Error adding path rule: {e}")
            return False
        except json.JSONDecodeError as e:
            print(f"Error parsing URL map JSON: {e}")
            return False
    
    def get_cloud_run_url(self, service_name: str, region: str) -> Optional[str]:
        """Get the Cloud Run service URL."""
        try:
            result = subprocess.run([
                "gcloud", "run", "services", "describe", service_name,
                f"--region={region}",
                "--format=json",
                f"--project={self.config.gcp_project_id}"
            ], check=True, capture_output=True, text=True)
            
            service_info = json.loads(result.stdout)
            url = service_info.get("status", {}).get("url", "")
            if url:
                # Extract hostname from URL
                return url.replace("https://", "").replace("http://", "")
            return None
            
        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            print(f"Warning: Could not get Cloud Run URL: {e}")
            return None
    
    def add_to_loadbalancer(
        self,
        path: Optional[str] = None,
        region: Optional[str] = None,
        cloud_run_service: Optional[str] = None,
        use_host_rewrite: bool = True
    ) -> bool:
        """
        Add the deployed Cloud Run service to the load balancer.
        
        Args:
            path: URL path prefix (default: /{project-name})
            region: GCP region (default: from manifest or config)
            cloud_run_service: Cloud Run service name (default: project name)
            use_host_rewrite: Whether to use host rewrite to Cloud Run URL
        """
        # Set defaults
        path = path or f"/{self.config.project_name}"
        region = region or self.manifest.get_config("region") or self.config.default_region
        cloud_run_service = cloud_run_service or self.config.project_name
        backend_name = f"{self.config.project_name}-backend"
        
        # Check if Cloud Run service is deployed
        if not self.manifest.get_state("deployed"):
            print("Error: Cloud Run service is not deployed yet. Run 'python -m manager deploy' first.")
            return False
        
        print("")
        print("=" * 60)
        print(f"Adding {self.config.project_name} to Load Balancer")
        print("=" * 60)
        print("")
        print(f"  Path: {path}/*")
        print(f"  Domain: https://{self.DOMAIN}{path}")
        print(f"  Backend: {backend_name}")
        print(f"  Cloud Run Service: {cloud_run_service}")
        print(f"  Region: {region}")
        print("")
        
        response = input("Do you want to continue? (y/N): ")
        if response.lower() not in ['y', 'yes']:
            print("Operation cancelled")
            return False
        
        # Step 1: Create serverless NEG
        if not self.create_serverless_neg(region, cloud_run_service):
            return False
        
        # Step 2: Create IAP OAuth client
        oauth_client = self.create_iap_oauth_client()
        if not oauth_client:
            return False
        
        # Step 3: Create security policy
        if not self.create_security_policy():
            return False
        
        # Step 4: Create backend service
        if not self.create_backend_service(region, oauth_client):
            return False
        
        # Step 5: Grant IAP access
        if not self.grant_iap_access(backend_name):
            return False
        
        # Step 6: Get Cloud Run URL (if using host rewrite)
        cloud_run_url = None
        if use_host_rewrite:
            cloud_run_url = self.get_cloud_run_url(cloud_run_service, region)
        
        # Step 7: Add path rule to URL map
        if not self.add_path_rule(path, backend_name, cloud_run_url):
            return False
        
        # Update manifest
        self.manifest.update_state("loadbalancer_configured", True)
        self.manifest.update_config("loadbalancer_path", path)
        self.manifest.update_config("loadbalancer_url", f"https://{self.DOMAIN}{path}")
        self.manifest.log_operation("loadbalancer_add", {
            "path": path,
            "backend_name": backend_name,
            "oauth_client": oauth_client["display_name"],
            "domain": self.DOMAIN
        })
        
        print("")
        print("=" * 60)
        print("Load balancer configuration complete!")
        print("=" * 60)
        print("")
        print(f"✓ Your service is now available at:")
        print(f"  https://{self.DOMAIN}{path}")
        print("")
        print(f"✓ Authentication: IAP enabled for {self.IAP_DOMAIN}")
        print(f"✓ Rate limiting: 500 requests per 60 seconds per IP")
        print("")
        
        return True
    
    def remove_from_loadbalancer(self, path: Optional[str] = None, skip_confirmation: bool = False) -> bool:
        """
        Remove the service from the load balancer.
        
        Args:
            path: URL path prefix to remove (default: from manifest or /{project-name})
            skip_confirmation: Skip user confirmation prompt (for automated cleanup)
        """
        path = path or self.manifest.get_config("loadbalancer_path") or f"/{self.config.project_name}"
        backend_name = f"{self.config.project_name}-backend"
        neg_name = f"{self.config.project_name}-neg"
        policy_name = f"default-security-policy-for-backend-service-{backend_name}"
        region = self.manifest.get_config("region") or self.config.default_region
        
        if not skip_confirmation:
            print("")
            print("=" * 60)
            print(f"Removing {self.config.project_name} from Load Balancer")
            print("=" * 60)
            print("")
            print("This will remove:")
            print(f"  - Path rule: {path}/*")
            print(f"  - Backend service: {backend_name}")
            print(f"  - Network Endpoint Group: {neg_name}")
            print(f"  - Security policy: {policy_name}")
            print("")
            
            response = input("Do you want to continue? (yes/N): ")
            if response.lower() != 'yes':
                print("Operation cancelled")
                return False
        
        # Remove path rule from URL map
        try:
            if not skip_confirmation:
                print("")
            print("Removing path rule from URL map...")
            result = subprocess.run([
                "gcloud", "compute", "url-maps", "describe", self.URL_MAP_NAME,
                "--format=json",
                f"--project={self.config.gcp_project_id}"
            ], check=True, capture_output=True, text=True)
            
            url_map = json.loads(result.stdout)
            
            # Remove the path rule
            for matcher in url_map.get("pathMatchers", []):
                if matcher["name"] == "path-matcher-1":
                    if "pathRules" in matcher:
                        matcher["pathRules"] = [
                            rule for rule in matcher["pathRules"]
                            if not any(p.startswith(path) for p in rule.get("paths", []))
                        ]
            
            # Clean up output-only fields
            if "id" in url_map:
                try:
                    url_map["id"] = int(url_map["id"])
                except (ValueError, TypeError):
                    del url_map["id"]
            
            for field in ["creationTimestamp", "selfLink", "fingerprint", "kind"]:
                if field in url_map:
                    del url_map[field]
            
            for matcher in url_map.get("pathMatchers", []):
                for field in ["kind"]:
                    if field in matcher:
                        del matcher[field]
            
            # Write and import updated URL map
            temp_file = "/tmp/url-map-update.json"
            with open(temp_file, 'w') as f:
                json.dump(url_map, f, indent=2)
            
            subprocess.run([
                "gcloud", "compute", "url-maps", "import", self.URL_MAP_NAME,
                f"--source={temp_file}",
                "--quiet",
                f"--project={self.config.gcp_project_id}"
            ], check=True)
            
            print(f"✓ Removed path rule: {path}/*")
            
        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            print(f"Warning: Error removing path rule: {e}")
        
        # Delete backend service
        try:
            print(f"Deleting backend service: {backend_name}")
            subprocess.run([
                "gcloud", "compute", "backend-services", "delete", backend_name,
                "--global",
                "--quiet",
                f"--project={self.config.gcp_project_id}"
            ], check=False)
            print(f"✓ Deleted backend service")
        except subprocess.CalledProcessError:
            pass
        
        # Delete NEG
        try:
            print(f"Deleting NEG: {neg_name}")
            subprocess.run([
                "gcloud", "compute", "network-endpoint-groups", "delete", neg_name,
                f"--region={region}",
                "--quiet",
                f"--project={self.config.gcp_project_id}"
            ], check=False)
            print(f"✓ Deleted NEG")
        except subprocess.CalledProcessError:
            pass
        
        # Delete security policy
        try:
            print(f"Deleting security policy: {policy_name}")
            subprocess.run([
                "gcloud", "compute", "security-policies", "delete", policy_name,
                "--quiet",
                f"--project={self.config.gcp_project_id}"
            ], check=False)
            print(f"✓ Deleted security policy")
        except subprocess.CalledProcessError:
            pass
        
        # Update manifest
        self.manifest.update_state("loadbalancer_configured", False)
        self.manifest.update_config("loadbalancer_path", None)
        self.manifest.update_config("loadbalancer_url", None)
        self.manifest.log_operation("loadbalancer_remove", {
            "path": path,
            "backend_name": backend_name
        })
        
        if not skip_confirmation:
            # Note: We don't delete the OAuth client as it may be referenced elsewhere
            print("")
            print("Note: OAuth client was not deleted (may be referenced by IAM policies)")
            print("")
            print("✓ Load balancer configuration removed")
            print("")
        
        return True

