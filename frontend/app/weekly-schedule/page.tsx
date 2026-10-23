
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import BrandLogo from "@/components/BrandLogo";
import {
  AlertCircle,
  ArrowLeft,
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  CheckCircle2,
  Clock3,
  DoorOpen,
  GraduationCap,
  Plus,
  Sparkles,
  Trash2,
  Info,
  Settings,
} from "lucide-react";

import { formatParticipants } from "../../lib/lesson-participants";
import type { LessonParticipant } from "../../lib/lesson-participants";

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
  week_type: "odd" | "even";
  faculties?: string[];
  groups?: LessonParticipant[];
  students_count?: number;
  lesson_type?: string | null;
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
  groups?: LessonParticipant[];
  students_count?: number;
  lesson_type?: string | null;
};

type MessageType = "success" | "error" | "info";

function startOfWeek(date: Date) {
  const result = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  result.setDate(result.getDate() - ((result.getDay() + 6) % 7));
  result.setHours(0, 0, 0, 0);
  return result;
}

function getWeekType(date: Date): "odd" | "even" {
  const year = date.getFullYear();
  const month = date.getMonth();
  const academicYear = month >= 8 ? year : year - 1;

  const septemberFirst = new Date(Date.UTC(academicYear, 8, 1));
  const mondayOffset = (septemberFirst.getUTCDay() + 6) % 7;
  const firstMonday =
    septemberFirst.getTime() - mondayOffset * 86400000;

  const selectedDay = Date.UTC(year, month, date.getDate());
  const weekNumber =
    Math.floor((selectedDay - firstMonday) / (7 * 86400000)) + 1;

  return weekNumber % 2 === 1 ? "odd" : "even";
}

function formatDayDate(date: Date) {
  return new Intl.DateTimeFormat("ru-RU", { day: "numeric", month: "short" }).format(date);
}

function formatMonth(date: Date) {
  return new Intl.DateTimeFormat("ru-RU", { month: "long", year: "numeric" }).format(date);
}

const fieldClass =
  "mt-2 block w-full rounded-xl border border-slate-300 bg-white px-3.5 py-3 text-sm font-medium text-slate-900 outline-none transition placeholder:text-slate-400 hover:border-slate-400 focus:border-slate-900 focus:ring-2 focus:ring-slate-900/10";

const labelClass =
  "block text-sm font-medium text-slate-700";

