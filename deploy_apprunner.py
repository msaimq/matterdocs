#!/usr/bin/env python3
"""Deploy MatterDocs to AWS App Runner."""

import boto3
import json
import time
from pathlib import Path

def create_app_runner_service():
    """Create App Runner service."""
    client = boto3.client('apprunner', region_name='us-east-1')
    
    # Create ECR repository first
    ecr = boto3.client('ecr', region_name='us-east-1')
    
    try:
        repo = ecr.create_repository(repositoryName='matterdocs')
        repo_uri = repo['repository']['repositoryUri']
        print(f"✅ Created ECR repository: {repo_uri}")
    except ecr.exceptions.RepositoryAlreadyExistsException:
        repos = ecr.describe_repositories(repositoryNames=['matterdocs'])
        repo_uri = repos['repositories'][0]['repositoryUri']
        print(f"✅ Using existing ECR repository: {repo_uri}")
    
    # App Runner service configuration
    service_config = {
        'ServiceName': 'matterdocs-service',
        'SourceConfiguration': {
            'ImageRepository': {
                'ImageIdentifier': f'{repo_uri}:latest',
                'ImageConfiguration': {
                    'Port': '8000',
                    'RuntimeEnvironmentVariables': {
                        'DATABASE_URL': 'sqlite:///app/matterdocs.db',
                        'STORAGE_ROOT': '/app/storage'
                    }
                },
                'ImageRepositoryType': 'ECR'
            },
            'AutoDeploymentsEnabled': False
        },
        'InstanceConfiguration': {
            'Cpu': '0.25 vCPU',
            'Memory': '0.5 GB'
        }
    }
    
    try:
        response = client.create_service(**service_config)
        service_arn = response['Service']['ServiceArn']
        print(f"✅ Created App Runner service: {service_arn}")
        
        # Wait for service to be running
        print("⏳ Waiting for service to be ready...")
        waiter = client.get_waiter('service_running')
        waiter.wait(ServiceArn=service_arn)
        
        # Get service URL
        service = client.describe_service(ServiceArn=service_arn)
        service_url = service['Service']['ServiceUrl']
        print(f"🚀 Service deployed at: https://{service_url}")
        
        return service_url
        
    except Exception as e:
        print(f"❌ Error creating service: {e}")
        return None

def build_and_push_docker():
    """Build and push Docker image to ECR."""
    import subprocess
    
    # Get ECR login token
    ecr = boto3.client('ecr', region_name='us-east-1')
    token = ecr.get_authorization_token()
    
    username, password = token['authorizationData'][0]['authorizationToken'].encode('utf-8')
    username, password = base64.b64decode(username).decode('utf-8').split(':')
    
    registry = token['authorizationData'][0]['proxyEndpoint']
    
    commands = [
        f"docker build -t matterdocs .",
        f"docker tag matterdocs:latest {registry}/matterdocs:latest",
        f"echo {password} | docker login --username {username} --password-stdin {registry}",
        f"docker push {registry}/matterdocs:latest"
    ]
    
    for cmd in commands:
        print(f"Running: {cmd}")
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Error: {result.stderr}")
            return False
        print(f"✅ {result.stdout}")
    
    return True

if __name__ == "__main__":
    print("🚀 Deploying MatterDocs to AWS App Runner...")
    
    # Build and push Docker image
    if build_and_push_docker():
        # Create App Runner service
        service_url = create_app_runner_service()
        
        if service_url:
            print(f"\n🎉 Deployment successful!")
            print(f"📋 Manifest URL: https://{service_url}/matterdocs-outlook-manifest.xml")
            
            # Update manifest with new URL
            from update_manifest import update_manifest
            update_manifest(f"https://{service_url}")
    else:
        print("❌ Docker build failed")