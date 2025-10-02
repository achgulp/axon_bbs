# Full path: axon_bbs/core/management/commands/rename_tables.py
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.utils import OperationalError

class Command(BaseCommand):
    help = "Safely renames database tables after the model refactoring, skipping any that are missing."

    def handle(self, *args, **options):
        # A list of (old_name, new_name) tuples
        tables_to_rename = [
            ('core_alias', 'accounts_alias'),
            ('core_bannedpubkey', 'accounts_bannedpubkey'),
            ('core_ignoredpubkey', 'accounts_ignoredpubkey'),
            ('core_messageboard', 'messaging_messageboard'),
            ('core_message', 'messaging_message'),
            ('core_privatemessage', 'messaging_privatemessage'),
            ('core_appletcategory', 'applets_appletcategory'),
            ('core_applet', 'applets_applet'),
            ('core_appletdata', 'applets_appletdata'),
            ('core_appletsharedstate', 'applets_appletsharedstate'),
            ('core_highscore', 'applets_highscore'),
            ('core_contentextensionrequest', 'federation_contentextensionrequest'),
            ('core_federatedaction', 'federation_federatedaction'),
            ('core_moderationreport', 'federation_moderationreport'),
        ]

        with connection.cursor() as cursor:
            for old_name, new_name in tables_to_rename:
                try:
                    cursor.execute(f"ALTER TABLE {old_name} RENAME TO {new_name};")
                    self.stdout.write(self.style.SUCCESS(f"Successfully renamed '{old_name}' to '{new_name}'."))
                except OperationalError as e:
                    if "no such table" in str(e):
                        self.stdout.write(self.style.WARNING(f"Skipping '{old_name}': Table does not exist (may already be renamed)."))
                    else:
                        self.stdout.write(self.style.ERROR(f"An unexpected database error occurred with '{old_name}': {e}"))
        
        self.stdout.write(self.style.SUCCESS("\nTable renaming process complete."))
