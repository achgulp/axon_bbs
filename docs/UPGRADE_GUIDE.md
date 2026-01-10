# Axon BBS Upgrade Guide

This document outlines the formal process for upgrading your Axon BBS instance to the latest version. Following this process ensures that both the application code and the database schema remain in sync, preventing crashes and data corruption.

## Guiding Principle

**Do not manually copy files or run individual Django commands to upgrade.** The only supported method for upgrading your instance is by using the `upgrade.sh` script provided in the project's root directory.

This script handles all necessary steps in the correct order:
1.  Fetches the latest source code from the official git repository.
2.  Installs any new or updated Python libraries.
3.  Applies all necessary database schema changes (migrations) safely.

## Standard Upgrade Process

To upgrade your BBS, follow these steps:

1.  **Navigate to your project directory:**
    ```bash
    cd /path/to/your/axon_bbs
    ```

2.  **Ensure the script is executable:**
    You only need to do this once.
    ```bash
    chmod +x upgrade.sh
    ```

3.  **Run the upgrade script:**
    ```bash
    ./upgrade.sh
    ```

4.  **Restart your application server.**
    After the script completes successfully, you must restart the process that serves your BBS. This could be Gunicorn, Daphne, or simply re-running the `runserver` command, depending on your setup.

## For Severely Corrupted Instances (Recovery)

In the rare case that a previous manual upgrade has corrupted your database's migration history (leading to `InconsistentMigrationHistory` errors), you may need to perform a recovery. **This is a last resort and should not be part of the normal process.**

The `AxonBBS_Handoff_10.21.2.txt` memo noted this exact problem occurred on the 'pibbs' instance. The fix is to rebuild the migration history from the current state of the models.

To do this, you would manually run the following commands **instead of** the upgrade script:

1.  Clear the migration history table in your database.
    ```bash
    # WARNING: This is a destructive action for migration history.
    sqlite3 data/axon_bbs.sqlite3 "DELETE FROM django_migrations;"
    ```

2.  Run the migration command with the `--fake-initial` flag. This tells Django to mark all initial migrations as "applied" without actually running them, because the tables already exist.
    ```bash
    python manage.py migrate --fake-initial
    ```

After this recovery, you should be able to use the standard `./upgrade.sh` script for all future updates.
