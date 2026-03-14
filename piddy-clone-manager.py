#!/usr/bin/env python3
"""
Piddy Microservices Cloner & Integrator

Programmatically clone and integrate Piddy microservices into your projects.
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Optional

class PiddyServiceManager:
    """Manage cloning and integration of Piddy microservices."""
    
    REPO = "https://github.com/burchdad/piddy-microservices.git"
    
    SERVICES = {
        'phase1': ['user'],
        'phase2': ['notifications'],
        'phase3': ['auth', 'email', 'sms', 'push', 'gateway'],
        'phase4': ['event-bus', 'notification-hub', 'webhook', 'task-queue', 'secrets'],
        'phase5': ['analytics', 'pipeline', 'messaging', 'payment', 'subscription'],
        'phase6': ['search', 'crm', 'cms', 'storage', 'monitoring'],
        'phase7': ['recommendation', 'document-manager', 'report-builder', 'ml-inference', 'social']
    }
    
    def __init__(self, target_dir: str = "./services"):
        self.target_dir = Path(target_dir)
        self.target_dir.mkdir(parents=True, exist_ok=True)
        self.cloned = []
        self.failed = []
    
    def list_services(self) -> Dict[str, List[str]]:
        """List all available services by phase."""
        return self.SERVICES
    
    def clone_service(self, service_name: str) -> bool:
        """Clone a single service from GitHub."""
        service_path = self.target_dir / service_name
        
        print(f"Cloning service: {service_name}...", end=" ")
        
        try:
            cmd = [
                'git', 'clone',
                '-b', f'service/{service_name}',
                self.REPO,
                str(service_path)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=60
            )
            
            if result.returncode == 0:
                print("✓")
                self.cloned.append(service_name)
                return True
            else:
                print("✗")
                self.failed.append((service_name, result.stderr.decode()))
                return False
                
        except Exception as e:
            print(f"✗ ({str(e)})")
            self.failed.append((service_name, str(e)))
            return False
    
    def clone_services(self, service_names: List[str]) -> Dict[str, bool]:
        """Clone multiple services."""
        results = {}
        for service in service_names:
            results[service] = self.clone_service(service)
        return results
    
    def get_service_info(self, service_name: str) -> Optional[Dict]:
        """Get information about a cloned service."""
        service_path = self.target_dir / service_name
        
        if not service_path.exists():
            return None
        
        # Find routes file
        routes_files = list(service_path.glob("**/routes_*.py"))
        dockerfile = list(service_path.glob("**/Dockerfile"))
        requirements = list(service_path.glob("**/requirements-*.txt"))
        
        return {
            'name': service_name,
            'path': str(service_path),
            'routes': str(routes_files[0]) if routes_files else None,
            'dockerfile': str(dockerfile[0]) if dockerfile else None,
            'requirements': str(requirements[0]) if requirements else None,
        }
    
    def create_integration_module(self) -> bool:
        """Create an integrate.py module for easy service mounting."""
        
        if not self.cloned:
            return False
        
        integration_file = self.target_dir / "integrate.py"
        
        with open(integration_file, 'w') as f:
            f.write('''"""
Piddy Microservices Integration Module

