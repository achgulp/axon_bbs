# Migration to convert AppletSharedState from applet-based to room-based
from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('applets', '0003_alter_applet_parameters'),
    ]

    operations = [
        # Drop and recreate the table with new schema
        migrations.DeleteModel(
            name='AppletSharedState',
        ),
        migrations.CreateModel(
            name='AppletSharedState',
            fields=[
                ('id', models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ('applet_id', models.CharField(max_length=100, db_index=True, default='', help_text='The applet instance ID (for backward compatibility)')),
                ('room_id', models.CharField(max_length=100, unique=True, db_index=True, default='', help_text='The shared room ID (allows multiple applet instances to share state)')),
                ('state_data', models.JSONField(default=dict)),
                ('version', models.PositiveIntegerField(default=0)),
                ('last_updated', models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
