# Full path: axon_bbs/core/management/commands/create_pibbs_user.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

User = get_user_model()

class Command(BaseCommand):
    help = "Creates the pibbs_user for the UAT."

    def handle(self, *args, **options):
        if not User.objects.filter(username='pibbs_user').exists():
            private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            public_key = private_key.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ).decode('utf-8')
            User.objects.create_user(
                username='pibbs_user',
                password='password',
                nickname='pibbs_user',
                pubkey=public_key,
            )
            self.stdout.write(self.style.SUCCESS("Successfully created pibbs_user."))
        else:
            self.stdout.write(self.style.WARNING("pibbs_user already exists."))
