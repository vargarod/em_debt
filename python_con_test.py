#!/usr/bin/env python3
"""
Python Environment Test Script
Tests the local Python environment, interpreter setup, and installed packages.
"""

import sys
import os
import platform
from pathlib import Path

def print_section(title):
    """Print a formatted section header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def test_python_version():
    """Display Python version and interpreter information."""
    print_section("Python Interpreter Information")
    print(f"Python Version: {sys.version}")
    print(f"Python Executable: {sys.executable}")
    print(f"Python Path: {sys.prefix}")
    print(f"Base Prefix: {sys.base_prefix}")
    
    # Check if in virtual environment
    in_venv = sys.prefix != sys.base_prefix
    print(f"In Virtual Environment: {in_venv}")

def test_system_info():
    """Display system information."""
    print_section("System Information")
    print(f"OS: {platform.system()} {platform.release()}")
    print(f"Platform: {platform.platform()}")
    print(f"Architecture: {platform.machine()}")
    print(f"Processor: {platform.processor()}")
    print(f"Python Implementation: {platform.python_implementation()}")

def test_path_info():
    """Display Python path information."""
    print_section("Python Path (sys.path)")
    for i, path in enumerate(sys.path, 1):
        print(f"{i}. {path}")

def test_environment_variables():
    """Display relevant environment variables."""
    print_section("Environment Variables")
    env_vars = ['PATH', 'PYTHONPATH', 'VIRTUAL_ENV', 'CONDA_DEFAULT_ENV', 'PYTHONHOME']
    
    for var in env_vars:
        value = os.environ.get(var, 'Not set')
        if var == 'PATH' and value != 'Not set':
            # Display PATH entries on separate lines for readability
            print(f"\n{var}:")
            for path in value.split(os.pathsep)[:5]:  # Show first 5 entries
                print(f"  - {path}")
            if len(value.split(os.pathsep)) > 5:
                print(f"  ... and {len(value.split(os.pathsep)) - 5} more")
        else:
            print(f"{var}: {value}")

def test_installed_packages():
    """List installed packages."""
    print_section("Installed Packages (using pip)")
    try:
        import subprocess
        result = subprocess.run(
            [sys.executable, "-m", "pip", "list"],
            capture_output=True,
            text=True,
            timeout=10
        )
        print(result.stdout)
    except Exception as e:
        print(f"Error listing packages: {e}")
        print("Trying alternative method...")
        try:
            import pkg_resources
            installed_packages = [(d.project_name, d.version) 
                                for d in pkg_resources.working_set]
            installed_packages.sort()
            for name, version in installed_packages:
                print(f"{name}: {version}")
        except Exception as e2:
            print(f"Alternative method also failed: {e2}")

def test_common_imports():
    """Test importing common packages."""
    print_section("Testing Common Package Imports")
    
    common_packages = [
        'os', 'sys', 'json', 'datetime', 'pathlib',
        'numpy', 'pandas', 'matplotlib', 'requests', 
        'flask', 'django', 'pytest', 'sqlalchemy'
    ]
    
    for package in common_packages:
        try:
            __import__(package)
            print(f"✓ {package:20} - Imported successfully")
        except ImportError:
            print(f"✗ {package:20} - Not installed")
        except Exception as e:
            print(f"⚠ {package:20} - Error: {str(e)[:40]}")

def test_pip_info():
    """Display pip information."""
    print_section("Pip Information")
    try:
        import subprocess
        result = subprocess.run(
            [sys.executable, "-m", "pip", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        print(result.stdout.strip())
    except Exception as e:
        print(f"Error getting pip info: {e}")

def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("  PYTHON ENVIRONMENT TEST SUITE")
    print("=" * 60)
    
    test_python_version()
    test_system_info()
    test_pip_info()
    test_path_info()
    test_environment_variables()
    test_installed_packages()
    test_common_imports()
    
    print("\n" + "=" * 60)
    print("  Test Complete!")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()
