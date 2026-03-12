# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only

from django.conf import settings
from django.db import models

from .base import BaseModel


class WhatsAppMessage(BaseModel):
    """Log of WhatsApp messages sent/received via Evolution API."""

    class Direction(models.TextChoices):
        OUTBOUND = "OUTBOUND", "Enviado"
        INBOUND = "INBOUND", "Recibido"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pendiente"
        SENT = "SENT", "Enviado"
        DELIVERED = "DELIVERED", "Entregado"
        READ = "READ", "Leído"
        FAILED = "FAILED", "Fallido"

    class MessageType(models.TextChoices):
        TEXT = "TEXT", "Texto"
        REMINDER = "REMINDER", "Recordatorio"
        INFO = "INFO", "Información"
        NOTIFICATION = "NOTIFICATION", "Notificación"

    workspace = models.ForeignKey(
        "db.Workspace",
        on_delete=models.CASCADE,
        related_name="whatsapp_messages",
        null=True,
        blank=True,
    )
    phone = models.CharField(max_length=20)
    contact_name = models.CharField(max_length=200, blank=True)
    direction = models.CharField(
        max_length=10,
        choices=Direction.choices,
        default=Direction.OUTBOUND,
    )
    message_type = models.CharField(
        max_length=20,
        choices=MessageType.choices,
        default=MessageType.TEXT,
    )
    content = models.TextField()
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.PENDING,
    )
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="whatsapp_messages_sent",
    )
    evolution_message_id = models.CharField(max_length=100, blank=True)
    error_detail = models.TextField(blank=True)
    resent_from = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resends",
    )

    class Meta:
        db_table = "whatsapp_messages"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_direction_display()} → {self.phone}: {self.content[:50]}"
