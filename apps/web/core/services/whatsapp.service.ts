import { API_BASE_URL } from "@plane/constants";

import { APIService } from "./api.service";

export interface IWhatsAppMessage {
  id: string;
  phone: string;
  contact_name: string;
  direction: "OUTBOUND" | "INBOUND";
  direction_display: string;
  message_type: "TEXT" | "REMINDER" | "INFO" | "NOTIFICATION";
  message_type_display: string;
  content: string;
  status: "PENDING" | "SENT" | "DELIVERED" | "READ" | "FAILED";
  status_display: string;
  sent_by: string | null;
  sent_by_name: string | null;
  evolution_message_id: string;
  error_detail: string;
  resent_from: string | null;
  is_resend: boolean;
  has_been_resent: boolean;
  created_at: string;
}

export interface IConnectionStatus {
  state: "open" | "close" | "connecting" | "error";
  instance?: string;
  detail?: string;
}

export interface IQRCodeResponse {
  base64?: string;
  code?: string;
  pairingCode?: string;
}

export interface ISendResult {
  sent: number;
  failed: number;
  errors: Array<{ phone: string; error: string }>;
}

class WhatsAppService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async getStatus(): Promise<IConnectionStatus> {
    return this.get("/api/whatsapp/status/")
      .then((res) => res.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  async getQR(): Promise<IQRCodeResponse> {
    return this.get("/api/whatsapp/qr/")
      .then((res) => res.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  async disconnect(): Promise<void> {
    return this.post("/api/whatsapp/disconnect/")
      .then((res) => res.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  async sendMessage(
    workspaceSlug: string,
    payload: {
      phone: string;
      message: string;
      contact_name?: string;
      message_type?: string;
    }
  ): Promise<IWhatsAppMessage> {
    return this.post(`/api/workspaces/${workspaceSlug}/whatsapp/send/`, payload)
      .then((res) => res.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  async resendMessages(workspaceSlug: string, messageIds: string[]): Promise<ISendResult> {
    return this.post(`/api/workspaces/${workspaceSlug}/whatsapp/resend/`, {
      message_ids: messageIds,
    })
      .then((res) => res.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  async getMessages(
    workspaceSlug: string,
    params?: {
      phone?: string;
      type?: string;
      direction?: string;
      status?: string;
    }
  ): Promise<IWhatsAppMessage[]> {
    return this.get(`/api/workspaces/${workspaceSlug}/whatsapp/messages/`, { params })
      .then((res) => res.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }
}

export const whatsAppService = new WhatsAppService();
