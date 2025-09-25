# Full path: axon_bbs/core/management/commands/rename_tables.py
from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = "Renames the database tables after the model refactoring."

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            cursor.execute("ALTER TABLE core_alias RENAME TO accounts_alias;")
            cursor.execute("ALTER TABLE core_bannedpubkey RENAME TO accounts_bannedpubkey;")
            cursor.execute("ALTER TABLE core_ignoredpubkey RENAME TO accounts_ignoredpubkey;")
            cursor.execute("ALTER TABLE core_messageboard RENAME TO messaging_messageboard;")
            cursor.execute("ALTER TABLE core_message RENAME TO messaging_message;")
            cursor.execute("ALTER TABLE core_privatemessage RENAME TO messaging_privatemessage;")
            cursor.execute("ALTER TABLE core_appletcategory RENAME TO applets_appletcategory;")
            cursor.execute("ALTER TABLE core_applet RENAME TO applets_applet;")
            cursor.execute("ALTER TABLE core_appletdata RENAME TO applets_appletdata;")
            cursor.execute("ALTER TABLE core_appletsharedstate RENAME TO applets_appletsharedstate;")
            cursor.execute("ALTER TABLE core_highscore RENAME TO applets_highscore;")
            cursor.execute("ALTER TABLE core_contentextensionrequest RENAME TO federation_contentextensionrequest;")
            cursor.execute("ALTER TABLE core_federatedaction RENAME TO federation_federatedaction;")
            cursor.execute("ALTER TABLE core_moderationreport RENAME TO federation_moderationreport;")
        self.stdout.write(self.style.SUCCESS("Successfully renamed database tables."))
