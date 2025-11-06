"""
Local development initialization.
"""

import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Tuple

from .config import ProjectConfig
from .manifest import ManifestManager


class InitManager:
    """Manages local development initialization."""
    
    def __init__(self, config: ProjectConfig, manifest: ManifestManager):
        self.config = config
        self.manifest = manifest
        self.is_mac = platform.system() == "Darwin"
    
    def check_command(self, command: str) -> bool:
        """Check if a command is available in PATH."""
        return shutil.which(command) is not None
    
    def check_python_version(self) -> Tuple[bool, str]:
        """Check if Python version is >= 3.10."""
        try:
            version = sys.version_info
            if version.major >= 3 and version.minor >= 10:
                return True, f"{version.major}.{version.minor}.{version.micro}"
            return False, f"{version.major}.{version.minor}.{version.micro}"
        except Exception:
            return False, "unknown"
    
    def install_with_homebrew(self, package: str) -> bool:
        """Install a package using Homebrew (Mac only)."""
        if not self.is_mac:
            return False
        
        if not self.check_command("brew"):
            print(f"  Homebrew not found. Please install Homebrew first:")
            print(f"    /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"")
            return False
        
        try:
            print(f"  Installing {package} with Homebrew...")
            subprocess.run(["brew", "install", package], check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"  Failed to install {package}: {e}")
            return False
    
    def install_uv(self) -> bool:
        """Install uv Python package manager."""
        if self.check_command("uv"):
            return True
        
        print("  uv not found. Attempting to install...")
        
        if self.is_mac:
            # Try Homebrew first
            if self.install_with_homebrew("uv"):
                return True
        
        # Fallback to official installer
        try:
            print("  Installing uv using official installer...")
            result = subprocess.run(
                "curl -LsSf https://astral.sh/uv/install.sh | sh",
                shell=True,
                check=True,
                capture_output=True,
                text=True
            )
            # After installation, check if uv is now available
            # May need to reload PATH, but at least verify installation attempted
            return True
        except subprocess.CalledProcessError as e:
            print(f"  Failed to install uv: {e}")
            print("  Please install uv manually:")
            print("    curl -LsSf https://astral.sh/uv/install.sh | sh")
            return False
    
    def check_and_install_dependencies(self) -> bool:
        """Check for required dependencies and offer to install missing ones."""
        print("Checking dependencies...")
        print("")
        
        missing_required = []
        
        # Check Git
        if not self.check_command("git"):
            missing_required.append(("git", "Git version control", "brew install git"))
        else:
            print("✓ git found")
        
        # Check Python
        python_ok, python_version = self.check_python_version()
        if not python_ok:
            missing_required.append(("python", f"Python >=3.10 (found: {python_version})", "brew install python@3.11"))
        else:
            print(f"✓ Python {python_version} found")
        
        # Check uv
        if not self.check_command("uv"):
            missing_required.append(("uv", "uv Python package manager", "curl -LsSf https://astral.sh/uv/install.sh | sh"))
        else:
            print("✓ uv found")
        
        # Check Node.js/npm
        if not self.check_command("node"):
            missing_required.append(("node", "Node.js", "brew install node"))
        else:
            try:
                node_version = subprocess.run(
                    ["node", "--version"],
                    capture_output=True,
                    text=True,
                    check=True
                ).stdout.strip()
                print(f"✓ Node.js {node_version} found")
            except Exception:
                print("✓ Node.js found")
        
        if not self.check_command("npm"):
            missing_required.append(("npm", "npm package manager", "brew install node"))
        else:
            print("✓ npm found")
        
        print("")
        
        # Handle missing required dependencies
        if missing_required:
            print("⚠️  Missing required dependencies:")
            for cmd, desc, install_cmd in missing_required:
                print(f"  - {cmd}: {desc}")
            print("")
            
            if self.is_mac:
                response = input("Would you like to install missing dependencies automatically? (y/N): ")
                if response.lower() in ['y', 'yes']:
                    for cmd, desc, install_cmd in missing_required:
                        print(f"\nInstalling {cmd}...")
                        if cmd == "uv":
                            if not self.install_uv():
                                print(f"Please install {cmd} manually: {install_cmd}")
                                return False
                        elif cmd == "python":
                            if not self.install_with_homebrew("python@3.11"):
                                print(f"Please install {cmd} manually: {install_cmd}")
                                return False
                        elif cmd == "node":
                            if not self.install_with_homebrew("node"):
                                print(f"Please install {cmd} manually: {install_cmd}")
                                return False
                        elif cmd == "git":
                            if not self.install_with_homebrew("git"):
                                print(f"Please install {cmd} manually: {install_cmd}")
                                return False
                    print("")
                    # Re-check after installation
                    return self.check_and_install_dependencies()
                else:
                    print("Please install the missing dependencies manually:")
                    for cmd, desc, install_cmd in missing_required:
                        print(f"  {install_cmd}")
                    return False
            else:
                print("Please install the missing dependencies manually:")
                for cmd, desc, install_cmd in missing_required:
                    print(f"  {install_cmd}")
                return False
        
        return True
    
    def check_dev_dependencies(self) -> bool:
        """Check for development dependencies (for deployment)."""
        print("Checking development dependencies...")
        print("")
        
        missing_dev = []
        
        if not self.check_command("docker"):
            missing_dev.append(("docker", "Docker", "brew install --cask docker"))
        else:
            print("✓ docker found")
        
        if not self.check_command("colima"):
            missing_dev.append(("colima", "Colima (Docker runtime for Mac)", "brew install colima"))
        else:
            print("✓ colima found")
        
        if not self.check_command("gcloud"):
            missing_dev.append(("gcloud", "Google Cloud SDK", "brew install --cask google-cloud-sdk"))
        else:
            print("✓ gcloud found")
        
        if not self.check_command("gh"):
            missing_dev.append(("gh", "GitHub CLI", "brew install gh"))
        else:
            print("✓ gh found")
        
        print("")
        
        if missing_dev:
            print("ℹ️  Development dependencies not found (needed for deployment):")
            for cmd, desc, install_cmd in missing_dev:
                print(f"  - {cmd}: {desc}")
            print("  You can install these later if needed for deployment.")
            print("")
        
        return True
    
    def update_project_files(self) -> bool:
        """Update project name in configuration files."""
        try:
            print("Updating project name in configuration files...")
            
            # Update pyproject.toml
            if self.config.pyproject_file.exists():
                content = self.config.pyproject_file.read_text()
                content = content.replace(
                    'name = "bff-template"',
                    f'name = "{self.config.project_name}"'
                )
                self.config.pyproject_file.write_text(content)
            
            # Update makefile
            if self.config.makefile.exists():
                content = self.config.makefile.read_text()
                content = content.replace(
                    'name = "bff-template"',
                    f'name = "{self.config.project_name}"'
                )
                self.config.makefile.write_text(content)
            
            print("✓ Configuration files updated")
            return True
        except Exception as e:
            print(f"Error updating project files: {e}")
            return False
    
    def setup_frontend(self, skip_build: bool = False) -> bool:
        """Setup the frontend React application with Vite."""
        try:
            print("Setting up frontend with Vite...")
            
            # Create frontend directory if it doesn't exist
            self.config.frontend_dir.mkdir(parents=True, exist_ok=True)
            
            # Check if frontend is already initialized
            package_json = self.config.frontend_dir / "package.json"
            if package_json.exists():
                print("Frontend already initialized")
                
                if not skip_build:
                    print("Building frontend...")
                    subprocess.run(
                        ["npm", "run", "build"],
                        cwd=self.config.frontend_dir,
                        check=True
                    )
            else:
                # Create package.json with Vite
                print("Creating Vite React app...")
                package_json_content = """{
  "name": "frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.1",
    "vite": "^5.4.2"
  }
}"""
                package_json.write_text(package_json_content)
                
                # Create vite.config.js
                vite_config = self.config.frontend_dir / "vite.config.js"
                vite_config_content = """import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
})
"""
                vite_config.write_text(vite_config_content)
                
                # Set up index.html at root - use existing one if available
                root_index = self.config.frontend_dir / "index.html"
                public_index = self.config.frontend_dir / "init" / "index.html"
                
                if public_index.exists() and not root_index.exists():
                    # Copy the custom index.html from init to root
                    root_index.write_text(public_index.read_text())
                elif not root_index.exists():
                    # Create a default index.html
                    default_index = """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="theme-color" content="#0F172A" />
    <meta name="description" content="Modern web application powered by React" />
    <title>BFF Template</title>
  </head>
  <body>
    <noscript>You need to enable JavaScript to run this app.</noscript>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
"""
                    root_index.write_text(default_index)
                
                # Create src directory and main entry point
                src_dir = self.config.frontend_dir / "src"
                src_dir.mkdir(exist_ok=True)
                
                main_jsx = src_dir / "main.jsx"
                main_jsx_content = """import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
"""
                main_jsx.write_text(main_jsx_content)
                
                # Create a basic App component
                app_jsx = src_dir / "App.jsx"
                app_jsx_content = """function App() {
  return (
    <div>
      <h1>Welcome to React + Vite</h1>
      <p>Your custom index.html is loaded!</p>
    </div>
  )
}

export default App
"""
                app_jsx.write_text(app_jsx_content)
                
                # Install dependencies
                print("Installing dependencies (this may take a few minutes)...")
                subprocess.run(
                    ["npm", "install"],
                    cwd=self.config.frontend_dir,
                    check=True
                )
                
                if not skip_build:
                    print("Building frontend...")
                    subprocess.run(
                        ["npm", "run", "build"],
                        cwd=self.config.frontend_dir,
                        check=True
                    )
            
            print("✓ Frontend setup complete")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error setting up frontend: {e}")
            return False
    
    def setup_backend(self) -> bool:
        """Setup the backend Python dependencies."""
        try:
            print("Setting up backend dependencies...")
            
            # Use uv to sync dependencies
            subprocess.run(["uv", "sync"], cwd=self.config.project_root, check=True)
            
            print("✓ Backend setup complete")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error setting up backend: {e}")
            return False
    
    def initialize(self, skip_frontend_build: bool = False) -> bool:
        """Run full local initialization."""
        print(f"Initializing project: {self.config.project_name}")
        print("")
        
        # Check if already initialized
        if self.manifest.get_state("initialized"):
            print("⚠️  Project is already initialized")
            response = input("Do you want to re-initialize? (y/N): ")
            if response.lower() not in ['y', 'yes']:
                return False
        
        # Check and install dependencies
        if not self.check_and_install_dependencies():
            print("✗ Dependency check failed. Please install missing dependencies and try again.")
            return False
        
        # Create .env file
        self.config.ensure_env_file()
        print("✓ .env file created")
        
        # Update configuration files
        if not self.update_project_files():
            return False
        
        # Setup frontend
        if not self.setup_frontend(skip_build=skip_frontend_build):
            return False
        
        # Setup backend
        if not self.setup_backend():
            return False
        
        # Update manifest
        self.manifest.update_state("initialized", True)
        self.manifest.update_config("project_name", self.config.project_name)
        self.manifest.log_operation("init", {"type": "local"})
        
        print("")
        print("=" * 50)
        print("Local development setup complete!")
        print("=" * 50)
        print("")
        print("Next steps:")
        print(f"  1. Set your Python interpreter to: .venv")
        print(f"  2. Run 'make local' to start the development server")
        print("")
        return True