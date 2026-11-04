"use client";

import { useEffect, useState } from "react";
import { History, LoaderCircle, RotateCcw } from "lucide-react";

const API = (process.env.NEXT_PUBLIC_API_URL ?? "").replace(/\/$/, "");
const DAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];
type Assignment = { id: number; lesson_id: number; weekday: number; room_id: number; start_time: string; end_time: string };
type Run = {
  id: number; created_at: string; teacher_name: string | null; teacher_id: number | null;
  restored_at: string | null; changes_count: number;
  metrics: { transition_time_before: number | null; transition_time_after: number | null };
  changes: { before: Assignment; after: Assignment }[];
};
type Props = {
  weekType: string; teacherId: string; revision: number; disabled: boolean;
  rooms: { id: number; name: string }[];
  onBusyChange: (busy: boolean) => void;
  onRestored: () => Promise<void>;
};
const dateLabel = (value: string) => new Date(value).toLocaleString("ru-RU", { timeZone: "Asia/Yekaterinburg" });
const minutes = (value: number | null | undefined) => value == null ? "не рассчитано" : `${value} мин`;

export default function OptimizationHistory({ weekType, teacherId, revision, disabled, rooms, onBusyChange, onRestored }: Props) {
  const [items, setItems] = useState<Run[]>([]);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState<number | null>(null);
  const [confirmation, setConfirmation] = useState<Run | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [reload, setReload] = useState(0);
  const params = new URLSearchParams({ week_type: weekType });
  if (teacherId) params.set("teacher_id", teacherId);
  const scope = params.toString();

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError(""); setItems([]); setConfirmation(null);
    fetch(`${API}/optimization/history?${scope}&offset=${offset}&limit=10`, { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error(`Не удалось загрузить историю: HTTP ${response.status}`);
        return response.json();
      })
      .then((data) => { setItems(data.items); setHasMore(data.has_more); })
      .catch((err) => { if (!controller.signal.aborted) setError(err instanceof Error ? err.message : "Ошибка загрузки истории."); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [scope, revision, offset, reload]);

  async function restore(run: Run, apply: boolean) {
    setWorking(run.id); setError(""); setNotice(""); onBusyChange(true);
    let saved = false;
    try {
      const response = await fetch(`${API}/optimization/history/${run.id}/${apply ? "restore" : "restore-preview"}?${scope}`, { method: apply ? "POST" : "GET" });
      const data = await response.json().catch(() => null);
      if (!response.ok) throw new Error(typeof data?.detail === "string" ? data.detail : `Ошибка восстановления: HTTP ${response.status}`);
      if (apply) {
        saved = true;
        setConfirmation(null);
        setNotice(`Восстановлены прежние назначения для ${data.restored_count} занятий.`);
        setReload((value) => value + 1);
        await onRestored();
      } else {
        setConfirmation(data.run);
      }
    } catch (err) {
      setConfirmation(null);
      setError(saved ? "Восстановление сохранено, но не удалось обновить экран. Обновите страницу." : err instanceof Error ? err.message : "Не удалось восстановить расписание.");
    } finally { setWorking(null); onBusyChange(false); }
  }
  const roomName = (id: number) => rooms.find((room) => room.id === id)?.name ?? `#${id}`;

  return <section className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
    <h2 className="flex items-center gap-2 text-base font-semibold"><History className="h-5 w-5" />История оптимизации</h2>
    <p className="mt-2 text-sm text-slate-500">{weekType === "odd" ? "Нечётная" : "Чётная"} неделя. {teacherId ? "Операции, выполненные отдельно для выбранного преподавателя." : "Операции для всех и отдельных преподавателей."} Время указано по Екатеринбургу.</p>
    <p className="mt-2 text-xs leading-5 text-slate-500">История ведётся с момента включения этой функции. Возврат восстановит только аудитории и время занятий выбранной операции. Изменённые позже записи и варианты, нарушающие текущие ограничения, восстановить нельзя.</p>
    {error && <div role="alert" className="mt-3 rounded-xl bg-red-50 p-3 text-sm text-red-800">{error}<button type="button" disabled={disabled || working !== null} onClick={() => setReload((value) => value + 1)} className="ml-2 underline">Обновить историю</button></div>}
    {notice && <p role="status" className="mt-3 rounded-xl bg-emerald-50 p-3 text-sm text-emerald-800">{notice}</p>}
    {loading ? <p className="mt-4 text-sm text-slate-500">Загрузка истории…</p> : !items.length && !error ? <p className="mt-4 text-sm text-slate-500">Сохранённых оптимизаций для этого выбора пока нет.</p> : <div className="mt-4 space-y-3">
      {items.map((run) => <article key={run.id} className="rounded-xl border border-slate-200 p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div><h3 className="text-sm font-semibold">#{run.id} · {dateLabel(run.created_at)}</h3><p className="mt-1 text-sm">{run.teacher_name ?? (run.teacher_id ? `Преподаватель #${run.teacher_id}` : "Все преподаватели")} · {run.changes_count} изменений</p><p className="mt-1 text-xs text-slate-500">Переходы на момент расчёта: {minutes(run.metrics.transition_time_before)} → {minutes(run.metrics.transition_time_after)}</p></div>
          {run.restored_at ? <p className="text-xs text-slate-500">Отменено {dateLabel(run.restored_at)}</p> : <button type="button" disabled={disabled || working !== null || confirmation !== null} onClick={() => restore(run, false)} className="inline-flex items-center gap-2 rounded-xl border border-slate-300 px-3 py-2 text-sm font-medium disabled:opacity-50">{working === run.id ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <RotateCcw className="h-4 w-4" />}Проверить возврат</button>}
        </div>
        <details className="mt-3 text-sm"><summary className="cursor-pointer text-slate-600">Посмотреть изменения</summary><ul className="mt-2 max-h-64 space-y-2 overflow-y-auto">{run.changes.map(({ before, after }) => <li key={before.id} className="rounded-lg bg-slate-50 p-2">{DAYS[before.weekday]} · занятие #{before.lesson_id}: {before.start_time.slice(0, 5)}–{before.end_time.slice(0, 5)}, {roomName(before.room_id)} → {after.start_time.slice(0, 5)}–{after.end_time.slice(0, 5)}, {roomName(after.room_id)}</li>)}</ul></details>
      </article>)}
    </div>}
    <div className="mt-4 flex flex-wrap gap-3 text-sm">
      {offset > 0 && <button type="button" disabled={disabled || loading || confirmation !== null} onClick={() => setOffset(Math.max(0, offset - 10))} className="rounded-lg border px-3 py-2 disabled:opacity-50">Более новые</button>}
      {hasMore && <button type="button" disabled={disabled || loading || confirmation !== null} onClick={() => setOffset(offset + 10)} className="rounded-lg border px-3 py-2 disabled:opacity-50">Более ранние</button>}
    </div>
    {confirmation && <div role="dialog" aria-modal="true" aria-labelledby="restore-title" className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 p-4"><div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl">
      <h3 id="restore-title" className="text-lg font-semibold">Отменить оптимизацию #{confirmation.id}?</h3>
      <p className="mt-3 text-sm leading-6 text-slate-600">Вернутся прежние аудитории и время для {confirmation.changes_count} занятий {weekType === "odd" ? "нечётной" : "чётной"} недели. Проверка пройдена; перед сохранением сервер выполнит её повторно. Условия преподавателей не изменятся.</p>
      <div className="mt-5 flex flex-wrap justify-end gap-3"><button type="button" disabled={working !== null} onClick={() => setConfirmation(null)} className="rounded-xl border px-4 py-2">Отмена</button><button type="button" disabled={working !== null} onClick={() => restore(confirmation, true)} className="rounded-xl bg-red-700 px-4 py-2 font-medium text-white disabled:opacity-50">{working !== null ? "Восстанавливаем…" : "Восстановить прежние назначения"}</button></div>
    </div></div>}
  </section>;
}
