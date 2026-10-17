
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
  Sparkles,
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
  const [selectedTeacherId, setSelectedTeacherId] = useState("");
  const [teacherSearch, setTeacherSearch] = useState("");
  const [showTeacherSuggestions, setShowTeacherSuggestions] = useState(false);
  const [profileRole, setProfileRole] = useState<"admin" | "teacher">("admin");
  const [profileLoaded, setProfileLoaded] = useState(false);
  const [profileTeacherName, setProfileTeacherName] = useState("");
  const [subjects, setSubjects] = useState<NamedOption[]>([]);
  const [groups, setGroups] = useState<NamedOption[]>([]);
  const [rooms, setRooms] = useState<NamedOption[]>([]);
  const lessonPairs = [
    { number: 1, start: "08:30", end: "10:05", label: "1-я пара (08:00–10:05)" },
    { number: 2, start: "10:15", end: "11:50", label: "2-я пара (10:15–11:50)" },
    { number: 3, start: "12:00", end: "13:35", label: "3-я пара (12:00–13:35)" },
    { number: 4, start: "14:30", end: "16:05", label: "4-я пара (14:30–16:05)" },
    { number: 5, start: "16:15", end: "17:50", label: "5-я пара (16:15–17:50)" },
    { number: 6, start: "18:00", end: "19:35", label: "6-я пара (18:00–19:35)" },
  ];

  const getLessonPair = (startTime: string, endTime: string) =>
  lessonPairs.find(
    (pair) => pair.start === startTime && pair.end === endTime
  );

  const [importFile, setImportFile] = useState<File | null>(null);
  const [importPreview, setImportPreview] = useState<any>(null);
  const [importing, setImporting] = useState(false);
  const [previewing, setPreviewing] = useState(false);

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
    try {
      const savedProfile = localStorage.getItem("uso-user-profile");
      if (savedProfile) {
        const profile = JSON.parse(savedProfile);
        if (profile.role === "teacher" && profile.teacherId) {
          setProfileRole("teacher");
          setProfileTeacherName(profile.name ?? "");
          setSelectedTeacherId(String(profile.teacherId));
          setTeacherSearch(profile.name ?? "");
        } else {
          setProfileRole("admin");
        }
      }
    } catch {
      localStorage.removeItem("uso-user-profile");
    } finally {
      setProfileLoaded(true);
    }
  }, []);

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

  
  async function readApiResponse(response: Response) {
    const data = await response.json().catch(() => null);

    if (!response.ok) {
      const detail = data?.detail;
      const message =
        typeof detail === "string"
          ? detail
          : detail?.message ??
            (typeof data?.message === "string" ? data.message : null) ??
            `Ошибка API: ${response.status}`;

      throw new Error(message);
    }

    return data;
  }

  async function previewImport() {
    if (!importFile) {
      showMessage("Сначала выбери Excel-файл (.xlsx)", "error");
      return;
    }

    setPreviewing(true);
    setImportPreview(null);
    setMessage("");

    try {
      const formData = new FormData();
      formData.append("file", importFile);

      const response = await fetch(
        `${API}/weekly-schedule/import/preview`,
        {
          method: "POST",
          body: formData,
        }
      );

      const data = await readApiResponse(response);
      setImportPreview(data);

      if (data.can_import) {
        showMessage(
          `Проверка завершена: готово к импорту ${data.ready_rows} занятий.`,
          "success"
        );
      } else {
        showMessage(
          `Проверка завершена. Готово: ${data.ready_rows} из ${data.total_rows}. Исправь ошибки перед импортом.`,
          "error"
        );
      }
    } catch (error) {
      showMessage(
        error instanceof Error ? error.message : "Не удалось проверить файл",
        "error"
      );
    } finally {
      setPreviewing(false);
    }
  }

  async function importSchedule() {
    if (!importFile || !importPreview?.can_import) {
      showMessage("Сначала выбери и проверь Excel-файл", "error");
      return;
    }

    setImporting(true);
    setMessage("");

    try {
      const formData = new FormData();
      formData.append("file", importFile);

      const response = await fetch(
        "https://usonew.onrender.com/weekly-schedule/import",
        {
          method: "POST",
          body: formData,
        }
      );

      const data = await readApiResponse(response);

      await loadSchedule();

      setImportPreview(null);
      setImportFile(null);

      const fileInput = document.getElementById(
        "weekly-schedule-import-file"
      ) as HTMLInputElement | null;

      if (fileInput) {
        fileInput.value = "";
      }

      showMessage(
        `Импорт завершён: сохранено занятий — ${data.imported_count}.`,
        "success"
      );
    } catch (error) {
      showMessage(
        error instanceof Error ? error.message : "Ошибка импорта расписания",
        "error"
      );
    } finally {
      setImporting(false);
    }
  }


  const filteredEntries = entries.filter((entry) => {
    if (selectedTeacherId === "") {
      return true;
    }

    const lesson = lessons.find(
      (item) => item.id === entry.lesson_id
    );

    return (
      lesson?.teacher_id === Number(selectedTeacherId)
    );
  });

  const totalLessons = filteredEntries.length;

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

  const filteredTeachers = teachers.filter((teacher) =>
    teacher.name
      .toLowerCase()
      .includes(teacherSearch.trim().toLowerCase())
  );
  
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

