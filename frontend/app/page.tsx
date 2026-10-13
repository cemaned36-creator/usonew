"use client";

import { useEffect, useState } from "react";

import Link from "next/link";

import {
  AlertTriangle,
  ArrowRight,
  CalendarDays,
  CheckCircle2,
  ChevronRight,
  Clock3,
  DoorOpen,
  GraduationCap,
  KeyRound,
  LayoutDashboard,
  MapPin,
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
  stats: {
    lessons: number;
    teachers: number;
    rooms: number;
    problems: number;
  };

  schedule: ScheduleItem[];

  optimization: {
    before: {
      transition_minutes: number;
      key_operations: number;
      conflicts: number;
    };

    after: {
      transition_minutes: number;
      key_operations: number;
      conflicts: number;
    };
  };
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

  /* =========================
     LOAD DATA FROM FASTAPI
  ========================= */

  useEffect(() => {
    async function loadDashboard() {
      try {
        const response = await fetch(`${API}/dashboard`);

        if (!response.ok) {
          throw new Error(
            `API error: ${response.status}`
          );
        }

        const data: DashboardData =
          await response.json();

        setDashboard(data);
      } catch (error) {
        console.error(
          "Ошибка загрузки Dashboard:",
          error
        );

        setError(
          "Не удалось подключиться к API"
        );
      } finally {
        setLoading(false);
      }
    }

    loadDashboard();
  }, []);

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

  return (
    <div className="min-h-screen bg-[#f7f8fa] text-slate-900">
      <div className="flex min-h-screen">

        {/* =====================================================
            SIDEBAR
        ===================================================== */}

        <aside className="hidden w-[250px] shrink-0 border-r border-slate-200 bg-white lg:flex lg:flex-col">

          {/* Logo */}

          <div className="flex h-[76px] items-center gap-3 border-b border-slate-200 px-6">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-900">
              <CalendarDays className="h-5 w-5 text-white" />
            </div>

            <div>
              <div className="text-[15px] font-semibold tracking-tight">
                University
              </div>

              <div className="text-[12px] text-slate-400">
                Schedule Optimizer
              </div>
            </div>
          </div>

          {/* Navigation */}

          <nav className="flex-1 px-3 py-5">

            <div className="mb-3 px-3 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
              Основное
            </div>

            <div className="space-y-1">

              <SidebarItem
                icon={LayoutDashboard}
                label="Dashboard"
                active
              />

              <SidebarItem
                icon={CalendarDays}
                label="Расписание"
              />

              <SidebarItem
                icon={GraduationCap}
                label="Преподаватели"
              />

              <SidebarItem
                icon={DoorOpen}
                label="Аудитории"
              />

              <SidebarItem
                icon={Sparkles}
                label="Оптимизация"
              />

            </div>

            <div className="mb-3 mt-8 px-3 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
              Система
            </div>

            <div className="space-y-1">

              <SidebarItem
                icon={Settings}
                label="Настройки"
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
                Dashboard
              </h1>

              <p className="mt-0.5 text-sm text-slate-400">
                Обзор расписания университета
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

              <div className="flex h-10 w-10 items-center justify-center rounded-full border border-slate-200 bg-white">
                <Users className="h-4 w-4 text-slate-500" />
              </div>

            </div>

          </header>

          {/* CONTENT */}

          <div className="px-5 py-6 sm:px-8">

            {/* =================================================
                STATISTICS
            ================================================= */}

            <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">

              <StatCard
                icon={CalendarDays}
                title="Занятий"
                value={String(
                  dashboard.stats.lessons
                )}
                description="в базе"
              />

              <StatCard
                icon={GraduationCap}
                title="Преподавателей"
                value={String(
                  dashboard.stats.teachers
                )}
                description="в системе"
              />

              <StatCard
                icon={DoorOpen}
                title="Аудиторий"
                value={String(
                  dashboard.stats.rooms
                )}
                description="доступно"
              />

              <StatCard
                icon={AlertTriangle}
                title="Проблем"
                value={String(
                  dashboard.stats.problems
                )}
                description="требуют внимания"
                warning={
                  dashboard.stats.problems > 0
                }
              />

            </section>

            {/* =================================================
                SCHEDULE
            ================================================= */}

            <section className="mt-6 w-full">
              <Link
                href="/weekly-schedule"
                className="group block overflow-hidden rounded-2xl border border-slate-200 bg-white transition hover:border-slate-300 hover:shadow-sm focus:outline-none focus:ring-2 focus:ring-slate-900 focus:ring-offset-2"
              >

                {/* Schedule header */}

                <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4 sm:px-6">

                  <div>

                    <h2 className="text-base font-semibold">
                      Расписание на сегодня
                    </h2>

                    <p className="mt-1 text-xs text-slate-400">
                      Занятия и распределение по аудиториям
                    </p>

                  </div>

                  <span className="flex items-center gap-1 text-sm font-medium text-slate-600 transition group-hover:text-slate-900">
                    Открыть
                    <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" />
                  </span>

                </div>

                {/* Schedule */}

                {dashboard.schedule.length === 0 ? (

                  <div className="flex flex-col items-center justify-center px-6 py-16 text-center">

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

                  <div>

                    {dashboard.schedule.map(
                      (item, index) => (

                        <div
                          key={item.id}
                          className={`grid grid-cols-[90px_minmax(220px,1.7fr)_minmax(160px,1fr)_100px_30px] items-center gap-4 px-5 py-4 sm:px-6 ${
                            index !==
                            dashboard.schedule.length - 1
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

                            <div className="truncate text-sm font-medium text-slate-800">
                              {item.subject}
                            </div>

                            <div className="mt-1 flex items-center gap-2 text-xs text-slate-400">

                              <span>
                                {item.teacher}
                              </span>

                              <span className="h-1 w-1 rounded-full bg-slate-300" />

                              <span>
                                {item.group}
                              </span>

                            </div>

                          </div>

                          {/* Room type */}

                          <div>

                            <span className="inline-flex rounded-lg bg-slate-50 px-2.5 py-1.5 text-xs font-medium text-slate-600">
                              {item.room_type}
                            </span>

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

            {/* =================================================
                OPTIMIZATION EFFECT
            ================================================= */}

            <section className="mt-6">

              <div className="mb-3 flex items-center justify-between">

                <div>

                  <h2 className="text-base font-semibold">
                    Эффект оптимизации
                  </h2>

                  <p className="mt-1 text-xs text-slate-400">
                    Сравнение текущего и оптимизированного расписания
                  </p>

                </div>

                <Sparkles className="h-5 w-5 text-slate-400" />

              </div>

              <div className="grid gap-4 lg:grid-cols-2">

                {/* CURRENT */}

                <div className="rounded-2xl border border-slate-200 bg-white p-5">

                  <div className="mb-4 flex items-center justify-between">

                    <div>

                      <div className="text-xs font-medium uppercase tracking-wide text-slate-400">
                        Текущее
                      </div>

                      <div className="mt-1 text-sm font-medium text-slate-700">
                        До оптимизации
                      </div>

                    </div>

                    <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-slate-100">
                      <Clock3 className="h-4 w-4 text-slate-500" />
                    </div>

                  </div>

                  <div className="grid grid-cols-3 gap-4">

                    <Metric
                      value={`${dashboard.optimization.before.transition_minutes} мин`}
                      label="перемещения"
                    />

                    <Metric
                      value={String(
                        dashboard.optimization.before.key_operations
                      )}
                      label="операций с ключами"
                    />

                    <Metric
                      value={String(
                        dashboard.optimization.before.conflicts
                      )}
                      label="конфликтов"
                    />

                  </div>

                </div>

                {/* OPTIMIZED */}

                <div className="rounded-2xl border border-emerald-200 bg-emerald-50/50 p-5">

                  <div className="mb-4 flex items-center justify-between">

                    <div>

                      <div className="text-xs font-medium uppercase tracking-wide text-emerald-600">
                        Оптимизированное
                      </div>

                      <div className="mt-1 text-sm font-medium text-slate-700">
                        После оптимизации
                      </div>

                    </div>

                    <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-100">
                      <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                    </div>

                  </div>

                  <div className="grid grid-cols-3 gap-4">

                    <Metric
                      value={`${dashboard.optimization.after.transition_minutes} мин`}
                      label="перемещения"
                      positive
                    />

                    <Metric
                      value={String(
                        dashboard.optimization.after.key_operations
                      )}
                      label="операций с ключами"
                      positive
                    />

                    <Metric
                      value={String(
                        dashboard.optimization.after.conflicts
                      )}
                      label="конфликтов"
                      positive
                    />

                  </div>

                </div>

              </div>

            </section>
            {/* =================================================
                PROBLEMS
            ================================================= */}

            <section className="mt-6">

              <div className="mb-3">

                <h2 className="text-base font-semibold">
                  Требуют внимания
                </h2>

                <p className="mt-1 text-xs text-slate-400">
                  Проблемы, найденные в текущем расписании
                </p>

              </div>

              <div className="grid gap-3 md:grid-cols-3">

                <ProblemCard
                  icon={AlertTriangle}
                  title="Конфликт расписания"
                  description="Проверка конфликтов будет подключена следующим этапом"
                />

                <ProblemCard
                  icon={MapPin}
                  title="Долгое перемещение"
                  description="Расчёт перемещений будет подключен к Dashboard"
                />

                <ProblemCard
                  icon={KeyRound}
                  title="Необходим ключ"
                  description="Информация о доступе к аудиториям уже доступна из API"
                />

              </div>

            </section>

          </div>

        </main>

      </div>
    </div>
  );
}

/* =============================================================
   SIDEBAR ITEM
============================================================= */

function SidebarItem({
  icon: Icon,
  label,
  active = false,
}: {
  icon: React.ElementType;
  label: string;
  active?: boolean;
}) {
  return (
    <button
      className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition ${
        active
          ? "bg-slate-900 text-white"
          : "text-slate-500 hover:bg-slate-50 hover:text-slate-900"
      }`}
    >
      <Icon
        className={`h-[18px] w-[18px] ${
          active
            ? "text-white"
            : "text-slate-400"
        }`}
      />

      <span>{label}</span>

      {active && (
        <div className="ml-auto h-1.5 w-1.5 rounded-full bg-white" />
      )}
    </button>
  );
}

/* =============================================================
   STAT CARD
============================================================= */

function StatCard({
  icon: Icon,
  title,
  value,
  description,
  warning = false,
}: {
  icon: React.ElementType;
  title: string;
  value: string;
  description: string;
  warning?: boolean;
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5">

      <div className="flex items-start justify-between">

        <div>

          <div className="text-sm text-slate-400">
            {title}
          </div>

          <div
            className={`mt-2 text-2xl font-semibold tracking-tight ${
              warning
                ? "text-amber-600"
                : "text-slate-900"
            }`}
          >
            {value}
          </div>

          <div className="mt-1 text-xs text-slate-400">
            {description}
          </div>

        </div>

        <div
          className={`flex h-10 w-10 items-center justify-center rounded-xl ${
            warning
              ? "bg-amber-50"
              : "bg-slate-50"
          }`}
        >

          <Icon
            className={`h-5 w-5 ${
              warning
                ? "text-amber-500"
                : "text-slate-500"
            }`}
          />

        </div>

      </div>

    </div>
  );
}

/* =============================================================
   METRIC
============================================================= */

function Metric({
  value,
  label,
  positive = false,
}: {
  value: string;
  label: string;
  positive?: boolean;
}) {
  return (
    <div>

      <div
        className={`text-lg font-semibold ${
          positive
            ? "text-emerald-600"
            : "text-slate-800"
        }`}
      >
        {value}
      </div>

      <div className="mt-1 text-xs text-slate-400">
        {label}
      </div>

    </div>
  );
}

/* =============================================================
   PROBLEM CARD
============================================================= */

function ProblemCard({
  icon: Icon,
  title,
  description,
}: {
  icon: React.ElementType;
  title: string;
  description: string;
}) {
  return (
    <div className="flex items-start gap-3 rounded-2xl border border-slate-200 bg-white p-4">

      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-amber-50">

        <Icon className="h-4 w-4 text-amber-600" />

      </div>

      <div className="min-w-0">

        <div className="text-sm font-medium text-slate-800">
          {title}
        </div>

        <div className="mt-1 text-xs leading-5 text-slate-400">
          {description}
        </div>

      </div>

    </div>
  );
}