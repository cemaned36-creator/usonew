"use client";

import { useState } from "react";
import { Download, LoaderCircle } from "lucide-react";
import type { OptimizationDetailedReport } from "@/components/OptimizationReport";

const API = (process.env.NEXT_PUBLIC_API_URL ?? "").replace(/\/$/, "");
type Preview = {
  detailed_report?: OptimizationDetailedReport | null;
  warnings: string[];
  constraint_issues: { reason: string }[];
  can_apply: boolean;
};

export default function PdfExportButton({ weekType, teacherId, preview, historyId }: {
  weekType: string;
  teacherId?: number | null;
  preview?: Preview;
  historyId?: number;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function download() {
    setBusy(true); setError("");
    try {
      const params = new URLSearchParams({ week_type: weekType });
      if (teacherId) params.set("teacher_id", String(teacherId));
      const response = historyId != null
        ? await fetch(`${API}/optimization/history/${historyId}/export?${params}`)
        : await fetch(`${API}/optimization/export-preview`, {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ week_type: weekType, teacher_id: teacherId ?? null,
              detailed_report: preview?.detailed_report, warnings: preview?.warnings ?? [],
              constraint_issues: preview?.constraint_issues ?? [], can_apply: preview?.can_apply ?? false }),
          });
      if (!response.ok) {
        const data = await response.json().catch(() => null);
        throw new Error(typeof data?.detail === "string" ? data.detail : "Не удалось скачать PDF. Попробуйте ещё раз.");
      }
      if (!response.headers.get("content-type")?.includes("application/pdf")) throw new Error("Сервер вернул неверный формат отчёта.");
      const url = URL.createObjectURL(await response.blob());
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = historyId != null ? `uso-history-${historyId}-${weekType}.pdf` : `uso-preview-${weekType}-${teacherId ?? "all"}.pdf`;
      document.body.appendChild(anchor); anchor.click(); anchor.remove();
      setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } catch (err) { setError(err instanceof Error ? err.message : "Ошибка экспорта PDF."); }
    finally { setBusy(false); }
  }
  return <div>
    <button type="button" onClick={download} disabled={busy || (historyId == null && !preview?.detailed_report)}
      className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50">
      {busy ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
      {busy ? "Формируем PDF…" : "Скачать отчёт PDF"}
    </button>
    {error && <p role="alert" className="mt-2 text-sm text-red-700">{error}</p>}
  </div>;
}
