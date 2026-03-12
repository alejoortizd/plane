# Generated migration for WhatsAppMessage model

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("db", "0120_issueview_archived_at"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="WhatsAppMessage",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Created At")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Last Modified At")),
                ("id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ("phone", models.CharField(max_length=20)),
                ("contact_name", models.CharField(blank=True, max_length=200)),
                ("direction", models.CharField(choices=[("OUTBOUND", "Enviado"), ("INBOUND", "Recibido")], default="OUTBOUND", max_length=10)),
                ("message_type", models.CharField(choices=[("TEXT", "Texto"), ("REMINDER", "Recordatorio"), ("INFO", "Información"), ("NOTIFICATION", "Notificación")], default="TEXT", max_length=20)),
                ("content", models.TextField()),
                ("status", models.CharField(choices=[("PENDING", "Pendiente"), ("SENT", "Enviado"), ("DELIVERED", "Entregado"), ("READ", "Leído"), ("FAILED", "Fallido")], default="PENDING", max_length=15)),
                ("evolution_message_id", models.CharField(blank=True, max_length=100)),
                ("error_detail", models.TextField(blank=True)),
                ("created_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_created_by", to=settings.AUTH_USER_MODEL, verbose_name="Created By")),
                ("updated_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_updated_by", to=settings.AUTH_USER_MODEL, verbose_name="Last Modified By")),
                ("sent_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="whatsapp_messages_sent", to=settings.AUTH_USER_MODEL)),
                ("workspace", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="whatsapp_messages", to="db.workspace")),
                ("resent_from", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="resends", to="db.whatsappmessage")),
            ],
            options={
                "db_table": "whatsapp_messages",
                "ordering": ["-created_at"],
            },
        ),
    ]