Auto-generated module for integrating cloned services.
"""

import sys
from pathlib import Path

# Add services directory to path
services_dir = Path(__file__).parent
sys.path.insert(0, str(services_dir))

services = {}

''')
            
            # Add imports
            for service in self.cloned:
                service_path = self.target_dir / service
                
                # Find the phase directory and routes file
                phase_dirs = list(service_path.glob("enhanced-api-phase*"))
                if phase_dirs:
                    phase_dir = phase_dirs[0]
                    routes_files = list(phase_dir.glob("routes_*.py"))
                    
                    if routes_files:
                        routes_file = routes_files[0]
                        module_name = routes_file.stem
                        phase_name = phase_dir.name
                        
                        import_line = f'''try:
    from {service}.{phase_name}.{module_name} import app as {service}_app
    services['{service}'] = {service}_app
except ImportError as e:
    print(f"Warning: Could not import {service}: {{e}}")

'''
                        f.write(import_line)
            
            # Add integration function
            f.write('''

def integrate_services(app, prefix="/api"):
    """
    Mount all cloned services to a FastAPI application.
    
    Args:
        app: FastAPI application instance
        prefix: URL prefix for all service endpoints (default: "/api")
    
    Example:
        from fastapi import FastAPI
        from services.integrate import integrate_services
        
        app = FastAPI()
        integrate_services(app)
        
        # All services now available at /api/{service_name}/*
    """
    for service_name, service_app in services.items():
        if hasattr(service_app, 'router'):
            app.include_router(
                service_app.router,
                prefix=f"{prefix}/{service_name}",
                tags=[service_name]
            )
            print(f"✓ Mounted {service_name} service at {prefix}/{service_name}")


def get_services():
    """Get list of available services."""
    return list(services.keys())


if __name__ == "__main__":
    print("Piddy Microservices Integration Module")
    print(f"Available services: {get_services()}")
''')
        
        print(f"✓ Created integration module: {integration_file}")
        return True
    
    def create_requirements_file(self) -> bool:
        """Combine requirements from all cloned services."""
        
        if not self.cloned:
            return False
        
        requirements_file = self.target_dir / "requirements-combined.txt"
        all_requirements = set()
        
        for service in self.cloned:
            service_path = self.target_dir / service
            req_files = list(service_path.glob("**/requirements-*.txt"))
            
            for req_file in req_files:
                with open(req_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            all_requirements.add(line)
        
        if all_requirements:
            with open(requirements_file, 'w') as f:
                f.write("# Combined requirements for Piddy microservices\n")
                f.write("# Generated automatically\n\n")
                for req in sorted(all_requirements):
                    f.write(f"{req}\n")
            
            print(f"✓ Created combined requirements: {requirements_file}")
            print(f"  ({len(all_requirements)} unique dependencies)")
            return True
        
        return False
    
    def create_docker_compose(self) -> bool:
        """Generate a docker-compose.yml for all cloned services."""
        
        if not self.cloned:
            return False
        
        compose_file = self.target_dir / "docker-compose.yml"
        
        compose = {
            'version': '3.8',
            'services': {
                'postgres': {
                    'image': 'postgres:16-alpine',
                    'environment': {
                        'POSTGRES_USER': 'piddy_user',
                        'POSTGRES_PASSWORD': 'piddy_password',
                        'POSTGRES_DB': 'piddy_db'
                    },
                    'ports': ['5432:5432'],
                    'healthcheck': {
                        'test': ['CMD-SHELL', 'pg_isready -U piddy_user'],
                        'interval': '10s',
                        'timeout': '5s',
                        'retries': 5
                    }
                },
                'redis': {
                    'image': 'redis:7-alpine',
                    'ports': ['6379:6379'],
                    'healthcheck': {
                        'test': ['CMD', 'redis-cli', 'ping'],
                        'interval': '10s',
                        'timeout': '5s',
                        'retries': 5
                    }
                }
            }
        }
        
        # Add service configurations
        port = 8001
        for service in sorted(self.cloned):
            service_info = self.get_service_info(service)
            if service_info:
                compose['services'][service] = {
                    'build': service_info['path'],
                    'ports': [f'{port}:8000'],
                    'environment': {
                        'DATABASE_URL': 'postgresql://piddy_user:piddy_password@postgres:5432/piddy_db',
                        'REDIS_URL': 'redis://redis:6379'
                    },
                    'depends_on': {
                        'postgres': {'condition': 'service_healthy'},
                        'redis': {'condition': 'service_healthy'}
                    },
                    'networks': ['piddy-network']
                }
                port += 1
        
        # Add volumes and networks
        compose['volumes'] = {'postgres_data': None}
        compose['networks'] = {'piddy-network': {'driver': 'bridge'}}
        
        with open(compose_file, 'w') as f:
            import yaml
            yaml.dump(compose, f, default_flow_style=False)
        
        print(f"✓ Created docker-compose.yml")
        return True
    
    def print_summary(self):
        """Print summary of cloning operation."""
        print("\n" + "="*50)
        print("Integration Summary")
        print("="*50)
        
        print(f"\n✓ Successfully cloned: {len(self.cloned)}")
        for service in self.cloned:
            print(f"  • {service}")
        
        if self.failed:
            print(f"\n✗ Failed to clone: {len(self.failed)}")
            for service, error in self.failed:
                print(f"  • {service}: {error}")
        
        if self.cloned:
            print("\nNext steps:")
            print(f"  1. cd {self.target_dir}")
            print(f"  2. pip install -r requirements-combined.txt")
            print(f"  3. from integrate import integrate_services")
            print(f"  4. integrate_services(app)")
            print("\nYou can also use Docker Compose:")
            print(f"  docker-compose up -d")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Clone and integrate Piddy microservices"
    )
    parser.add_argument(
        'services',
        nargs='*',
        help='Service names to clone (or "all" for all services)'
    )
    parser.add_argument(
        '-d', '--directory',
        default='./services',
        help='Target directory (default: ./services)'
    )
    parser.add_argument(
        '-l', '--list',
        action='store_true',
        help='List all available services'
    )
    
    args = parser.parse_args()
    
    manager = PiddyServiceManager(args.directory)
    
    # List services if requested
    if args.list:
        print("Available Piddy Microservices:\n")
        for phase, services in manager.list_services().items():
            print(f"{phase}: {', '.join(services)}")
        return
    
    # Determine services to clone
    if not args.services:
        parser.print_help()
        return
    
    services_to_clone = []
    if 'all' in args.services:
        for phase_services in manager.list_services().values():
            services_to_clone.extend(phase_services)
    else:
        services_to_clone = args.services
    
    # Clone services
    print(f"Cloning {len(services_to_clone)} service(s) to {args.directory}\n")
    manager.clone_services(services_to_clone)
    
    # Create helpers
    if manager.cloned:
        print("\nGenerating integration files...")
        manager.create_integration_module()
        manager.create_requirements_file()
        
        # Try to create docker-compose (requires PyYAML)
        try:
            manager.create_docker_compose()
        except ImportError:
            print("  (install PyYAML to generate docker-compose.yml)")
    
    # Print summary
    manager.print_summary()


if __name__ == "__main__":
    main()
