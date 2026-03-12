# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only

from django.urls import path

from plane.app.views.whatsapp import (
    WhatsAppStatusEndpoint,
    WhatsAppQREndpoint,
    WhatsAppDisconnectEndpoint,
    WhatsAppSendEndpoint,
    WhatsAppMessagesEndpoint,
    WhatsAppResendEndpoint,
    WhatsAppWebhookEndpoint,
)

urlpatterns = [
    path(
        "whatsapp/status/",
        WhatsAppStatusEndpoint.as_view(),
        name="whatsapp-status",
    ),
    path(
        "whatsapp/qr/",
        WhatsAppQREndpoint.as_view(),
        name="whatsapp-qr",
    ),
    path(
        "whatsapp/disconnect/",
        WhatsAppDisconnectEndpoint.as_view(),
        name="whatsapp-disconnect",
    ),
    path(
        "whatsapp/webhook/",
        WhatsAppWebhookEndpoint.as_view(),
        name="whatsapp-webhook",
    ),
    path(
        "workspaces/<str:slug>/whatsapp/send/",
        WhatsAppSendEndpoint.as_view(),
        name="whatsapp-send",
    ),
    path(
        "workspaces/<str:slug>/whatsapp/resend/",
        WhatsAppResendEndpoint.as_view(),
        name="whatsapp-resend",
    ),
    path(
        "workspaces/<str:slug>/whatsapp/messages/",
        WhatsAppMessagesEndpoint.as_view(),
        name="whatsapp-messages",
    ),
]