{profileRole === "admin" && (
              <Link
                href="/optimization"
                className="mt-1 flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-slate-500 transition hover:bg-slate-50 hover:text-slate-900"
              >
                <Sparkles className="h-[18px] w-[18px] text-slate-400" />
                Оптимизация
              </Link>
            )}
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
{profileRole === "teacher" ? `Расписание преподавателя: ${profileTeacherName}` : "Управление занятиями и распределением по аудиториям"}
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
            {profileRole === "admin" && (
              <>
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

            
                      </>
            )}

            {profileRole === "admin" && (
              <>
{/* Импорт Excel */}
        <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
          <div className="border-b border-slate-200 px-5 py-4 sm:px-6">
            <h2 className="text-base font-semibold text-slate-900">
              Импорт расписания из Excel
            </h2>
            <p className="mt-1 text-xs text-slate-400">
              Загрузи файл с листом «Данные для импорта»
            </p>
          </div>

          <div className="space-y-4 p-5 sm:p-6">
            <label className={labelClass}>
              Excel-файл (.xlsx)
              <input
                id="weekly-schedule-import-file"
                type="file"
                accept=".xlsx"
                className={fieldClass}
                onChange={(event) => {
                  const file = event.target.files?.[0] ?? null;
                  setImportFile(file);
                  setImportPreview(null);
                  setMessage("");
                }}
              />
            </label>

            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                onClick={previewImport}
                disabled={!importFile || previewing || importing}
                className="inline-flex min-h-11 items-center justify-center rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {previewing ? "Проверка..." : "Проверить файл"}
              </button>

              <button
                type="button"
                onClick={importSchedule}
                disabled={
                  !importFile ||
                  !importPreview?.can_import ||
                  importing ||
                  previewing
                }
                className="inline-flex min-h-11 items-center justify-center rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {importing
                  ? "Импорт..."
                  : `Импортировать ${importPreview?.ready_rows ?? ""} занятий`}
              </button>
            </div>

            {importPreview && (
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                <p className="text-sm font-medium text-slate-800">
                  Результат проверки
                </p>

                <div className="mt-2 flex flex-wrap gap-4 text-sm">
                  <span>
                    Всего строк: <strong>{importPreview.total_rows}</strong>
                  </span>
                  <span className="text-emerald-700">
                    Готово: <strong>{importPreview.ready_rows}</strong>
                  </span>
                  <span className="text-red-700">
                    Ошибки: <strong>{importPreview.needs_mapping}</strong>
                  </span>
                </div>

                {importPreview.rows?.some(
                  (row: any) => row.issues?.length > 0
                ) && (
                  <div className="mt-3 space-y-2">
                    {importPreview.rows.map((row: any) =>
                      row.issues?.length ? (
                        <div
                          key={row.excel_row}
                          className="text-sm text-red-700"
                        >
                          <strong>Строка {row.excel_row}:</strong>{" "}
                          {row.issues.join("; ")}
                        </div>
                      ) : null
                    )}
                  </div>
                )}

                {importPreview.can_import && (
                  <p className="mt-3 text-sm font-medium text-emerald-700">
                    Все строки готовы. Можно импортировать расписание.
                  </p>
                )}
              </div>
            )}
          </div>
        </section>


                          </>
            )}

            {profileRole === "admin" && (
              <>
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

                <div>
                  <label className={labelClass}>
                    <span className="flex items-center gap-2">
                      <Clock3 className="h-4 w-4 text-slate-400" />
                      Учебная пара
                    </span>

                    <select
                      required
                      value={`${start}-${end}`}
                      onChange={(event) => {
                        const [newStart, newEnd] = event.target.value.split("-");
                        setStart(newStart);
                        setEnd(newEnd);
                      }}
                      className={fieldClass}
                    >
                      <option value="">Выберите пару</option>
                      <option value="08:30-10:05">1-я пара (08:30–10:05)</option>
                      <option value="10:15-11:50">2-я пара (10:15–11:50)</option>
                      <option value="12:00-13:35">3-я пара (12:00–13:35)</option>
                      <option value="14:30-16:05">4-я пара (14:30–16:05)</option>
                      <option value="16:15-17:50">5-я пара (16:15–17:50)</option>
                      <option value="18:00-19:35">6-я пара (18:00–19:35)</option>
                    </select>
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

                          </>
            )}

            {/* Сообщения API */}
            {profileRole === "admin" && message && (
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
                {profileRole === "admin" && <div className="mb-4 rounded-2xl border border-slate-200 bg-white p-5">
                  <label
                    htmlFor="teacher-filter"
                    className={labelClass}
                  >
                    Расписание преподавателя
                  </label>

                  <select
                    id="teacher-filter"
                    value={selectedTeacherId}
                    onChange={(event) =>
                      setSelectedTeacherId(event.target.value)
                    }
                    className={fieldClass}
                  >
                    <option value="">Все преподаватели</option>

                    {teachers.map((teacher) => (
                      <option key={teacher.id} value={teacher.id}>
                        {teacher.name}
                      </option>
                    ))}
                  </select>
                  <div className="relative mb-4 rounded-2xl border border-slate-200 bg-white p-5">
                    <label
                      htmlFor="teacher-search"
                      className={`${labelClass} block`}
                    >
                      Поиск преподавателя
                    </label>

                    <input
                      id="teacher-search"
                      type="text"
                      value={teacherSearch}
                      onChange={(event) => {
                        setTeacherSearch(event.target.value);
                        setSelectedTeacherId("");
                        setShowTeacherSuggestions(true);
                      }}
                      onFocus={() => setShowTeacherSuggestions(true)}
                      onBlur={() => {
                        setTimeout(() => setShowTeacherSuggestions(false), 150);
                      }}
                      placeholder="Введите имя преподавателя..."
                      autoComplete="off"
                      className={fieldClass}
                    />

                    {showTeacherSuggestions && teacherSearch.trim() !== "" && (
                      <div className="absolute left-5 right-5 top-full z-20 mt-1 max-h-60 overflow-y-auto rounded-xl border border-slate-200 bg-white py-1 shadow-lg">
                        {filteredTeachers.length > 0 ? (
                          filteredTeachers.map((teacher) => (
                            <button
                              key={teacher.id}
                              type="button"
                              className="block w-full px-4 py-3 text-left text-sm text-slate-700 hover:bg-slate-100"
                              onMouseDown={(event) => event.preventDefault()}
                              onClick={() => {
                                setSelectedTeacherId(String(teacher.id));
                                setTeacherSearch(teacher.name);
                                setShowTeacherSuggestions(false);
                              }}
                            >
                              {teacher.name}
                            </button>
                          ))
                        ) : (
                          <p className="px-4 py-3 text-sm text-slate-500">
                            Преподаватели не найдены
                          </p>
                        )}
                      </div>
                    )}

                    {selectedTeacherId && (
                      <button
                        type="button"
                        onClick={() => {
                          setSelectedTeacherId("");
                          setTeacherSearch("");
                          setShowTeacherSuggestions(false);
                        }}
                        className="mt-3 text-sm text-blue-600 hover:text-blue-800"
                      >
                        Показать всех преподавателей
                      </button>
                    )}
                  </div>

                </div>}
                <h2 className="text-base font-semibold text-slate-900">
                  Занятия по дням недели
                </h2>
                <p className="mt-1 text-xs text-slate-400">
                  Занятия отсортированы по времени начала
                </p>
              </div>

              <div className="space-y-4">
                {days.map((day, index) => {
                  const dayEntries = filteredEntries
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
                                    {(() => {
                                      const pair = [
                                        { number: 1, start: "08:30", end: "10:05" },
                                        { number: 2, start: "10:15", end: "11:50" },
                                        { number: 3, start: "12:00", end: "13:35" },
                                        { number: 4, start: "14:30", end: "16:05" },
                                        { number: 5, start: "16:15", end: "17:50" },
                                        { number: 6, start: "18:00", end: "19:35" },
                                      ].find(
                                        (pair) =>
                                          pair.start === entry.start_time &&
                                          pair.end === entry.end_time
                                      );

                                      return (
                                        <p className="mb-1 text-xs font-semibold text-blue-700">
                                          {pair
                                            ? `${pair.number}-я пара`
                                            : "Время вне стандартных пар"}
                                        </p>
                                      );
                                    })()}

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

                                {profileRole === "admin" && <button
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
                                </button>}
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
