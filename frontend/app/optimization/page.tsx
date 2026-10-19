"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import BrandLogo from "@/components/BrandLogo";
import {
  AlertCircle,
  ArrowRight,
  CalendarDays,
  CheckCircle2,
  Clock3,
  DoorOpen,
  GraduationCap,
  LoaderCircle,
  ShieldCheck,
  Sparkles,
  Users,
  X,
} from "lucide-react";

const API = (process.env.NEXT_PUBLIC_API_URL ?? "").replace(/\/$/, "");
const DAYS = [
  "Понедельник",
  "Вторник",
  "Среда",
  "Четверг",
  "Пятница",
  "Суббота",
  "Воскресенье",
];

type ScheduleEntry = {
  id: number;
  lesson_id: number;
  weekday: number;
  start_time: string;
  end_time: string;
  room_id: number;
  room_name: string | null;
  teacher_id?: number | null;
  subject_id?: number | null;
  group_id?: number | null;
};

type NamedOption = { id: number; name: string };
type Lesson = {
  id: number;
  teacher_id: number;
  subject_id: number;
  group_id: number;
};
type Change = {
  entry_id: number;
  lesson_id: number;
  weekday: number;
  start_time: string;
  end_time: string;
  old_room_id: number;
  old_room_name: string;
  new_room_id: number;
  new_room_name: string;
};
type UnknownRoute = {
  previous_entry_id: number;
  current_entry_id: number;
  reason: string;
};
type OptimizationResult = {
  changes: Change[];
  changes_count: number;
  transition_time_before: number | null;
  transition_time_after: number | null;
  time_saved: number | null;
  unknown_routes: UnknownRoute[];
  saved_to_database: boolean;
};

type Message = { kind: "success" | "error" | "info"; text: string };

