#!/usr/bin/env python
"""
Deployment setup script for ReportCardApp
Runs all necessary Django management commands for initial setup and deployment.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(command, description):
    """Run a shell command and print status."""
    print(f"\n🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(e.stderr)
        return False

def main():
    """Main setup function."""
    print("🚀 Starting ReportCardApp deployment setup...")

    # Get the project root directory
    project_root = Path(__file__).parent
    os.chdir(project_root)



    # Check if requirements.txt exists
    if not Path('requirements.txt').exists():
        print("❌ requirements.txt not found!")
        return False

    # Install requirements
    if not run_command("pip install -r requirements.txt", "Installing Python requirements"):
        return False

    # Run migrations
    if not run_command("python manage.py migrate", "Running database migrations"):
        return False

    # Ensure staticfiles directory exists
    static_root = project_root / "staticfiles"
    static_root.mkdir(exist_ok=True)

    # Collect static files (clear first to avoid conflicts)
    if not run_command("python manage.py collectstatic --clear --noinput", "Collecting static files"):
        return False

    # Compress static files (for production) - optional if no compress tags
    if not run_command("python manage.py compress", "Compressing static files"):
        print("⚠️  Static file compression failed (possibly no compress tags in templates), continuing...")

    # Create initial backup
    if not run_command("python manage.py backup_db", "Creating initial database backup"):
        print("⚠️  Backup creation failed, but continuing...")

    # Create superuser if it doesn't exist
    print("\n🔄 Checking for superuser...")
    try:
        from django.conf import settings
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
        import django
        django.setup()

        from django.contrib.auth import get_user_model
        User = get_user_model()

        if not User.objects.filter(is_superuser=True).exists():
            print("No superuser found. Creating one...")
            username = input("Enter superuser username: ").strip()
            email = input("Enter superuser email: ").strip()
            password = input("Enter superuser password: ").strip()

            User.objects.create_superuser(username=username, email=email, password=password)
            print("✅ Superuser created successfully")
        else:
            print("✅ Superuser already exists")
    except Exception as e:
        print(f"⚠️  Could not check/create superuser: {e}")

    print("\n🎉 Deployment setup completed successfully!")
    print("\nNext steps:")
    print("1. Configure your web server (e.g., Apache/Nginx or PythonAnywhere)")
    print("2. Set up SSL/HTTPS")
    print("3. Configure ALLOWED_HOSTS in settings.py")
    print("4. Set DEBUG=False in production")
    print("5. Schedule regular backups with: python manage.py backup_db")
    print("6. Start the application server")

    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
