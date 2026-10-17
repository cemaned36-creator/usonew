"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import BrandLogo from "@/components/BrandLogo";
import {
  AlertCircle,
  ArrowLeft,
  BookOpen,
  CalendarDays,
  ChevronDown,
  GraduationCap,
  Search,
  Sparkles,
  Users,
} from "lucide-react";

const API = (process.env.NEXT_PUBLIC_API_URL ?? "").replace(/\/$/, "");

type Teacher = { id: number; name: string; email?: string | null };
type Lesson = { id: number; teacher_id: number; subject_id: number; group_id: number };
type NamedItem = { id: number; name: string; students_count?: number };

export default function TeachersPage() {
  const [teachers, setTeachers] = useState<Teacher[]>([]);
  const [lessons, setLessons] = useState<Lesson[]>([]);
  const [subjects, setSubjects] = useState<NamedItem[]>([]);
  const [groups, setGroups] = useState<NamedItem[]>([]);
  const [search, setSearch] = useState("");
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      try {
        if (!API) throw new Error("Не задан NEXT_PUBLIC_API_URL для frontend.");
        const paths = ["/teachers/", "/lessons/", "/subjects/", "/student-groups/"];
        const responses = await Promise.all(paths.map((path) => fetch(`${API}${path}`)));
        const failed = responses.find((response) => !response.ok);
        if (failed) throw new Error(`Не удалось загрузить данные: HTTP ${failed.status}`);
        const [teacherData, lessonData, subjectData, groupData] = await Promise.all(
          responses.map((response) => response.json())
        );
        setTeachers(Array.isArray(teacherData) ? teacherData : []);
        setLessons(Array.isArray(lessonData) ? lessonData : []);
        setSubjects(Array.isArray(subjectData) ? subjectData : []);
        setGroups(Array.isArray(groupData) ? groupData : []);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Не удалось загрузить список преподавателей.");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const filteredTeachers = useMemo(() => {
    const query = search.trim().toLocaleLowerCase("ru");
    return teachers.filter((teacher) => teacher.name.toLocaleLowerCase("ru").includes(query));
  }, [teachers, search]);

  const subjectById = useMemo(() => new Map(subjects.map((subject) => [subject.id, subject])), [subjects]);
  const groupById = useMemo(() => new Map(groups.map((group) => [group.id, group])), [groups]);

  return (
    <div className="min-h-screen bg-[#f7f8fa] text-slate-900">
      <div className="flex min-h-screen">
        <aside className="hidden w-[250px] shrink-0 flex-col border-r border-slate-200 bg-white lg:flex">
          <BrandLogo />
          <nav className="flex-1 px-3 py-5">
            <p className="mb-3 px-3 text-[11px] font-semibold uppercase tracking-wider text-slate-400">Основное</p>
            <div className="space-y-1">
              <NavItem href="/" label="Главная страница" icon={<Users className="h-[18px] w-[18px]" />} />
              <NavItem href="/weekly-schedule" label="Расписание" icon={<CalendarDays className="h-[18px] w-[18px]" />} />
              <NavItem href="/teachers" label="Преподаватели" active icon={<GraduationCap className="h-[18px] w-[18px]" />} />
              <NavItem href="#" label="Аудитории" icon={<BookOpen className="h-[18px] w-[18px]" />} />
              <NavItem href="/optimization" label="Оптимизация" icon={<Sparkles className="h-[18px] w-[18px]" />} />
            </div>
            <p className="mb-3 mt-8 px-3 text-[11px] font-semibold uppercase tracking-wider text-slate-400">Система</p>
            <div className="space-y-1">
              <NavItem href="#" label="Настройки" icon={<Users className="h-[18px] w-[18px]" />} />
            </div>
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
              <div className="flex items-center gap-2">
                <GraduationCap className="h-5 w-5 text-slate-500 lg:hidden" />
                <h1 className="text-xl font-semibold tracking-tight">Преподаватели</h1>
              </div>
              <p className="mt-1 text-sm text-slate-400">Список преподавателей, дисциплин и учебных групп</p>
            </div>
            <Link href="/" className="hidden items-center gap-2 rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm font-medium text-slate-600 transition hover:bg-slate-50 sm:flex">
              <ArrowLeft className="h-4 w-4" /> На главную
            </Link>
          </header>

          <div className="mx-auto max-w-5xl space-y-5 px-5 py-6 sm:px-8">
            <section className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
              <label htmlFor="teacher-search" className="mb-2 block text-sm font-medium text-slate-700">Поиск преподавателя</label>
              <div className="relative">
                <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <input id="teacher-search" type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Введите имя преподавателя..." className="w-full rounded-xl border border-slate-200 bg-white py-3 pl-10 pr-4 text-sm outline-none transition focus:border-slate-400 focus:ring-2 focus:ring-slate-900/10" />
              </div>
              <p className="mt-3 text-xs text-slate-400">Найдено преподавателей: {filteredTeachers.length}</p>
            </section>

            {error && (
              <div role="alert" className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" /> {error}
              </div>
            )}

            {loading ? (
              <div className="rounded-2xl border border-slate-200 bg-white p-10 text-center text-sm text-slate-500">Загружаем преподавателей...</div>
            ) : filteredTeachers.length === 0 ? (
              <div className="rounded-2xl border border-slate-200 bg-white p-10 text-center">
                <GraduationCap className="mx-auto h-8 w-8 text-slate-300" />
                <p className="mt-3 text-sm font-medium text-slate-700">{teachers.length ? "Преподаватели не найдены" : "Список преподавателей пуст"}</p>
                <p className="mt-1 text-sm text-slate-400">Попробуйте изменить поисковый запрос.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {filteredTeachers.map((teacher) => {
                  const teacherLessons = lessons.filter((lesson) => lesson.teacher_id === teacher.id);
                  const expanded = expandedId === teacher.id;
                  const subjectGroups = Array.from(new Set(teacherLessons.map((lesson) => lesson.subject_id))).map((subjectId) => ({
                    subjectId,
                    subjectName: subjectById.get(subjectId)?.name ?? `Дисциплина #${subjectId}`,
                    groupNames: Array.from(new Set(
                      teacherLessons
                        .filter((lesson) => lesson.subject_id === subjectId)
                        .map((lesson) => lesson.group_id)
                    )).map((groupId) => groupById.get(groupId)?.name ?? `Группа #${groupId}`),
                  }));
                  return (
                    <section key={teacher.id} className="overflow-hidden rounded-2xl border border-slate-200 bg-white transition hover:border-slate-300">
                      <button type="button" aria-expanded={expanded} onClick={() => setExpandedId(expanded ? null : teacher.id)} className="flex w-full items-center gap-4 px-5 py-4 text-left sm:px-6">
                        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-sm font-semibold text-slate-700">
                          {teacher.name.split(/\s+/).slice(0, 2).map((part) => part[0]).join("").toLocaleUpperCase("ru")}
                        </div>
                        <div className="min-w-0 flex-1">
                          <h2 className="truncate text-sm font-semibold text-slate-900">{teacher.name}</h2>
                          <p className="mt-1 text-xs text-slate-400">
                            {subjectGroups.length} {subjectGroups.length === 1 ? "дисциплина" : "дисциплин"} · {new Set(teacherLessons.map((lesson) => lesson.group_id)).size} {new Set(teacherLessons.map((lesson) => lesson.group_id)).size === 1 ? "группа" : "групп"}
                          </p>
                        </div>
                        <ChevronDown className={`h-5 w-5 shrink-0 text-slate-400 transition-transform ${expanded ? "rotate-180" : ""}`} />
                      </button>

                      {expanded && (
                        <div className="border-t border-slate-100 bg-slate-50/70 px-5 py-5 sm:px-6">
                          {teacherLessons.length === 0 ? (
                            <p className="text-sm text-slate-500">За этим преподавателем пока не закреплены дисциплины и группы.</p>
                          ) : (
                            <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
                              <div className="grid grid-cols-1 gap-2 bg-slate-100 px-4 py-3 text-[11px] font-semibold uppercase tracking-wide text-slate-500 sm:grid-cols-[minmax(0,0.9fr)_minmax(0,1.5fr)] sm:gap-4">
                                <div>Дисциплина</div>
                                <div>Учебные группы</div>
                              </div>
                              <div className="divide-y divide-slate-100">
                                {subjectGroups.map(({ subjectId, subjectName, groupNames }) => (
                                  <div key={subjectId} className="grid grid-cols-1 gap-2 px-4 py-4 sm:grid-cols-[minmax(0,0.9fr)_minmax(0,1.5fr)] sm:items-start sm:gap-4">
                                    <div className="flex items-start gap-2 text-sm font-semibold text-slate-800">
                                      <BookOpen className="mt-0.5 h-4 w-4 shrink-0 text-slate-400" />
                                      <span>{subjectName}</span>
                                    </div>
                                    <div className="flex flex-wrap gap-2">
                                      {groupNames.length ? groupNames.map((groupName) => (
                                        <span key={groupName} className="rounded-lg bg-slate-100 px-3 py-1.5 text-xs font-medium text-slate-700">{groupName}</span>
                                      )) : <span className="text-sm text-slate-400">Группы не указаны</span>}
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                          <div className="mt-4 border-t border-slate-200 pt-4">
                            <p className="text-xs text-slate-400">Всего записей о занятиях: {teacherLessons.length}</p>
                          </div>
                        </div>
                      )}
                    </section>
                  );
                })}
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}

function NavItem({ href, label, icon, active = false }: { href: string; label: string; icon: React.ReactNode; active?: boolean }) {
  return (
    <Link href={href} aria-current={active ? "page" : undefined} className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition ${active ? "bg-slate-900 font-medium text-white" : "text-slate-500 hover:bg-slate-50 hover:text-slate-900"}`}>
      <span className={active ? "text-white" : "text-slate-400"}>{icon}</span>
      <span>{label}</span>
      {active && <span className="ml-auto h-1.5 w-1.5 rounded-full bg-white" />}
    </Link>
  );
}