export default function WeeklySchedulePage() {
  const [entries, setEntries] = useState<Entry[]>([]);
  const [lessons, setLessons] = useState<Lesson[]>([]);
  const [teachers, setTeachers] = useState<NamedOption[]>([]);
  const [selectedTeacherId, setSelectedTeacherId] = useState("");
  const [selectedFaculty, setSelectedFaculty] = useState("");
  const [teacherSearch, setTeacherSearch] = useState("");
  const [showTeacherSuggestions, setShowTeacherSuggestions] = useState(false);
  const [profileRole, setProfileRole] = useState<"admin" | "teacher">("admin");
  const [profileLoaded, setProfileLoaded] = useState(false);
  const [profileTeacherName, setProfileTeacherName] = useState("");
  const [subjects, setSubjects] = useState<NamedOption[]>([]);
  const [groups, setGroups] = useState<NamedOption[]>([]);
  const [rooms, setRooms] = useState<NamedOption[]>([]);
  const lessonPairs = [
    { number: 1, start: "08:30", end: "10:05", label: "1-я пара (08:30–10:05)" },
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

  const [oddImportFile, setOddImportFile] = useState<File | null>(null);
  const [evenImportFile, setEvenImportFile] = useState<File | null>(null);
  const [oddImportPreview, setOddImportPreview] = useState<any>(null);
  const [evenImportPreview, setEvenImportPreview] = useState<any>(null);
  const [importingWeek, setImportingWeek] = useState<"odd" | "even" | null>(null);
  const [previewingWeek, setPreviewingWeek] = useState<"odd" | "even" | null>(null);

  const [lessonId, setLessonId] = useState("");
  const [roomId, setRoomId] = useState("");
  const [weekday, setWeekday] = useState("0");
  const [selectedWeekType, setSelectedWeekType] = useState<"odd" | "even">(() => getWeekType(new Date()));
  const [weekStart, setWeekStart] = useState<Date>(() => startOfWeek(new Date()));
  const [calendarMonth, setCalendarMonth] = useState<Date>(() => {
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), 1);
  });
  const [calendarOpen, setCalendarOpen] = useState(false);
  const [manualFormOpen, setManualFormOpen] = useState(false);
  const [bulkDeleteType, setBulkDeleteType] = useState<"odd" | "even" | "both">("both");
  const [bulkDeleting, setBulkDeleting] = useState(false);
  const [entryWeekType, setEntryWeekType] = useState<"odd" | "even">("odd");
  const [start, setStart] = useState("08:30");
  const [end, setEnd] = useState("10:05");

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

  function lessonLabel(id: number, entry?: Entry) {
    const lesson = lessons.find((item) => item.id === id);
    const scheduled = entry ?? entries.find((item) => item.lesson_id === id);

    if (!lesson) {
      return `Занятие #${id}`;
    }

    const subject = subjects.find(
      (item) => item.id === lesson.subject_id,
    );
    const teacher = teachers.find(
      (item) => item.id === lesson.teacher_id,
    );

    return [
      subject?.name ?? `Предмет #${lesson.subject_id}`,
      teacher?.name ?? `Преподаватель #${lesson.teacher_id}`,
      formatParticipants(lesson.groups ?? scheduled?.groups),
    ].join(" — ");
  }

    async function chooseCalendarDate(date: Date) {
    const nextStart = startOfWeek(date);
    const nextType = getWeekType(date);

    setWeekStart(nextStart);
    setSelectedWeekType(nextType);
    setCalendarOpen(false);
    setLoading(true);

    try {
      await loadSchedule(nextType);
    } catch (error) {
      showMessage(
        error instanceof Error
          ? error.message
          : "Не удалось загрузить расписание",
        "error",
      );
    } finally {
      setLoading(false);
    }
  }

  async function deleteScheduleBulk() {
    const weekLabel =
      bulkDeleteType === "both"
        ? "обеих недель"
        : bulkDeleteType === "odd"
          ? "нечётной недели"
          : "чётной недели";

    if (
      !window.confirm(
        `Удалить все занятия для ${weekLabel}? Это действие нельзя отменить.`,
      )
    ) {
      return;
    }

    setBulkDeleting(true);

    try {
      const response = await fetch(
        `${API}/weekly-schedule/bulk?week_type=${bulkDeleteType}`,
        { method: "DELETE" },
      );
      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : "Не удалось очистить расписание",
        );
      }

      showMessage(
        `Удалено занятий: ${data.deleted_count ?? 0}.`,
        "success",
      );
      await loadSchedule(selectedWeekType);
    } catch (error) {
      showMessage(
        error instanceof Error
          ? error.message
          : "Ошибка удаления расписания",
        "error",
      );
    } finally {
      setBulkDeleting(false);
    }
  }

  async function loadSchedule(weekType: "odd" | "even" = selectedWeekType) {
    const response = await fetch(`${API}/weekly-schedule/?week_type=${weekType}`);

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
          `/weekly-schedule/?week_type=${getWeekType(new Date())}`,
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
          week_type: entryWeekType,
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

  async function previewImport(weekType: "odd" | "even") {
    if (!profileLoaded || profileRole !== "admin") return;

    const importFile = weekType === "odd" ? oddImportFile : evenImportFile;
    if (!importFile) {
      showMessage("Сначала выбери Excel-файл (.xlsx)", "error");
      return;
    }

    setPreviewingWeek(weekType);
    if (weekType === "odd") setOddImportPreview(null);
    else setEvenImportPreview(null);
    setMessage("");

    try {
      const formData = new FormData();
      formData.append("file", importFile);

      const response = await fetch(`${API}/weekly-schedule/import/preview`, {
        method: "POST",
        body: formData,
      });

      const data = await readApiResponse(response);
      if (weekType === "odd") setOddImportPreview(data);
      else setEvenImportPreview(data);

      if (data.can_import) {
        showMessage(
          `Проверка файла для ${weekType === "odd" ? "нечётной" : "чётной"} недели завершена: готово ${data.ready_rows} занятий.`,
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
      setPreviewingWeek(null);
    }
  }

  async function importSchedule(weekType: "odd" | "even") {
    if (!profileLoaded || profileRole !== "admin") return;

    const importFile = weekType === "odd" ? oddImportFile : evenImportFile;
    const importPreview = weekType === "odd" ? oddImportPreview : evenImportPreview;

    if (!importFile || !importPreview?.can_import) {
      showMessage("Сначала выбери и проверь Excel-файл", "error");
      return;
    }

    const weekLabel = weekType === "odd" ? "нечётной" : "чётной";
    if (!window.confirm(
      `Загрузить расписание на ${weekLabel} неделю? Все записи выбранной недели будут заменены. Расписание противоположной недели останется без изменений.`
    )) {
      return;
    }

    setImportingWeek(weekType);
    setMessage("");

    try {
      const formData = new FormData();
      formData.append("file", importFile);

      const response = await fetch(
        `${API}/weekly-schedule/import?week_type=${weekType}`,
        {
          method: "POST",
          body: formData,
        }
      );

      const data = await readApiResponse(response);
      await loadSchedule();

      if (weekType === "odd") {
        setOddImportPreview(null);
        setOddImportFile(null);
        const input = document.getElementById("weekly-schedule-import-odd") as HTMLInputElement | null;
        if (input) input.value = "";
      } else {
        setEvenImportPreview(null);
        setEvenImportFile(null);
        const input = document.getElementById("weekly-schedule-import-even") as HTMLInputElement | null;
        if (input) input.value = "";
      }

      showMessage(
        `Импорт на ${weekLabel} неделю завершён: сохранено занятий — ${data.imported_count}.`,
        "success"
      );
    } catch (error) {
      showMessage(
        error instanceof Error ? error.message : "Ошибка импорта расписания",
        "error"
      );
    } finally {
      setImportingWeek(null);
    }
  }

  const isAdmin = profileLoaded && profileRole === "admin";
  const isTeacherView = profileLoaded && profileRole === "teacher";

  const faculties = Array.from(new Set([
    ...entries.flatMap((entry) => entry.faculties ?? []),
    ...(selectedFaculty ? [selectedFaculty] : []),
  ])).sort((a, b) => a.localeCompare(b, "ru"));

  const filteredEntries = entries.filter((entry) => {
    const entryFaculties = entry.faculties ?? [];
    if (selectedFaculty && !entryFaculties.includes(selectedFaculty)) {
      return false;
    }

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
          <BrandLogo />

          <nav className="flex-1 px-3 py-5">
            <p className="mb-3 px-3 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
              Основное
            </p>

            <Link
              href="/"
              className="mb-1 flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-slate-500 transition hover:bg-slate-50 hover:text-slate-900"
            >
              <GraduationCap className="h-[18px] w-[18px] text-emerald-600" />
              Главная страница
            </Link>

            <Link
              href="/weekly-schedule"
              aria-current="page"
              className="flex items-center gap-3 rounded-xl bg-slate-900 px-3 py-2.5 text-sm font-medium text-white"
            >
              <CalendarDays className="h-[18px] w-[18px] text-emerald-600" />
              Расписание
              <span className="ml-auto h-1.5 w-1.5 rounded-full bg-white" />
            </Link>

            <Link
              href="/teachers"
              className="mt-1 flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-slate-500 transition hover:bg-slate-50 hover:text-slate-900"
            >
              <GraduationCap className="h-[18px] w-[18px] text-emerald-600" />
              Преподаватели
            </Link>

{isAdmin && (
              <Link
                href="/optimization"
                className="mt-1 flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-slate-500 transition hover:bg-slate-50 hover:text-slate-900"
              >
                <Sparkles className="h-[18px] w-[18px] text-emerald-600" />
                Оптимизация
              </Link>
            )}
            <p className="mb-3 mt-8 px-3 text-[11px] font-semibold uppercase tracking-wider text-slate-400">Система</p>
            <Link href="#" className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-slate-500 transition hover:bg-slate-50 hover:text-slate-900"><Settings className="h-[18px] w-[18px]" />Настройки</Link>
            <Link href="/about-system" className="mt-1 flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-slate-500 transition hover:bg-slate-50 hover:text-slate-900"><Info className="h-[18px] w-[18px]" />О системе</Link>
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
          <header className="relative flex min-h-[88px] items-center justify-between border-b border-slate-200 bg-white px-5 py-4 sm:px-8">
            <div className="flex-1" />
            <div className="absolute left-1/2 max-w-[58%] -translate-x-1/2 text-center"><h1 className="text-lg font-semibold tracking-tight text-slate-900 sm:text-xl">Недельное расписание</h1><p className="mt-1 hidden text-sm text-slate-400 sm:block">{isTeacherView ? `Расписание преподавателя: ${profileTeacherName}` : "Управление занятиями и распределением по аудиториям"}</p></div>
            <div className="flex flex-1 justify-end"><Link href="/" className="hidden items-center gap-2 rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm font-medium text-slate-600 transition hover:bg-slate-50 hover:text-slate-900 sm:flex"><ArrowLeft className="h-4 w-4" /> На главную</Link></div>
          </header>

          <div className="space-y-6 px-5 py-6 sm:px-8">


            {/* Сообщения API */}
            {isAdmin && message && (
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
              <div className="mb-4 rounded-2xl border border-slate-200 bg-white p-4 sm:p-5">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div className="relative shrink-0">
                    <button type="button" onClick={() => setCalendarOpen((open) => !open)} aria-expanded={calendarOpen} className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm font-medium text-slate-800 hover:bg-slate-50">
                      <CalendarDays className="h-4 w-4" /> Выбор недели
                    </button>
                    {calendarOpen && <div className="absolute left-0 z-30 mt-2 w-[min(340px,calc(100vw-3rem))] rounded-2xl border border-slate-200 bg-white p-4 shadow-xl">
                      <div className="mb-3 flex items-center justify-between gap-2">
                        <button type="button" aria-label="Предыдущий месяц" onClick={() => setCalendarMonth((month) => new Date(month.getFullYear(), month.getMonth() - 1, 1))} className="rounded-lg p-2 hover:bg-slate-100"><ChevronLeft className="h-4 w-4" /></button>
                        <p className="text-sm font-semibold capitalize">{formatMonth(calendarMonth)}</p>
                        <button type="button" aria-label="Следующий месяц" onClick={() => setCalendarMonth((month) => new Date(month.getFullYear(), month.getMonth() + 1, 1))} className="rounded-lg p-2 hover:bg-slate-100"><ChevronRight className="h-4 w-4" /></button>
                      </div>
                      <div className="grid grid-cols-7 gap-1 text-center text-xs text-slate-500">{["Пн","Вт","Ср","Чт","Пт","Сб","Вс"].map((day) => <span key={day} className="py-1">{day}</span>)}</div>
                      <div className="grid grid-cols-7 gap-1">
                        {Array.from({ length: 42 }, (_, index) => {
                          const first = startOfWeek(calendarMonth);
                          const date = new Date(first.getFullYear(), first.getMonth(), first.getDate() + index);
                          const inMonth = date.getMonth() === calendarMonth.getMonth();
                          const isSelected = startOfWeek(date).toDateString() === weekStart.toDateString();
                          return <button key={date.toISOString()} type="button" onClick={() => chooseCalendarDate(date)} className={`rounded-lg py-2 text-sm transition ${isSelected ? "bg-slate-900 text-white" : inMonth ? "text-slate-800 hover:bg-slate-100" : "text-slate-300 hover:bg-slate-50"}`}>{date.getDate()}</button>;
                        })}
                      </div>
                      <p className="mt-3 text-xs text-slate-500">Выберите любой день нужной недели.</p>
                    </div>}
                  </div>
                  <div className="min-w-0 flex-1 sm:max-w-xs">
                    <label htmlFor="faculty-filter" className="sr-only">Факультет</label>
                    <select
                      id="faculty-filter"
                      value={selectedFaculty}
                      onChange={(event) => setSelectedFaculty(event.target.value)}
                      className="block w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm font-medium text-slate-900 outline-none transition focus:border-slate-900 focus:ring-2 focus:ring-slate-900/10"
                    >
                      <option value="">Все факультеты</option>
                      {faculties.map((faculty) => (
                        <option key={faculty} value={faculty}>{faculty}</option>
                      ))}
                    </select>
                  </div>
                  {isAdmin && <div className="relative min-w-0 flex-1 sm:max-w-md">
                    <label htmlFor="teacher-search" className="sr-only">Поиск преподавателя</label>
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
                      placeholder="Поиск преподавателя..."
                      autoComplete="off"
                      className="block w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm font-medium text-slate-900 outline-none transition placeholder:text-slate-400 hover:border-slate-400 focus:border-slate-900 focus:ring-2 focus:ring-slate-900/10"
                    />
                    {showTeacherSuggestions && teacherSearch.trim() !== "" && (
                      <div className="absolute left-0 right-0 top-full z-20 mt-1 max-h-60 overflow-y-auto rounded-xl border border-slate-200 bg-white py-1 shadow-lg">
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
                          <p className="px-4 py-3 text-sm text-slate-500">Преподаватели не найдены</p>
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
                        className="mt-2 text-xs text-blue-600 hover:text-blue-800"
                      >Показать всех преподавателей</button>
                    )}
                  </div>}
                </div>
                <div className="mt-4 flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 pt-3">
                  <h2 className="text-base font-semibold text-slate-900">Занятия по дням недели</h2>
                  <span className="text-xs text-slate-500">Неделя с {formatDayDate(weekStart)} по {formatDayDate(new Date(weekStart.getFullYear(), weekStart.getMonth(), weekStart.getDate() + 6))} · {selectedWeekType === "odd" ? "нечётная" : "чётная"} неделя</span>
                </div>
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
                          {day} · {formatDayDate(new Date(weekStart.getFullYear(), weekStart.getMonth(), weekStart.getDate() + index))}
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
                                  <div className="flex w-[94px] shrink-0 flex-col items-center justify-center rounded-xl bg-slate-50 px-3 py-2 text-center">
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
                                      {lessonLabel(entry.lesson_id, entry)}
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

                                {isAdmin && <button
                                  type="button"
                                  onClick={() => removeEntry(entry.id)}
                                  disabled={deletingId === entry.id}
                                  aria-label={`Удалить занятие ${lessonLabel(entry.lesson_id, entry)}`}
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



            {isAdmin && (
              <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
                <button type="button" onClick={() => setManualFormOpen((open) => !open)} aria-expanded={manualFormOpen} className="flex w-full items-center justify-between px-5 py-4 text-left sm:px-6">
                  <span>
                    <span className="block text-base font-semibold text-slate-900">Добавить занятие вручную</span>
                    <span className="mt-1 block text-xs text-slate-500">Добавь отдельное занятие без загрузки Excel-файла.</span>
                  </span>
                  <Plus className={`h-5 w-5 transition-transform ${manualFormOpen ? "rotate-45" : ""}`} />
                </button>

                {manualFormOpen && <form onSubmit={addEntry} className="grid gap-5 p-5 sm:grid-cols-2 sm:p-6">
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
                        Сначала создай занятие в разделе занятий.
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
                  </label>

                  <label className={labelClass}>
                    Неделя
                    <select
                      className={fieldClass}
                      value={entryWeekType}
                      onChange={(event) =>
                        setEntryWeekType(event.target.value as "odd" | "even")
                      }
                    >
                      <option value="odd">Только нечётная</option>
                      <option value="even">Только чётная</option>
                    </select>
                  </label>

                  <label className={labelClass}>
                    День недели
                    <select
                      className={fieldClass}
                      value={weekday}
                      onChange={(event) => setWeekday(event.target.value)}
                    >
                      {days.map((day, index) => (
                        <option key={day} value={index}>{day}</option>
                      ))}
                    </select>
                  </label>

                  <label className={labelClass}>
                    Учебная пара
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

                  <div className="sm:col-span-2">
                    <button
                      type="submit"
                      disabled={saving || !lessons.length || !rooms.length}
                      className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-slate-900 px-5 py-3 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      <Plus className="h-4 w-4" />
                      {saving ? "Добавление..." : "Добавить занятие"}
                    </button>
                  </div>
                </form>}
              </section>
            )}

{/* Импорт отдельных расписаний по типу недели */}
        {isAdmin && <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
          <div className="border-b border-slate-200 px-5 py-4 sm:px-6">
            <h2 className="text-base font-semibold text-slate-900">
              Импорт расписания из Excel
            </h2>
            <p className="mt-1 text-xs text-slate-500">
              Для каждого файла нужен лист «Данные для импорта» и столбцы weekday, group, start_time, end_time, subject, teacher, room.
              При импорте заменяются записи выбранной недели и старые общие записи «обе недели». Расписание противоположной недели сохраняется.
            </p>
          </div>

          <div className="grid gap-5 p-5 sm:grid-cols-2 sm:p-6">
            {([
              {
                type: "odd" as const,
                title: "Нечётная неделя",
                file: oddImportFile,
                preview: oddImportPreview,
                inputId: "weekly-schedule-import-odd",
                setFile: setOddImportFile,
              },
              {
                type: "even" as const,
                title: "Чётная неделя",
                file: evenImportFile,
                preview: evenImportPreview,
                inputId: "weekly-schedule-import-even",
                setFile: setEvenImportFile,
              },
            ]).map((item) => (
              <div key={item.type} className="space-y-4 rounded-xl border border-slate-200 p-4">
                <h3 className="text-sm font-semibold text-slate-900">{item.title}</h3>
                <label className={labelClass}>
                  Excel-файл (.xlsx)
                  <input
                    id={item.inputId}
                    type="file"
                    accept=".xlsx"
                    className={fieldClass}
                    onChange={(event) => {
                      item.setFile(event.target.files?.[0] ?? null);
                      if (item.type === "odd") setOddImportPreview(null);
                      else setEvenImportPreview(null);
                      setMessage("");
                    }}
                  />
                </label>

                <div className="flex flex-wrap gap-3">
                  <button
                    type="button"
                    onClick={() => previewImport(item.type)}
                    disabled={!item.file || previewingWeek !== null || importingWeek !== null}
                    className="inline-flex min-h-11 items-center justify-center rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {previewingWeek === item.type ? "Проверка..." : "Проверить файл"}
                  </button>

                  <button
                    type="button"
                    onClick={() => importSchedule(item.type)}
                    disabled={!item.file || !item.preview?.can_import || importingWeek !== null || previewingWeek !== null}
                    className="inline-flex min-h-11 items-center justify-center rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {importingWeek === item.type
                      ? "Импорт..."
                      : `Импортировать ${item.preview?.ready_rows ?? ""} занятия`}
                  </button>
                </div>

                {item.preview && (
                  <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                    <p className="text-sm font-medium text-slate-800">Результат проверки</p>
                    <div className="mt-2 flex flex-wrap gap-4 text-sm">
                      <span>Всего строк: {item.preview.total_rows}</span>
                      <span className="text-emerald-700">Готово: {item.preview.ready_rows}</span>
                      <span className="text-red-700">Ошибок: {item.preview.needs_mapping}</span>
                    </div>
                    {item.preview.needs_mapping > 0 && (
                      <div className="mt-3 space-y-2">
                        {item.preview.rows
                          .filter((row: any) => row.status !== "ready")
                          .slice(0, 5)
                          .map((row: any) => (
                            <div key={row.excel_row} className="text-xs text-red-700">
                              Строка {row.excel_row}: {row.issues.join("; ")}
                            </div>
                          ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>}



            {isAdmin && <section className="overflow-hidden rounded-2xl border border-red-200 bg-white">
              <div className="border-b border-red-100 px-5 py-4 sm:px-6">
                <h2 className="text-base font-semibold text-red-800">Очистить расписание</h2>
                <p className="mt-1 text-xs text-slate-500">Удаление затрагивает все занятия выбранного типа недели.</p>
              </div>
              <div className="flex flex-col gap-4 p-5 sm:flex-row sm:items-end sm:justify-between sm:p-6">
                <label className={labelClass}>Какое расписание удалить?
                  <select value={bulkDeleteType} onChange={(event) => setBulkDeleteType(event.target.value as "odd" | "even" | "both")} className={fieldClass}>
                    <option value="odd">Только нечётную неделю</option>
                    <option value="even">Только чётную неделю</option>
                    <option value="both">Обе недели</option>
                  </select>
                </label>
                <button type="button" onClick={deleteScheduleBulk} disabled={bulkDeleting} className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-red-700 px-5 py-3 text-sm font-semibold text-white transition hover:bg-red-800 disabled:cursor-not-allowed disabled:opacity-50">
                  <Trash2 className="h-4 w-4" /> {bulkDeleting ? "Удаление..." : "Удалить всё расписание"}
                </button>
              </div>
            </section>}

            <footer className="pb-2 text-center text-xs text-slate-400">
              Оптимизатор расписания УрГУПС
            </footer>
          </div>
        </main>
      </div>
    </div>
  );
}
