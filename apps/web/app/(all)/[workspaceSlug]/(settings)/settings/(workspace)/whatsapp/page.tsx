"use client";

import { useEffect, useState, useCallback } from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
// plane imports
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { Input } from "@plane/ui";
// services
import { whatsAppService, type IWhatsAppMessage, type IConnectionStatus } from "@/services/whatsapp.service";

const MESSAGE_TYPES = [
  { value: "TEXT", label: "Texto" },
  { value: "REMINDER", label: "Recordatorio" },
  { value: "INFO", label: "Información" },
  { value: "NOTIFICATION", label: "Notificación" },
];

const STATUS_COLORS: Record<string, string> = {
  SENT: "bg-green-500/15 text-green-600 border-green-500/20",
  DELIVERED: "bg-blue-500/15 text-blue-600 border-blue-500/20",
  READ: "bg-slate-500/15 text-slate-600 border-slate-500/20",
  PENDING: "bg-yellow-500/15 text-yellow-600 border-yellow-500/20",
  FAILED: "bg-red-500/15 text-red-600 border-red-500/20",
};

function StatusBadge({ status, label }: { status: string; label: string }) {
  const cls = STATUS_COLORS[status] || "bg-slate-500/15 text-slate-600";
  return (
    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-11 font-medium ${cls}`}>
      {label}
    </span>
  );
}

function formatDate(iso: string) {
  try {
    return new Date(iso).toLocaleString("es-CO", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

const WhatsAppSettingsPage = observer(function WhatsAppSettingsPage() {
  const { workspaceSlug } = useParams<{ workspaceSlug: string }>();

  // Connection
  const [connState, setConnState] = useState<IConnectionStatus | null>(null);
  const [connLoading, setConnLoading] = useState(false);
  const [qrData, setQrData] = useState<string | null>(null);
  const [showQR, setShowQR] = useState(false);

  // Send
  const [sendPhone, setSendPhone] = useState("");
  const [sendMessage, setSendMessage] = useState("");
  const [sendType, setSendType] = useState("TEXT");
  const [sendContactName, setSendContactName] = useState("");
  const [sending, setSending] = useState(false);

  // Messages
  const [messages, setMessages] = useState<IWhatsAppMessage[]>([]);
  const [msgsLoading, setMsgsLoading] = useState(false);
  const [filterPhone, setFilterPhone] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const [filterDirection, setFilterDirection] = useState("");
  const [selectedFailed, setSelectedFailed] = useState<Set<string>>(new Set());

  const fetchStatus = useCallback(async () => {
    setConnLoading(true);
    try {
      const s = await whatsAppService.getStatus();
      setConnState(s);
    } catch {
      setConnState({ state: "error", detail: "No se pudo conectar" });
    } finally {
      setConnLoading(false);
    }
  }, []);

  const fetchMessages = useCallback(async () => {
    if (!workspaceSlug) return;
    setMsgsLoading(true);
    try {
      const params: Record<string, string> = {};
      if (filterPhone) params.phone = filterPhone;
      if (filterStatus) params.status = filterStatus;
      if (filterDirection) params.direction = filterDirection;
      const msgs = await whatsAppService.getMessages(workspaceSlug, params);
      setMessages(msgs);
    } catch {
      setToast({ type: TOAST_TYPE.ERROR, title: "Error", message: "No se pudieron cargar los mensajes" });
    } finally {
      setMsgsLoading(false);
    }
  }, [workspaceSlug, filterPhone, filterStatus, filterDirection]);

  useEffect(() => {
    fetchStatus();
    fetchMessages();
  }, [fetchStatus, fetchMessages]);

  const handleConnect = async () => {
    try {
      const res = await whatsAppService.getQR();
      if (res.base64) {
        setQrData(res.base64);
        setShowQR(true);
      } else if (res.code) {
        setQrData(res.code);
        setShowQR(true);
      } else {
        await fetchStatus();
        setToast({ type: TOAST_TYPE.SUCCESS, title: "Conectado", message: "WhatsApp ya está conectado" });
      }
    } catch {
      setToast({ type: TOAST_TYPE.ERROR, title: "Error", message: "No se pudo obtener el QR" });
    }
  };

  const handleDisconnect = async () => {
    try {
      await whatsAppService.disconnect();
      await fetchStatus();
      setToast({ type: TOAST_TYPE.SUCCESS, title: "Desconectado", message: "WhatsApp desconectado" });
    } catch {
      setToast({ type: TOAST_TYPE.ERROR, title: "Error", message: "No se pudo desconectar" });
    }
  };

  const handleSend = async () => {
    if (!sendPhone || !sendMessage || !workspaceSlug) return;
    setSending(true);
    try {
      await whatsAppService.sendMessage(workspaceSlug, {
        phone: sendPhone.replace(/[^0-9+]/g, ""),
        message: sendMessage,
        contact_name: sendContactName,
        message_type: sendType,
      });
      setToast({ type: TOAST_TYPE.SUCCESS, title: "Enviado", message: "Mensaje enviado correctamente" });
      setSendPhone("");
      setSendMessage("");
      setSendContactName("");
      fetchMessages();
    } catch {
      setToast({ type: TOAST_TYPE.ERROR, title: "Error", message: "No se pudo enviar el mensaje" });
    } finally {
      setSending(false);
    }
  };

  const handleResend = async () => {
    if (selectedFailed.size === 0 || !workspaceSlug) return;
    try {
      const result = await whatsAppService.resendMessages(workspaceSlug, Array.from(selectedFailed));
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: "Reenviados",
        message: `${result.sent} enviados, ${result.failed} fallidos`,
      });
      setSelectedFailed(new Set());
      fetchMessages();
    } catch {
      setToast({ type: TOAST_TYPE.ERROR, title: "Error", message: "No se pudieron reenviar los mensajes" });
    }
  };

  const toggleFailedSelection = (id: string) => {
    setSelectedFailed((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const isConnected = connState?.state === "open";
  const failedMessages = messages.filter((m) => m.status === "FAILED" && !m.has_been_resent);

  return (
    <div className="w-full overflow-y-auto px-6 py-8">
      <div className="mx-auto max-w-4xl space-y-8">
        {/* Header */}
        <div>
          <h2 className="text-21 font-semibold text-primary">WhatsApp</h2>
          <p className="mt-1 text-13 text-tertiary">
            Gestiona la conexión de WhatsApp y revisa el historial de mensajes enviados.
          </p>
        </div>

        {/* Connection Status */}
        <div className="border-primary/10 rounded-lg border p-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div
                className={`h-3 w-3 rounded-full ${
                  isConnected
                    ? "bg-green-500"
                    : connState?.state === "connecting"
                      ? "bg-yellow-500 animate-pulse"
                      : "bg-red-500"
                }`}
              />
              <div>
                <h3 className="text-16 font-medium text-primary">Estado de conexión</h3>
                <p className="text-13 text-tertiary">
                  {isConnected
                    ? `Conectado — instancia: ${connState?.instance || "—"}`
                    : connState?.state === "connecting"
                      ? "Conectando..."
                      : "Desconectado"}
                </p>
              </div>
            </div>
            <div className="flex gap-2">
              <Button variant="neutral-primary" size="sm" onClick={fetchStatus} disabled={connLoading}>
                {connLoading ? "Verificando..." : "Verificar"}
              </Button>
              {isConnected ? (
                <Button variant="error-outline" size="sm" onClick={handleDisconnect}>
                  Desconectar
                </Button>
              ) : (
                <Button variant="primary" size="sm" onClick={handleConnect}>
                  Conectar / QR
                </Button>
              )}
            </div>
          </div>
        </div>

        {/* QR Modal */}
        {showQR && qrData && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
            <div className="shadow-xl rounded-lg bg-surface-1 p-8">
              <h3 className="mb-4 text-16 font-semibold text-primary">Escanea el código QR</h3>
              {qrData.startsWith("data:") || qrData.startsWith("http") ? (
                <img src={qrData} alt="QR Code" className="mx-auto h-64 w-64" />
              ) : (
                <div className="mx-auto flex h-64 w-64 items-center justify-center rounded-lg bg-surface-2 text-13 text-tertiary">
                  <pre className="overflow-auto text-10">{qrData}</pre>
                </div>
              )}
              <div className="mt-4 flex justify-end gap-2">
                <Button
                  variant="neutral-primary"
                  size="sm"
                  onClick={() => {
                    setShowQR(false);
                    setQrData(null);
                    fetchStatus();
                  }}
                >
                  Cerrar
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Send Message */}
        <div className="border-primary/10 rounded-lg border p-5">
          <h3 className="mb-4 text-16 font-medium text-primary">Enviar mensaje</h3>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="flex flex-col gap-1">
              <label htmlFor="wa-phone" className="text-13 font-medium text-secondary">
                Teléfono
              </label>
              <Input
                id="wa-phone"
                type="tel"
                placeholder="+573001234567"
                value={sendPhone}
                onChange={(e) => setSendPhone(e.target.value)}
                className="w-full"
              />
            </div>
            <div className="flex flex-col gap-1">
              <label htmlFor="wa-contact" className="text-13 font-medium text-secondary">
                Nombre contacto
              </label>
              <Input
                id="wa-contact"
                type="text"
                placeholder="Nombre (opcional)"
                value={sendContactName}
                onChange={(e) => setSendContactName(e.target.value)}
                className="w-full"
              />
            </div>
            <div className="flex flex-col gap-1 sm:col-span-2">
              <label htmlFor="wa-type" className="text-13 font-medium text-secondary">
                Tipo
              </label>
              <select
                id="wa-type"
                value={sendType}
                onChange={(e) => setSendType(e.target.value)}
                className="border-primary/10 rounded-md border bg-transparent px-3 py-2 text-13 text-primary outline-none"
              >
                {MESSAGE_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex flex-col gap-1 sm:col-span-2">
              <label htmlFor="wa-message" className="text-13 font-medium text-secondary">
                Mensaje
              </label>
              <textarea
                id="wa-message"
                rows={3}
                placeholder="Escribe tu mensaje..."
                value={sendMessage}
                onChange={(e) => setSendMessage(e.target.value)}
                className="border-primary/10 w-full rounded-md border bg-transparent px-3 py-2 text-13 text-primary outline-none"
              />
            </div>
            <div className="sm:col-span-2">
              <Button
                variant="primary"
                size="sm"
                onClick={handleSend}
                loading={sending}
                disabled={!sendPhone || !sendMessage || !isConnected}
              >
                {sending ? "Enviando..." : "Enviar"}
              </Button>
              {!isConnected && (
                <span className="ml-3 text-11 text-tertiary">WhatsApp debe estar conectado para enviar</span>
              )}
            </div>
          </div>
        </div>

        {/* Failed Messages Resend */}
        {failedMessages.length > 0 && (
          <div className="border-red-500/20 bg-red-500/5 rounded-lg border p-5">
            <div className="flex items-center justify-between">
              <h3 className="text-16 font-medium text-primary">Mensajes fallidos ({failedMessages.length})</h3>
              {selectedFailed.size > 0 && (
                <Button variant="primary" size="sm" onClick={handleResend}>
                  Reenviar seleccionados ({selectedFailed.size})
                </Button>
              )}
            </div>
            <div className="mt-3 max-h-48 space-y-1 overflow-y-auto">
              {failedMessages.map((m) => (
                <label
                  key={m.id}
                  className="flex cursor-pointer items-center gap-2 rounded p-1 text-13 hover:bg-surface-2"
                >
                  <input
                    type="checkbox"
                    checked={selectedFailed.has(m.id)}
                    onChange={() => toggleFailedSelection(m.id)}
                    className="rounded"
                  />
                  <span className="text-secondary">{m.phone}</span>
                  <span className="truncate text-tertiary">{m.content.slice(0, 60)}…</span>
                  <span className="ml-auto text-11 text-tertiary">{formatDate(m.created_at)}</span>
                </label>
              ))}
            </div>
          </div>
        )}

        {/* Message History */}
        <div className="border-primary/10 rounded-lg border p-5">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-16 font-medium text-primary">Historial de mensajes</h3>
            <Button variant="neutral-primary" size="sm" onClick={fetchMessages} disabled={msgsLoading}>
              {msgsLoading ? "Cargando..." : "Actualizar"}
            </Button>
          </div>

          {/* Filters */}
          <div className="mb-4 flex flex-wrap gap-3">
            <Input
              type="text"
              placeholder="Buscar por teléfono..."
              value={filterPhone}
              onChange={(e) => setFilterPhone(e.target.value)}
              className="w-48"
            />
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="border-primary/10 rounded-md border bg-transparent px-3 py-1.5 text-13 text-primary outline-none"
            >
              <option value="">Todos los estados</option>
              <option value="SENT">Enviado</option>
              <option value="DELIVERED">Entregado</option>
              <option value="READ">Leído</option>
              <option value="PENDING">Pendiente</option>
              <option value="FAILED">Fallido</option>
            </select>
            <select
              value={filterDirection}
              onChange={(e) => setFilterDirection(e.target.value)}
              className="border-primary/10 rounded-md border bg-transparent px-3 py-1.5 text-13 text-primary outline-none"
            >
              <option value="">Todas las direcciones</option>
              <option value="OUTBOUND">Enviados</option>
              <option value="INBOUND">Recibidos</option>
            </select>
          </div>

          {/* Table */}
          {messages.length === 0 ? (
            <p className="py-8 text-center text-13 text-tertiary">
              {msgsLoading ? "Cargando mensajes..." : "No hay mensajes para mostrar"}
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-13">
                <thead>
                  <tr className="border-primary/10 border-b text-left text-tertiary">
                    <th className="px-2 py-2 font-medium">Fecha</th>
                    <th className="px-2 py-2 font-medium">Teléfono</th>
                    <th className="px-2 py-2 font-medium">Contacto</th>
                    <th className="px-2 py-2 font-medium">Dir.</th>
                    <th className="px-2 py-2 font-medium">Tipo</th>
                    <th className="px-2 py-2 font-medium">Mensaje</th>
                    <th className="px-2 py-2 font-medium">Estado</th>
                    <th className="px-2 py-2 font-medium">Enviado por</th>
                  </tr>
                </thead>
                <tbody>
                  {messages.map((m) => (
                    <tr key={m.id} className="border-primary/5 border-b hover:bg-surface-2">
                      <td className="px-2 py-2 whitespace-nowrap text-tertiary">{formatDate(m.created_at)}</td>
                      <td className="px-2 py-2 whitespace-nowrap text-secondary">{m.phone}</td>
                      <td className="px-2 py-2 text-secondary">{m.contact_name || "—"}</td>
                      <td className="px-2 py-2">
                        <span className={m.direction === "OUTBOUND" ? "text-blue-600" : "text-green-600"}>
                          {m.direction === "OUTBOUND" ? "↑" : "↓"}
                        </span>
                      </td>
                      <td className="px-2 py-2 text-tertiary">{m.message_type_display}</td>
                      <td className="max-w-xs truncate px-2 py-2 text-secondary" title={m.content}>
                        {m.content.slice(0, 80)}
                        {m.content.length > 80 ? "…" : ""}
                      </td>
                      <td className="px-2 py-2">
                        <StatusBadge status={m.status} label={m.status_display} />
                        {m.is_resend && <span className="ml-1 text-10 text-tertiary">(reenvío)</span>}
                        {m.has_been_resent && <span className="ml-1 text-10 text-tertiary">(reenviado)</span>}
                      </td>
                      <td className="px-2 py-2 text-tertiary">{m.sent_by_name || "Sistema"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
});

export default WhatsAppSettingsPage;
