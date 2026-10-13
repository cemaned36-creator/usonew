
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  ArrowLeft,
  CalendarDays,
  CheckCircle2,
  Clock3,
  DoorOpen,
  GraduationCap,
  Plus,
  Trash2,
} from "lucide-react";


const API = (process.env.NEXT_PUBLIC_API_URL ?? "").replace(/\/$/, "");


const days = [
  "Понедельник",
  "Вторник",
  "Среда",
  "Четверг",
  "Пятница",
  "Суббота",
  "Воскресенье",
];

type Entry = {
  id: number;
  lesson_id: number;
  weekday: number;
  start_time: string;
  end_time: string;
  room_id: number;
  room_name: string | null;
};

type NamedOption = {
  id: number;
  name: string;
};

type Lesson = {
  id: number;
  teacher_id: number;
  subject_id: number;
  group_id: number;
};

type MessageType = "success" | "error" | "info";

const fieldClass =
  "mt-2 block w-full rounded-xl border border-slate-300 bg-white px-3.5 py-3 text-sm font-medium text-slate-900 outline-none transition placeholder:text-slate-400 hover:border-slate-400 focus:border-slate-900 focus:ring-2 focus:ring-slate-900/10";

const labelClass =
  "block text-sm font-medium text-slate-700";

export default function WeeklySchedulePage() {
  const [entries, setEntries] = useState<Entry[]>([]);
  const [lessons, setLessons] = useState<Lesson[]>([]);
  const [teachers, setTeachers] = useState<NamedOption[]>([]);
  const [subjects, setSubjects] = useState<NamedOption[]>([]);
  const [groups, setGroups] = useState<NamedOption[]>([]);
  const [rooms, setRooms] = useState<NamedOption[]>([]);

  const [lessonId, setLessonId] = useState("");
  const [roomId, setRoomId] = useState("");
  const [weekday, setWeekday] = useState("0");
  const [start, setStart] = useState("08:30");
  const [end, setEnd] = useState("10:00");

  const [message, setMessage] = useState("");
  const [messageType, setMessageType] =
    useState<MessageType>("info");

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  function showMessage(text: string, type: MessageType) {
    setMessage(text);
    setMessageType(type);
  }

  function lessonLabel(id: number) {
    const lesson = lessons.find((item) => item.id === id);

    if (!lesson) {
      return `Занятие #${id}`;
    }

    const subject = subjects.find(
      (item) => item.id === lesson.subject_id
    );
    const teacher = teachers.find(
      (item) => item.id === lesson.teacher_id
    );
    const group = groups.find(
      (item) => item.id === lesson.group_id
    );

    return [
      subject?.name ?? `Предмет #${lesson.subject_id}`,
      teacher?.name ?? `Преподаватель #${lesson.teacher_id}`,
      group?.name ?? `Группа #${lesson.group_id}`,
    ].join(" — ");
  }

  async function loadSchedule() {
    const response = await fetch(`${API}/weekly-schedule/`);

    if (!response.ok) {
      throw new Error("Не удалось загрузить расписание");
    }

    setEntries(await response.json());
  }

  useEffect(() => {
    async function loadData() {
      try {
        const endpoints = [
          "/weekly-schedule/",
          "/lessons/",
          "/rooms/",
          "/teachers/",
          "/subjects/",
          "/student-groups/",
        ];

        const responses = await Promise.all(
          endpoints.map((path) => fetch(`${API}${path}`))
        );

        const failed = responses.find((response) => !response.ok);

        if (failed) {
          throw new Error(
            `Ошибка API: ${failed.status}. Проверь маршруты backend.`
          );
        }

        const [
          scheduleData,
          lessonsData,
          roomsData,
          teachersData,
          subjectsData,
          groupsData,
        ] = await Promise.all(
          responses.map((response) => response.json())
        );

        setEntries(scheduleData);
        setLessons(lessonsData);
        setRooms(roomsData);
        setTeachers(teachersData);
        setSubjects(subjectsData);
        setGroups(groupsData);
      } catch (error) {
        showMessage(
          error instanceof Error
            ? error.message
            : "Ошибка загрузки данных",
          "error"
        );
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, []);

  async function addEntry(
    event: React.FormEvent<HTMLFormElement>
  ) {
    event.preventDefault();
    setMessage("");

    if (!lessonId || !roomId) {
      showMessage("Выбери занятие и аудиторию", "error");
      return;
    }

    if (end <= start) {
      showMessage(
        "Время окончания должно быть позже начала",
        "error"
      );
      return;
    }

    setSaving(true);

    try {
      const response = await fetch(`${API}/weekly-schedule/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          lesson_id: Number(lessonId),
          room_id: Number(roomId),
          weekday: Number(weekday),
          start_time: start,
          end_time: end,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : "Не удалось добавить занятие"
        );
      }

      await loadSchedule();
      showMessage("Занятие успешно добавлено в расписание", "success");
    } catch (error) {
      showMessage(
        error instanceof Error
          ? error.message
          : "Ошибка сохранения",
        "error"
      );
    } finally {
      setSaving(false);
    }
  }

  async function removeEntry(id: number) {
    setDeletingId(id);
    setMessage("");

    try {
      const response = await fetch(
        `${API}/weekly-schedule/${id}`,
        { method: "DELETE" }
      );

      if (!response.ok) {
        const data = await response.json().catch(() => null);
        throw new Error(
          typeof data?.detail === "string"
            ? data.detail
            : "Не удалось удалить запись"
        );
      }

      await loadSchedule();
      showMessage("Занятие удалено из расписания", "success");
    } catch (error) {
      showMessage(
        error instanceof Error ? error.message : "Ошибка удаления",
        "error"
      );
    } finally {
      setDeletingId(null);
    }
  }

  const totalLessons = entries.length;

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#f7f8fa] text-slate-900">
        <div className="flex items-center gap-3 text-sm text-slate-500">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-slate-300 border-t-slate-900" />
          Загрузка недельного расписания...
        </div>
      </main>
    );
  }

  return (
    <div className="min-h-screen bg-[#f7f8fa] text-slate-900">
      <div className="flex min-h-screen">
        {/* Боковая панель */}
        <aside className="hidden w-[250px] shrink-0 flex-col border-r border-slate-200 bg-white lg:flex">
          <Link
            href="/"
            className="flex h-[76px] items-center gap-3 border-b border-slate-200 px-6"
          >
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-900">
              <CalendarDays className="h-5 w-5 text-white" />
            </div>
            <div>
              <div className="text-[15px] font-semibold tracking-tight text-slate-900">
                University
              </div>
              <div className="text-xs text-slate-400">
                Schedule Optimizer
              </div>
            </div>
          </Link>

          <nav className="flex-1 px-3 py-5">
            <p className="mb-3 px-3 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
              Основное
            </p>

            <Link
              href="/"
              className="mb-1 flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-slate-500 transition hover:bg-slate-50 hover:text-slate-900"
            >
              <GraduationCap className="h-[18px] w-[18px] text-slate-400" />
              Dashboard
            </Link>

            <Link
              href="/weekly-schedule"
              aria-current="page"
              className="flex items-center gap-3 rounded-xl bg-slate-900 px-3 py-2.5 text-sm font-medium text-white"
            >
              <CalendarDays className="h-[18px] w-[18px] text-white" />
              Расписание
              <span className="ml-auto h-1.5 w-1.5 rounded-full bg-white" />
            </Link>
          </nav>

          <div className="border-t border-slate-200 p-4">
            <div className="rounded-xl bg-slate-50 p-3">
              <div className="text-sm font-medium text-slate-800">
                University Schedule
              </div>
              <div className="mt-1 text-xs text-slate-400">
                Управление расписанием
              </div>
            </div>
          </div>
        </aside>

        {/* Основная область */}
        <main className="min-w-0 flex-1">
          <header className="flex min-h-[76px] items-center justify-between border-b border-slate-200 bg-white px-5 py-4 sm:px-8">
            <div>
              <div className="flex items-center gap-2">
                <CalendarDays className="h-5 w-5 text-slate-500 lg:hidden" />
                <h1 className="text-xl font-semibold tracking-tight text-slate-900">
                  Недельное расписание
                </h1>
              </div>
              <p className="mt-1 text-sm text-slate-400">
                Управление занятиями и распределением по аудиториям
              </p>
            </div>

            <Link
              href="/"
              className="hidden items-center gap-2 rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm font-medium text-slate-600 transition hover:bg-slate-50 hover:text-slate-900 sm:flex"
            >
              <ArrowLeft className="h-4 w-4" />
              На главную
            </Link>
          </header>

          <div className="space-y-6 px-5 py-6 sm:px-8">
            {/* Краткая статистика */}
            <section className="grid gap-4 sm:grid-cols-2">
              <div className="rounded-2xl border border-slate-200 bg-white p-5">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-sm text-slate-500">
                      Занятий в расписании
                    </p>
                    <p className="mt-2 text-2xl font-semibold tracking-tight text-slate-900">
                      {totalLessons}
                    </p>
                    <p className="mt-1 text-xs text-slate-400">
                      За все дни недели
                    </p>
                  </div>
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-50">
                    <CalendarDays className="h-5 w-5 text-slate-500" />
                  </div>
                </div>
              </div>

              <div className="rounded-2xl border border-slate-200 bg-white p-5">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-sm text-slate-500">
                      Доступно аудиторий
                    </p>
                    <p className="mt-2 text-2xl font-semibold tracking-tight text-slate-900">
                      {rooms.length}
                    </p>
                    <p className="mt-1 text-xs text-slate-400">
                      В базе университета
                    </p>
                  </div>
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-50">
                    <DoorOpen className="h-5 w-5 text-slate-500" />
                  </div>
                </div>
              </div>
            </section>

            {/* Форма добавления */}
            <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
              <div className="flex items-center gap-3 border-b border-slate-200 px-5 py-4 sm:px-6">
                <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-slate-100">
                  <Plus className="h-4 w-4 text-slate-700" />
                </div>
                <div>
                  <h2 className="text-base font-semibold text-slate-900">
                    Добавить занятие
                  </h2>
                  <p className="mt-0.5 text-xs text-slate-400">
                    Выбери занятие, аудиторию и время
                  </p>
                </div>
              </div>

              <form
                onSubmit={addEntry}
                className="grid gap-5 p-5 sm:grid-cols-2 sm:p-6"
              >
                <label className={labelClass}>
                  Занятие
                  <select
                    className={fieldClass}
                    required
                    value={lessonId}
                    onChange={(event) => setLessonId(event.target.value)}
                  >
                    <option value="">Выберите занятие</option>
                    {lessons.map((item) => (
                      <option key={item.id} value={item.id}>
                        {lessonLabel(item.id)}
                      </option>
                    ))}
                  </select>
                  {lessons.length === 0 && (
                    <span className="mt-2 block text-xs text-amber-700">
                      Сначала создай занятие в разделе Lessons.
                    </span>
                  )}
                </label>

                <label className={labelClass}>
                  Аудитория
                  <select
                    className={fieldClass}
                    required
                    value={roomId}
                    onChange={(event) => setRoomId(event.target.value)}
                  >
                    <option value="">Выберите аудиторию</option>
                    {rooms.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.name}
                      </option>
                    ))}
                  </select>
                  {rooms.length === 0 && (
                    <span className="mt-2 block text-xs text-amber-700">
                      В базе пока нет аудиторий.
                    </span>
                  )}
                </label>

                <label className={labelClass}>
                  День недели
                  <select
                    className={fieldClass}
                    value={weekday}
                    onChange={(event) => setWeekday(event.target.value)}
                  >
                    {days.map((day, index) => (
                      <option key={day} value={index}>
                        {day}
                      </option>
                    ))}
                  </select>
                </label>

                <div className="grid grid-cols-2 gap-3">
                  <label className={labelClass}>
                    <span className="flex items-center gap-2">
                      <Clock3 className="h-4 w-4 text-slate-400" />
                      Начало
                    </span>
                    <input
                      type="time"
                      required
                      value={start}
                      onChange={(event) => setStart(event.target.value)}
                      className={fieldClass}
                    />
                  </label>

                  <label className={labelClass}>
                    <span className="flex items-center gap-2">
                      <Clock3 className="h-4 w-4 text-slate-400" />
                      Окончание
                    </span>
                    <input
                      type="time"
                      required
                      value={end}
                      onChange={(event) => setEnd(event.target.value)}
                      className={fieldClass}
                    />
                  </label>
                </div>

                <div className="sm:col-span-2">
                  <button
                    type="submit"
                    disabled={
                      saving || !lessons.length || !rooms.length
                    }
                    className="inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-xl bg-slate-900 px-5 py-3 text-sm font-medium text-white transition hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-900 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
                  >
                    <Plus className="h-4 w-4" />
                    {saving ? "Добавление..." : "Добавить занятие"}
                  </button>
                </div>
              </form>
            </section>

            {/* Сообщения API */}
            {message && (
              <div
                role="status"
                aria-live="polite"
                className={`flex items-start gap-3 rounded-xl border p-4 text-sm ${
                  messageType === "success"
                    ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                    : messageType === "error"
                      ? "border-red-200 bg-red-50 text-red-800"
                      : "border-slate-200 bg-white text-slate-700"
                }`}
              >
                {messageType === "success" ? (
                  <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
                ) : (
                  <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                )}
                <span>{message}</span>
              </div>
            )}

            {/* Расписание по дням */}
            <section>
              <div className="mb-4">
                <h2 className="text-base font-semibold text-slate-900">
                  Занятия по дням недели
                </h2>
                <p className="mt-1 text-xs text-slate-400">
                  Занятия отсортированы по времени начала
                </p>
              </div>

              <div className="space-y-4">
                {days.map((day, index) => {
                  const dayEntries = entries
                    .filter((entry) => entry.weekday === index)
                    .sort((a, b) =>
                      a.start_time.localeCompare(b.start_time)
                    );

                  return (
                    <section
                      key={day}
                      className="overflow-hidden rounded-2xl border border-slate-200 bg-white"
                    >
                      <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
                        <h3 className="text-sm font-semibold text-slate-800">
                          {day}
                        </h3>
                        <span className="rounded-lg bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">
                          {dayEntries.length}{" "}
                          {dayEntries.length === 1
                            ? "занятие"
                            : dayEntries.length >= 2 &&
                                dayEntries.length <= 4
                              ? "занятия"
                              : "занятий"}
                        </span>
                      </div>

                      {dayEntries.length === 0 ? (
                        <div className="flex items-center gap-3 px-5 py-6">
                          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-slate-50">
                            <CalendarDays className="h-4 w-4 text-slate-400" />
                          </div>
                          <p className="text-sm text-slate-500">
                            На этот день занятий нет
                          </p>
                        </div>
                      ) : (
                        <div>
                          {dayEntries.map((entry) => {
                            const roomName =
                              entry.room_name ??
                              rooms.find(
                                (room) => room.id === entry.room_id
                              )?.name ??
                              `Аудитория #${entry.room_id}`;

                            return (
                              <div
                                key={entry.id}
                                className="flex flex-col gap-4 border-b border-slate-100 px-5 py-4 last:border-b-0 sm:flex-row sm:items-center sm:justify-between"
                              >
                                <div className="flex min-w-0 gap-4">
                                  <div className="flex w-[94px] shrink-0 flex-col justify-center rounded-xl bg-slate-50 px-3 py-2">
                                    <span className="text-sm font-semibold tabular-nums text-slate-800">
                                      {entry.start_time}
                                    </span>
                                    <span className="mt-0.5 text-xs tabular-nums text-slate-500">
                                      {entry.end_time}
                                    </span>
                                  </div>

                                  <div className="min-w-0 flex-1 self-center">
                                    <p className="break-words text-sm font-medium leading-5 text-slate-800">
                                      {lessonLabel(entry.lesson_id)}
                                    </p>
                                    <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-slate-500">
                                      <span className="inline-flex items-center gap-1.5 rounded-lg bg-slate-50 px-2 py-1">
                                        <DoorOpen className="h-3.5 w-3.5 text-slate-400" />
                                        {roomName}
                                      </span>
                                      <span className="text-slate-300">·</span>
                                      <span>
                                        ID занятия: {entry.lesson_id}
                                      </span>
                                    </div>
                                  </div>
                                </div>

                                <button
                                  type="button"
                                  onClick={() => removeEntry(entry.id)}
                                  disabled={deletingId === entry.id}
                                  aria-label={`Удалить занятие ${lessonLabel(entry.lesson_id)}`}
                                  className="inline-flex min-h-10 shrink-0 items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-sm font-medium text-slate-600 transition hover:border-red-200 hover:bg-red-50 hover:text-red-700 focus:outline-none focus:ring-2 focus:ring-red-200 disabled:cursor-not-allowed disabled:opacity-50 sm:min-h-9"
                                >
                                  <Trash2 className="h-4 w-4" />
                                  {deletingId === entry.id
                                    ? "Удаление..."
                                    : "Удалить"}
                                </button>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </section>
                  );
                })}
              </div>
            </section>

            <footer className="pb-2 text-center text-xs text-slate-400">
              University Schedule Optimizer
            </footer>
          </div>
        </main>
      </div>
    </div>
  );
}
