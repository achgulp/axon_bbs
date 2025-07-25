# axon_bbs/manage.py
#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

# --- Application Version ---
APP_VERSION = "8.4.0"

def main():
    """Run administrative tasks."""
    if os.environ.get('RUN_MAIN') != 'true':
        print(f"--- Axon BBS Management Utility v{APP_VERSION} ---")
    
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'axon_project.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
           "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc

    # Custom message for runserver command
    if 'runserver' in sys.argv and os.environ.get('RUN_MAIN') == 'true':  # Only in the child process
        print("Starting development server at http://127.0.0.1:8000/")
    
    print("Admin site available at http://127.0.0.1:8000/admin/")

    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
