"use client";

import { useEffect, useState } from "react";

import Link from "next/link";
import BrandLogo from "@/components/BrandLogo";

import {
  AlertTriangle,
  ArrowRight,
  CalendarDays,
  ChevronRight,
  DoorOpen,
  GraduationCap,
  LayoutDashboard,
  Settings,
  Sparkles,
  Users,
} from "lucide-react";

/* =========================
   TYPES
========================= */

type ScheduleItem = {
  id: number;
  time: string;
  end: string;
  subject: string;
  teacher: string;
  group: string;
  room: string;
  room_type: string;
  access_type: string;
};

type DashboardData = {
  schedule: ScheduleItem[];
};

type TodayScheduleData = {
  date: string;
  academic_year: string;
  week_number: number;
  week_type: "odd" | "even";
  schedule: ScheduleItem[];
};

/* =========================
   MAIN PAGE
========================= */
const API = (process.env.NEXT_PUBLIC_API_URL ?? "").replace(/\/$/, "");

export default function Home() {
  const [dashboard, setDashboard] =
    useState<DashboardData | null>(null);

  const [loading, setLoading] = useState(true);

  const [error, setError] = useState<string | null>(null);
  const [todayData, setTodayData] = useState<TodayScheduleData | null>(null);
  const [todayLoading, setTodayLoading] = useState(false);
  const [todayError, setTodayError] = useState<string | null>(null);
  const [teachers, setTeachers] = useState<{ id: number; name: string }[]>([]);
  const [teacherSearch, setTeacherSearch] = useState("");
  const [selectedProfile, setSelectedProfile] = useState<{ role: "admin" | "teacher"; teacherId?: number; name: string } | null>(null);
  const [showProfilePicker, setShowProfilePicker] = useState(false);

  function chooseProfile(profile: { role: "admin" | "teacher"; teacherId?: number; name: string }) {
    localStorage.setItem("uso-user-profile", JSON.stringify(profile));
    setSelectedProfile(profile);
    setShowProfilePicker(false);
    setTeacherSearch("");
  }

  /* =========================
     LOAD DATA FROM FASTAPI
  ========================= */

  useEffect(() => {
    try {
      const savedProfile = localStorage.getItem("uso-user-profile");
      if (savedProfile) {
        const parsed = JSON.parse(savedProfile);
        if (parsed?.role === "admin" || (parsed?.role === "teacher" && parsed?.teacherId)) {
          setSelectedProfile(parsed);
        } else {
          setShowProfilePicker(true);
        }
      } else {
        setShowProfilePicker(true);
      }
    } catch {
      localStorage.removeItem("uso-user-profile");
      setShowProfilePicker(true);
    }

    fetch(`${API}/teachers/`)
      .then((response) => response.ok ? response.json() : [])
      .then((data) => setTeachers(Array.isArray(data) ? data : []))
      .catch(() => setTeachers([]));

    async function loadDashboard() {
      try {
        console.log("API URL:", API);

        const response = await fetch(`${API}/dashboard`);

        console.log("HTTP status:", response.status);

        if (!response.ok) {
          throw new Error(`API error: ${response.status}`);
        }

        const data: DashboardData = await response.json();

        console.log("Dashboard data:", data);

        setDashboard(data);
        console.log("Данные переданы в setDashboard");
      } catch (error) {
        console.error("Ошибка загрузки Dashboard:", error);

        setError("Не удалось подключиться к API");
      } finally {
        setLoading(false);
        console.log("Загрузка завершена");
      }
    }

    loadDashboard();
  }, []);

  useEffect(() => {
    if (!selectedProfile) return;

    const controller = new AbortController();
    const profile = selectedProfile;

    async function loadTodaySchedule() {
      setTodayLoading(true);
      setTodayError(null);

      try {
        const params = profile.role === "teacher" && profile.teacherId
          ? `?teacher_id=${profile.teacherId}`
          : "";
        const response = await fetch(`${API}/dashboard/today${params}`, {
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error(`API error: ${response.status}`);
        }

        const data: TodayScheduleData = await response.json();
        setTodayData(data);
      } catch (loadError) {
        if (loadError instanceof Error && loadError.name === "AbortError") return;
        console.error("Ошибка загрузки расписания на сегодня:", loadError);
        setTodayError("Не удалось загрузить расписание на сегодня.");
        setTodayData(null);
      } finally {
        if (!controller.signal.aborted) setTodayLoading(false);
      }
    }

    loadTodaySchedule();
    return () => controller.abort();
  }, [selectedProfile?.role, selectedProfile?.teacherId]);

  /* =========================
     LOADING
  ========================= */

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#f7f8fa]">
        <div className="flex items-center gap-3 text-sm text-slate-500">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-slate-300 border-t-slate-800" />

          <span>
            Загрузка Dashboard...
          </span>
        </div>
      </div>
    );
  }

  /* =========================
     ERROR
  ========================= */

  if (error || !dashboard) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#f7f8fa] px-5">
        <div className="rounded-2xl border border-red-200 bg-white px-8 py-6 text-center shadow-sm">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-red-50">
            <AlertTriangle className="h-6 w-6 text-red-500" />
          </div>

          <h2 className="mt-4 text-base font-semibold text-slate-800">
            Не удалось загрузить Dashboard
          </h2>

          <p className="mt-2 text-sm text-slate-400">
            Не удалось получить данные от сервера.
          Проверьте подключение к API и повторите попытку.
          </p>

          <button
            onClick={() => window.location.reload()}
            className="mt-5 rounded-xl bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800"
          >
            Повторить
          </button>
        </div>
      </div>
    );
  }

  const visibleSchedule = todayData?.schedule ?? [];
  const matchingTeachers = teachers.filter((teacher) =>
    teacher.name.toLowerCase().includes(teacherSearch.trim().toLowerCase())
  );

  return (
    <>
    <div className="min-h-screen bg-[#f7f8fa] text-slate-900">
      <div className="flex min-h-screen">

        {/* =====================================================
            SIDEBAR
        ===================================================== */}

        <aside className="hidden w-[250px] shrink-0 border-r border-slate-200 bg-white lg:flex lg:flex-col">

          {/* Logo */}

          <BrandLogo />

          {/* Navigation */}

          <nav className="flex-1 px-3 py-5">

            <div className="mb-3 px-3 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
              Основное
            </div>

            <div className="space-y-1">

              <SidebarItem
                icon={LayoutDashboard}
                label="Главная страница"
                href="/"
                active
              />

              <SidebarItem
                icon={CalendarDays}
                label="Расписание"
                href="/weekly-schedule"
              />

              <SidebarItem
                icon={GraduationCap}
                label="Преподаватели"
                href="/teachers"
              />

              <SidebarItem
                icon={DoorOpen}
                label="Аудитории"
                href="#"
              />

              {selectedProfile?.role !== "teacher" && (
                <SidebarItem
                  icon={Sparkles}
                  label="Оптимизация"
                  href="/optimization"
                />
              )}

            </div>

            <div className="mb-3 mt-8 px-3 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
              Система
            </div>

            <div className="space-y-1">

              <SidebarItem
                icon={Settings}
                label="Настройки"
                href="#"
              />

            </div>

          </nav>

          {/* User */}

          <div className="border-t border-slate-200 p-4">

            <div className="flex items-center gap-3 rounded-xl bg-slate-50 p-3">

              <div className="flex h-9 w-9 items-center justify-center rounded-full bg-slate-200 text-sm font-semibold">
                АИ
              </div>

              <div className="min-w-0 flex-1">

                <div className="truncate text-sm font-medium">
                  Администратор
                </div>

                <div className="truncate text-xs text-slate-400">
                  admin@university.ru
                </div>

              </div>

            </div>

          </div>

        </aside>

        {/* =====================================================
            MAIN
        ===================================================== */}

        <main className="min-w-0 flex-1">

          {/* Header */}

          <header className="flex h-[76px] items-center justify-between border-b border-slate-200 bg-white px-5 sm:px-8">

            <div>

              <h1 className="text-xl font-semibold tracking-tight">
                Главная страница
              </h1>

              <p className="mt-0.5 text-sm text-slate-400">
                {selectedProfile?.role === "teacher" ? `Личный кабинет преподавателя: ${selectedProfile.name}` : "Обзор расписания университета"}
              </p>

            </div>

            <div className="flex items-center gap-3">

              <div className="hidden text-right sm:block">

                <div className="text-sm font-medium">
                  Сегодня
                </div>

                <div className="text-xs text-slate-400">
                  {new Date().toLocaleDateString(
                    "ru-RU",
                    {
                      day: "numeric",
                      month: "long",
                      year: "numeric",
                    }
                  )}
                </div>

              </div>

              <button
                type="button"
                onClick={() => setShowProfilePicker(true)}
                className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-600 transition hover:bg-slate-50"
              >
                <Users className="h-4 w-4 text-slate-500" />
                <span className="hidden sm:inline">{selectedProfile?.name ?? "Выбрать пользователя"}</span>
              </button>

            </div>

          </header>

          {/* CONTENT */}

          <div className="flex min-h-[calc(100vh-76px)] flex-col px-5 py-5 sm:px-8">

            {/* =================================================
                SCHEDULE
            ================================================= */}

            <section className="mt-1 flex w-full flex-1 flex-col">
              <Link
                href={selectedProfile?.role === "teacher" ? `/weekly-schedule?teacherId=${selectedProfile.teacherId}` : "/weekly-schedule"}
                className="group flex min-h-[calc(100vh-150px)] flex-1 flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white transition hover:border-slate-300 hover:shadow-sm focus:outline-none focus:ring-2 focus:ring-slate-900 focus:ring-offset-2"
              >

                {/* Schedule header */}

                <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4 sm:px-6">

                  <div>

                    <h2 className="text-base font-semibold">
                      Расписание на сегодня
                    </h2>

                    <p className="mt-1 text-xs text-slate-400">
                      {todayData
                        ? `Учебный год ${todayData.academic_year} · ${todayData.week_number}-я неделя · ${todayData.week_type === "odd" ? "нечётная" : "чётная"}`
                        : "Занятия и распределение по аудиториям"}
                    </p>

                  </div>

                  <span className="flex items-center gap-1 text-sm font-medium text-slate-600 transition group-hover:text-slate-900">
                    Открыть
                    <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" />
                  </span>

                </div>

                {/* Schedule */}

                {todayLoading ? (
                  <div className="flex flex-1 flex-col items-center justify-center px-6 py-16 text-center">
                    <div className="h-6 w-6 animate-spin rounded-full border-2 border-slate-200 border-t-emerald-600" />
                    <p className="mt-3 text-sm text-slate-500">Загружаем расписание...</p>
                  </div>
                ) : todayError ? (
                  <div className="flex flex-1 flex-col items-center justify-center px-6 py-16 text-center">
                    <AlertTriangle className="h-8 w-8 text-amber-500" />
                    <p className="mt-3 text-sm text-slate-600">{todayError}</p>
                  </div>
                ) : visibleSchedule.length === 0 ? (

                  <div className="flex flex-1 flex-col items-center justify-center px-6 py-16 text-center">

                    <div className="flex h-12 w-12 items-center justify-center rounded-full bg-slate-50">
                      <CalendarDays className="h-6 w-6 text-slate-400" />
                    </div>

                    <h3 className="mt-4 text-sm font-medium text-slate-700">
                      На сегодня занятий нет
                    </h3>

                    <p className="mt-1 text-xs text-slate-400">
                      В базе пока нет записей расписания на текущую дату
                    </p>

                  </div>

                ) : (

                  <div className="flex-1">

                    {visibleSchedule.map(
                      (item, index) => (

                        <div
                          key={item.id}
                          className={`grid grid-cols-[90px_minmax(0,1fr)_100px_30px] items-center gap-4 px-5 py-4 sm:px-6 ${
                            index !==
                            visibleSchedule.length - 1
                              ? "border-b border-slate-100"
                              : ""
                          }`}
                        >

                          {/* Time */}

                          <div>

                            <div className="text-sm font-semibold text-slate-800">
                              {item.time}
                            </div>

                            <div className="mt-0.5 text-xs text-slate-400">
                              {item.end}
                            </div>

                          </div>

                          {/* Lesson */}

                          <div className="min-w-0">

                            <div className="flex min-w-0 items-center gap-2 text-base font-semibold text-slate-800">
                              <span className="truncate">{item.subject}</span>
                              <span aria-hidden="true" className="shrink-0 text-emerald-500">·</span>
                              <span className="shrink-0">{item.group}</span>
                            </div>

                          </div>

                          {/* Room */}

                          <div className="flex items-center gap-2">

                            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-100">
                              <DoorOpen className="h-4 w-4 text-slate-500" />
                            </div>

                            <div>

                              <div className="text-sm font-semibold">
                                {item.room}
                              </div>

                              <div className="text-[11px] text-slate-400">
                                {item.access_type ===
                                "KEY"
                                  ? "ключ"
                                  : "пропуск"}
                              </div>

                            </div>

                          </div>

                          {/* Status */}

                          <div className="flex justify-end">

                            <ChevronRight className="h-4 w-4 text-slate-300" />

                          </div>

                        </div>

                      )
                    )}

                  </div>

                )}

              </Link>

            </section>

          </div>

        </main>

      </div>
    </div>

      {showProfilePicker && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 p-4">
          <div role="dialog" aria-modal="true" aria-labelledby="profile-picker-title" className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-2xl">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-slate-100">
              <Users className="h-6 w-6 text-slate-700" />
            </div>
            <h2 id="profile-picker-title" className="mt-4 text-xl font-semibold">Кто будет пользоваться системой?</h2>
            <p className="mt-1 text-sm leading-6 text-slate-500">Выбери роль. Преподаватель сможет только просматривать своё расписание.</p>
            <button type="button" onClick={() => chooseProfile({ role: "admin", name: "Администратор" })} className="mt-5 flex w-full items-center gap-3 rounded-xl border border-slate-200 p-4 text-left transition hover:border-slate-400 hover:bg-slate-50">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-slate-900 text-white"><Settings className="h-5 w-5" /></div>
              <div><div className="font-medium text-slate-800">Администратор</div><div className="mt-0.5 text-xs text-slate-500">Полный доступ к функциям управления</div></div>
            </button>
            <div className="mt-5">
              <label htmlFor="teacher-profile-search" className="text-sm font-medium text-slate-700">Преподаватель</label>
              <input id="teacher-profile-search" value={teacherSearch} onChange={(event) => setTeacherSearch(event.target.value)} placeholder="Начни вводить имя преподавателя..." className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 text-sm outline-none focus:border-slate-900 focus:ring-2 focus:ring-slate-900/10" />
              <div className="mt-2 max-h-52 overflow-y-auto rounded-xl border border-slate-100">
                {matchingTeachers.length ? matchingTeachers.map((teacher) => (
                  <button key={teacher.id} type="button" onClick={() => chooseProfile({ role: "teacher", teacherId: teacher.id, name: teacher.name })} className="block w-full border-b border-slate-100 px-4 py-3 text-left text-sm text-slate-700 last:border-b-0 hover:bg-slate-50">{teacher.name}</button>
                )) : <p className="px-4 py-3 text-sm text-slate-500">{teachers.length ? "Преподаватели не найдены" : "Список преподавателей пока недоступен"}</p>}
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

/* =============================================================
   SIDEBAR ITEM
============================================================= */

function SidebarItem({
  icon: Icon,
  label,
  href,
  active = false,
}: {
  icon: React.ElementType;
  label: string;
  href: string;
  active?: boolean;
}) {
  return (
    <Link
      href={href}
      aria-current={active ? "page" : undefined}
      className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition ${
        active
          ? "bg-slate-900 text-white"
          : "text-slate-500 hover:bg-slate-50 hover:text-slate-900"
      }`}
    >
      <Icon
        className={`h-[18px] w-[18px] ${
          "text-emerald-600"
        }`}
      />
      <span>{label}</span>
      {active && (
        <div className="ml-auto h-1.5 w-1.5 rounded-full bg-white" />
      )}
    </Link>
  );
}