export default function OptimizationPage() {
  const [entries, setEntries] = useState<ScheduleEntry[]>([]);
  const [lessons, setLessons] = useState<Lesson[]>([]);
  const [rooms, setRooms] = useState<NamedOption[]>([]);
  const [teachers, setTeachers] = useState<NamedOption[]>([]);
  const [subjects, setSubjects] = useState<NamedOption[]>([]);
  const [groups, setGroups] = useState<NamedOption[]>([]);
  const [result, setResult] = useState<OptimizationResult | null>(null);
  const [loadingData, setLoadingData] = useState(true);
  const [running, setRunning] = useState(false);
  const [saving, setSaving] = useState(false);
  const [confirmStep, setConfirmStep] = useState<0 | 1 | 2>(0);
  const [message, setMessage] = useState<Message | null>(null);
  const [teacherAccess, setTeacherAccess] = useState(false);
  const [selectedWeekType, setSelectedWeekType] = useState("odd");

  useEffect(() => {
    try {
      const savedProfile = localStorage.getItem("uso-user-profile");
      if (savedProfile && JSON.parse(savedProfile)?.role === "teacher") {
        setTeacherAccess(true);
      }
    } catch {
      // Ignore malformed local profile; dashboard will request a new selection.
    }
  }, []);

  const loadData = useCallback(async () => {
    if (!API) throw new Error("Не задан NEXT_PUBLIC_API_URL для frontend.");
    const paths = [
      "/weekly-schedule/",
      "/lessons/",
      "/rooms/",
      "/teachers/",
      "/subjects/",
      "/student-groups/",
    ];
    const responses = await Promise.all(paths.map((path) => fetch(`${API}${path}`)));
    const failed = responses.find((response) => !response.ok);
    if (failed) throw new Error(`Не удалось загрузить данные: HTTP ${failed.status}`);
    const [scheduleData, lessonData, roomData, teacherData, subjectData, groupData] =
      await Promise.all(responses.map((response) => response.json()));
    setEntries(scheduleData);
    setLessons(lessonData);
    setRooms(roomData);
    setTeachers(teacherData);
    setSubjects(subjectData);
    setGroups(groupData);
  }, []);

  useEffect(() => {
    loadData()
      .catch((error) =>
        setMessage({
          kind: "error",
          text: error instanceof Error ? error.message : "Не удалось загрузить расписание.",
        })
      )
      .finally(() => setLoadingData(false));
  }, [loadData]);

  const lessonById = useMemo(() => new Map(lessons.map((item) => [item.id, item])), [lessons]);
  const roomById = useMemo(() => new Map(rooms.map((item) => [item.id, item])), [rooms]);
  const teacherById = useMemo(() => new Map(teachers.map((item) => [item.id, item.name])), [teachers]);
  const subjectById = useMemo(() => new Map(subjects.map((item) => [item.id, item.name])), [subjects]);
  const groupById = useMemo(() => new Map(groups.map((item) => [item.id, item.name])), [groups]);
  const changesByEntry = useMemo(
    () => new Map((result?.changes ?? []).map((item) => [item.entry_id, item])),
    [result]
  );

  const displayEntries = useMemo(() => {
    return entries.map((entry) => {
      const change = changesByEntry.get(entry.id);
      return {
        ...entry,
        displayRoomId: change ? change.new_room_id : entry.room_id,
        displayRoomName: change ? change.new_room_name : entry.room_name,
      };
    });
  }, [entries, changesByEntry]);

  async function runOptimizationPreview() {
    setRunning(true);
    setMessage(null);
    setConfirmStep(0);
    try {
      const response = await fetch(`${API}/optimization/preview?week_type=${selectedWeekType}`);
      const data = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(
          typeof data?.detail === "string" ? data.detail : `Ошибка API: HTTP ${response.status}`
        );
      }
      setResult(data as OptimizationResult);
      setMessage({
        kind: "success",
        text: data.changes_count
          ? `Расчёт завершён. Предлагается изменить аудиторий: ${data.changes_count}.`
          : "Расчёт завершён: изменения аудиторий не требуются.",
      });
    } catch (error) {
      setResult(null);
      setMessage({
        kind: "error",
        text: error instanceof Error ? error.message : "Не удалось выполнить оптимизацию.",
      });
    } finally {
      setRunning(false);
    }
  }

  async function applyOptimization() {
    if (!result || result.changes.length === 0) return;
    setSaving(true);
    setMessage(null);
    try {
      const response = await fetch(`${API}/optimization/apply`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          week_type: selectedWeekType,
          changes: result.changes.map((change) => ({
            entry_id: change.entry_id,
            old_room_id: change.old_room_id,
            new_room_id: change.new_room_id,
          })),
        }),
      });
      const data = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(
          typeof data?.detail === "string"
            ? data.detail
            : `Не удалось сохранить изменения: HTTP ${response.status}`
        );
      }
      await loadData();
      setResult(null);
      setConfirmStep(0);
      setMessage({
        kind: "success",
        text: `Расписание сохранено в базе данных. Изменено аудиторий: ${data.saved_count}.`,
      });
    } catch (error) {
      setConfirmStep(0);
      setMessage({
        kind: "error",
        text: error instanceof Error ? error.message : "Ошибка сохранения оптимизации.",
      });
    } finally {
      setSaving(false);
    }
  }

  function lessonDetails(entry: ScheduleEntry) {
    const lesson = lessonById.get(entry.lesson_id);
    if (!lesson) return { subject: `Занятие #${entry.lesson_id}`, teacher: "Преподаватель не найден", group: "Группа не найдена" };
    return {
      subject: subjectById.get(lesson.subject_id) ?? `Предмет #${lesson.subject_id}`,
      teacher: teacherById.get(lesson.teacher_id) ?? `Преподаватель #${lesson.teacher_id}`,
      group: groupById.get(lesson.group_id) ?? `Группа #${lesson.group_id}`,
    };
  }

  function renderScheduleColumn(optimized: boolean) {
    const items = optimized ? displayEntries : entries;
    return (
      <div className="min-w-0 overflow-hidden rounded-2xl border border-slate-200 bg-white">
        <div className="flex items-center gap-3 border-b border-slate-200 px-5 py-4">
          <div className={`flex h-10 w-10 items-center justify-center rounded-xl ${optimized ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-600"}`}>
            {optimized ? <Sparkles className="h-5 w-5" /> : <CalendarDays className="h-5 w-5" />}
          </div>
          <div>
            <h2 className="font-semibold">{optimized ? "После оптимизации" : "Текущее расписание"}</h2>
            <p className="mt-0.5 text-xs text-slate-400">
              {optimized ? "Предлагаемые аудитории" : "Существующие назначения"}
            </p>
          </div>
        </div>
        <div className="space-y-4 p-3 sm:p-4">
          {DAYS.map((day, dayIndex) => {
            const dayEntries = items
              .filter((entry) => entry.weekday === dayIndex)
              .sort((a, b) => a.start_time.localeCompare(b.start_time));
            return (
              <section key={day} className="overflow-hidden rounded-xl border border-slate-100">
                <div className="flex items-center justify-between bg-slate-50 px-3 py-2.5">
                  <h3 className="text-sm font-semibold text-slate-700">{day}</h3>
                  <span className="text-xs text-slate-400">{dayEntries.length} занятий</span>
                </div>
                {dayEntries.length === 0 ? (
                  <p className="px-3 py-4 text-xs text-slate-400">Занятий нет</p>
                ) : (
                  <div className="divide-y divide-slate-100">
                    {dayEntries.map((entry) => {
                      const change = changesByEntry.get(entry.id);
                      const details = lessonDetails(entry);
                      const highlighted = optimized && Boolean(change);
                      const roomName = optimized
                        ? (entry as ScheduleEntry & { displayRoomName?: string | null }).displayRoomName
                        : entry.room_name;
                      return (
                        <div
                          key={entry.id}
                          className={`grid grid-cols-[68px_minmax(0,1fr)] gap-3 px-3 py-3 ${highlighted ? "bg-emerald-50 ring-1 ring-inset ring-emerald-200" : ""}`}
                        >
                          <div className="pt-0.5">
                            <div className="text-xs font-semibold text-slate-800">{entry.start_time}</div>
                            <div className="mt-0.5 text-[11px] text-slate-400">{entry.end_time}</div>
                          </div>
                          <div className="min-w-0">
                            <div className="break-words text-sm font-medium text-slate-800">{details.subject}</div>
                            <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-slate-500">
                              <span className="inline-flex items-center gap-1"><GraduationCap className="h-3.5 w-3.5" />{details.teacher}</span>
                              <span className="text-slate-300">•</span>
                              <span className="inline-flex items-center gap-1"><Users className="h-3.5 w-3.5" />{details.group}</span>
                            </div>
                            <div className="mt-2 flex flex-wrap items-center gap-2">
                              <span className={`inline-flex items-center gap-1.5 rounded-lg px-2 py-1 text-xs font-semibold ${highlighted ? "bg-emerald-100 text-emerald-800" : "bg-slate-100 text-slate-700"}`}>
                                <DoorOpen className="h-3.5 w-3.5" />
                                Аудитория {roomName ?? roomById.get(entry.room_id)?.name ?? "—"}
                              </span>
                              {highlighted && change && (
                                <span className="text-[11px] font-medium text-emerald-700">
                                  <ArrowRight className="mr-1 inline h-3 w-3" />
                                  {change.old_room_name} → {change.new_room_name}
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </section>
            );
          })}
        </div>
      </div>
    );
  }

  if (teacherAccess) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#f7f8fa] p-6">
        <div className="max-w-md rounded-2xl border border-slate-200 bg-white p-7 text-center shadow-sm">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-slate-100">
            <CalendarDays className="h-6 w-6 text-slate-600" />
          </div>
          <h1 className="mt-4 text-lg font-semibold text-slate-900">Раздел доступен только администратору</h1>
          <p className="mt-2 text-sm leading-6 text-slate-500">В режиме преподавателя доступен только просмотр недельного расписания.</p>
          <Link href="/weekly-schedule" className="mt-5 inline-flex rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-slate-800">Открыть расписание</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#f7f8fa] text-slate-900">
      <div className="flex min-h-screen">
        <aside className="hidden w-[250px] shrink-0 flex-col border-r border-slate-200 bg-white lg:flex">
          <BrandLogo />
          <nav className="flex-1 px-3 py-5">
            <p className="mb-3 px-3 text-[11px] font-semibold uppercase tracking-wider text-slate-400">Основное</p>
            <Link href="/" className="mb-1 flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-slate-500 transition hover:bg-slate-50 hover:text-slate-900">
              <GraduationCap className="h-[18px] w-[18px] text-emerald-600" />Главная страница
            </Link>
            <Link href="/weekly-schedule" className="mb-1 flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-slate-500 transition hover:bg-slate-50 hover:text-slate-900">
              <CalendarDays className="h-[18px] w-[18px] text-emerald-600" />Расписание
            </Link>
            <Link href="/teachers" className="mb-1 flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-slate-500 transition hover:bg-slate-50 hover:text-slate-900">
              <GraduationCap className="h-[18px] w-[18px] text-emerald-600" />Преподаватели
            </Link>
            <Link href="/optimization" aria-current="page" className="flex items-center gap-3 rounded-xl bg-slate-900 px-3 py-2.5 text-sm font-medium text-white">
              <Sparkles className="h-[18px] w-[18px] text-emerald-600" />Оптимизация
              <span className="ml-auto h-1.5 w-1.5 rounded-full bg-white" />
            </Link>
          </nav>
          <div className="border-t border-slate-200 p-4">
            <div className="rounded-xl bg-slate-50 p-3">
              <div className="text-sm font-medium text-slate-800">Расписание УрГУПС</div>
              <div className="mt-1 text-xs text-slate-400">Управление расписанием</div>
            </div>
          </div>
        </aside>

        <main className="min-w-0 flex-1">
          <header className="flex min-h-[76px] items-center justify-between border-b border-slate-200 bg-white px-5 py-4 sm:px-8">
            <div>
              <h1 className="text-xl font-semibold tracking-tight">Оптимизация расписания</h1>
              <p className="mt-1 text-sm text-slate-400">Сравнение текущих аудиторий с предлагаемыми изменениями</p>
            </div>
            <div className="hidden items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs text-slate-500 sm:flex">
              <ShieldCheck className="h-4 w-4" />Предварительный просмотр до подтверждения
            </div>
          </header>

          <div className="space-y-6 px-4 py-6 sm:px-8">
            <section className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
              <div className="mb-5 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div><h2 className="text-base font-semibold">Неделя расписания</h2><p className="mt-1 text-sm text-slate-500">Выбери чётность недели — только её занятия будут оптимизированы.</p></div>
                <div className="inline-flex rounded-xl border border-slate-200 bg-slate-50 p-1">
                  <button type="button" onClick={() => { setSelectedWeekType("odd"); setResult(null); setMessage(null); }} aria-pressed={selectedWeekType === "odd"} className="rounded-lg px-4 py-2.5 text-sm font-semibold transition">Нечётная</button>
                  <button type="button" onClick={() => { setSelectedWeekType("even"); setResult(null); setMessage(null); }} aria-pressed={selectedWeekType === "even"} className="rounded-lg px-4 py-2.5 text-sm font-semibold transition">Чётная</button>
                </div>
              </div>
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <h2 className="text-base font-semibold">Запуск оптимизации — {selectedWeekType === "odd" ? "нечётная неделя" : "чётная неделя"}</h2>
                  <p className="mt-1 max-w-2xl text-sm leading-6 text-slate-500">
                    Система подберёт подходящие аудитории и сравнит время переходов преподавателей.
                    База данных не изменится, пока ты не подтвердишь результат дважды.
                  </p>
                </div>
                <button
                  onClick={runOptimizationPreview}
                  disabled={running || loadingData || saving}
                  className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl bg-slate-900 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {running ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                  {running ? "Выполняется расчёт…" : "Запустить оптимизацию"}
                </button>
              </div>
            </section>

            {message && (
              <div role={message.kind === "error" ? "alert" : "status"} className={`flex items-start gap-3 rounded-xl border p-4 text-sm ${message.kind === "success" ? "border-emerald-200 bg-emerald-50 text-emerald-800" : message.kind === "error" ? "border-red-200 bg-red-50 text-red-800" : "border-slate-200 bg-white text-slate-700"}`}>
                {message.kind === "success" ? <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" /> : <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />}
                <span>{message.text}</span>
              </div>
            )}

            {loadingData ? (
              <div className="flex items-center justify-center gap-3 rounded-2xl border border-slate-200 bg-white p-12 text-sm text-slate-500">
                <LoaderCircle className="h-5 w-5 animate-spin" />Загрузка расписания…
              </div>
            ) : (
              <>
                <div className="grid items-start gap-5 2xl:grid-cols-2">
                  {renderScheduleColumn(false)}
                  {renderScheduleColumn(Boolean(result))}
                </div>

                {result && (
                  <>
                    <section className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
                      <div className="mb-5 flex items-center gap-3">
                        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-100">
                          <Clock3 className="h-5 w-5 text-slate-600" />
                        </div>
                        <div>
                          <h2 className="font-semibold">Время на перемещения</h2>
                          <p className="mt-0.5 text-xs text-slate-400">Суммарное время переходов между последовательными занятиями преподавателей</p>
                        </div>
                      </div>
                      <div className="grid gap-3 sm:grid-cols-3">
                        <MetricCard label="До оптимизации" value={result.transition_time_before == null ? "Не рассчитано" : `${result.transition_time_before} мин`} />
                        <MetricCard label="После оптимизации" value={result.transition_time_after == null ? "Не рассчитано" : `${result.transition_time_after} мин`} />
                        <MetricCard label="Экономия" value={result.time_saved == null ? "—" : `${result.time_saved} мин`} highlight />
                      </div>
                      <div className="mt-4 flex flex-wrap gap-3 text-sm">
                        <span className="rounded-lg bg-slate-100 px-3 py-2 text-slate-700">Изменений: <strong>{result.changes_count}</strong></span>
                        <span className={`rounded-lg px-3 py-2 ${result.unknown_routes.length ? "bg-amber-50 text-amber-800" : "bg-emerald-50 text-emerald-800"}`}>
                          Предупреждений о переходах: <strong>{result.unknown_routes.length}</strong>
                        </span>
                      </div>
                      {result.unknown_routes.length > 0 && (
                        <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-4">
                          <h3 className="text-sm font-semibold text-amber-900">Требуют внимания</h3>
                          <ul className="mt-2 space-y-2 text-sm text-amber-800">
                            {result.unknown_routes.map((route) => (
                              <li key={`${route.previous_entry_id}-${route.current_entry_id}`}>
                                Занятия #{route.previous_entry_id} → #{route.current_entry_id}: {route.reason}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </section>

                    <section className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
                      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                        <div>
                          <h2 className="font-semibold">Применить изменения</h2>
                          <p className="mt-1 max-w-2xl text-sm leading-6 text-slate-500">
                            Сохранение изменит аудитории в базе данных. Перед записью сервер повторно проверит актуальность плана и ограничения расписания.
                          </p>
                        </div>
                        <button
                          onClick={() => setConfirmStep(1)}
                          disabled={!result.changes.length || result.unknown_routes.length > 0 || saving}
                          className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl bg-emerald-700 px-5 py-3 text-sm font-semibold text-white transition hover:bg-emerald-800 disabled:cursor-not-allowed disabled:opacity-40"
                        >
                          <ShieldCheck className="h-4 w-4" />
                          Подтвердить изменения
                        </button>
                      </div>
                      {!result.changes.length && <p className="mt-3 text-sm text-slate-500">Нет изменений для сохранения.</p>}
                      {result.unknown_routes.length > 0 && <p className="mt-3 text-sm text-amber-700">Сохранение отключено, пока есть предупреждения о переходах.</p>}
                    </section>
                  </>
                )}
              </>
            )}
          </div>
        </main>
      </div>

      {confirmStep > 0 && result && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 p-4" role="presentation">
          <div role="dialog" aria-modal="true" aria-labelledby="confirm-title" className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-2xl">
            <div className="flex items-start justify-between gap-4">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-amber-50 text-amber-700">
                <ShieldCheck className="h-5 w-5" />
              </div>
              <button onClick={() => setConfirmStep(0)} disabled={saving} aria-label="Закрыть подтверждение" className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-700 disabled:opacity-50">
                <X className="h-5 w-5" />
              </button>
            </div>
            {confirmStep === 1 ? (
              <>
                <h2 id="confirm-title" className="mt-4 text-lg font-semibold">Проверить изменения?</h2>
                <p className="mt-2 text-sm leading-6 text-slate-500">
                  Будет изменено назначение аудитории для {result.changes.length} занятий. Это пока первый этап подтверждения; данные ещё не сохранены.
                </p>
                <div className="mt-4 max-h-48 space-y-2 overflow-y-auto rounded-xl bg-slate-50 p-3">
                  {result.changes.map((change) => (
                    <div key={change.entry_id} className="flex items-start justify-between gap-3 text-sm">
                      <span className="text-slate-600">Занятие #{change.lesson_id}, {change.start_time}</span>
                      <span className="shrink-0 font-semibold text-emerald-700">{change.old_room_name} → {change.new_room_name}</span>
                    </div>
                  ))}
                </div>
                <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
                  <button onClick={() => setConfirmStep(0)} className="rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50">Отмена</button>
                  <button onClick={() => setConfirmStep(2)} className="rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white hover:bg-slate-800">Продолжить</button>
                </div>
              </>
            ) : (
              <>
                <h2 id="confirm-title" className="mt-4 text-lg font-semibold">Окончательно сохранить расписание?</h2>
                <p className="mt-2 text-sm leading-6 text-slate-600">
                  Это действие запишет новые аудитории в базу данных. Сервер проверит, что расписание не изменилось с момента расчёта. Продолжить?
                </p>
                <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
                  <button onClick={() => setConfirmStep(0)} disabled={saving} className="rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50">Нет, отменить</button>
                  <button onClick={applyOptimization} disabled={saving} className="inline-flex items-center justify-center gap-2 rounded-xl bg-red-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-red-800 disabled:opacity-50">
                    {saving && <LoaderCircle className="h-4 w-4 animate-spin" />}
                    {saving ? "Сохраняем…" : "Да, сохранить в базе"}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function MetricCard({ label, value, highlight = false }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className={`rounded-xl border p-4 ${highlight ? "border-emerald-200 bg-emerald-50" : "border-slate-200 bg-white"}`}>
      <div className="text-xs font-medium text-slate-500">{label}</div>
      <div className={`mt-2 text-2xl font-semibold tracking-tight ${highlight ? "text-emerald-700" : "text-slate-900"}`}>{value}</div>
    </div>
  );
}
