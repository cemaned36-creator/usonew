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
  Info,
} from "lucide-react";

const API = (process.env.NEXT_PUBLIC_API_URL ?? "").replace(/\/$/, "");

type Room = { id: number; name: string; building: string; floor: number; capacity: number };
type Conditions = { earliest_start_pair: number; max_floor: number | null; prefer_near_entrance: boolean; preferred_rooms_by_type: Record<string, number[]> };
type Teacher = Conditions & { id: number; name: string; email?: string | null };
type Lesson = { id: number; teacher_id: number; subject_id: number; group_id: number };
type NamedItem = { id: number; name: string; students_count?: number };

export default function TeachersPage() {
  const [teachers, setTeachers] = useState<Teacher[]>([]);
  const [lessons, setLessons] = useState<Lesson[]>([]);
  const [subjects, setSubjects] = useState<NamedItem[]>([]);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [groups, setGroups] = useState<NamedItem[]>([]);
  const [search, setSearch] = useState("");
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [profileLoaded, setProfileLoaded] = useState(false);
  const [profileTeacherId, setProfileTeacherId] = useState<number | null>(null);
  const [profileRole, setProfileRole] = useState<"admin" | "teacher">("admin");

  useEffect(() => {
    try {
      const savedProfile = localStorage.getItem("uso-user-profile");
      if (savedProfile) {
        const profile = JSON.parse(savedProfile);
        if (profile?.role === "admin" || profile?.role === "teacher") {
          setProfileRole(profile.role);
          setProfileTeacherId(Number(profile.teacherId) || null);
        }
      }
    } catch {
      localStorage.removeItem("uso-user-profile");
    } finally {
      setProfileLoaded(true);
    }
  }, []);

  useEffect(() => {
    async function load() {
      try {
        if (!API) throw new Error("Не задан NEXT_PUBLIC_API_URL для frontend.");
        const paths = ["/teachers/", "/lessons/", "/subjects/", "/student-groups/", "/rooms/"];
        const responses = await Promise.all(paths.map((path) => fetch(`${API}${path}`)));
        const failed = responses.find((response) => !response.ok);
        if (failed) throw new Error(`Не удалось загрузить данные: HTTP ${failed.status}`);
        const [teacherData, lessonData, subjectData, groupData, roomData] = await Promise.all(
          responses.map((response) => response.json())
        );
        setTeachers(Array.isArray(teacherData) ? teacherData : []);
        setLessons(Array.isArray(lessonData) ? lessonData : []);
        setSubjects(Array.isArray(subjectData) ? subjectData : []);
        setGroups(Array.isArray(groupData) ? groupData : []);
        setRooms(Array.isArray(roomData) ? roomData : []);
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
              <NavItem href="/settings" label="Настройки" icon={<Users className="h-[18px] w-[18px]" />} />
              <NavItem href="/about-system" label="О системе" icon={<Info className="h-[18px] w-[18px]" />} />
            </div>
          </nav>
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
                  admin@usurt.ru
                </div>
              </div>
            </div>
          </div>
        </aside>

        <main className="min-w-0 flex-1">
          <header className="relative flex min-h-[88px] items-center justify-between border-b border-slate-200 bg-white px-5 py-4 sm:px-8">
            <div className="flex-1" />
            <div className="absolute left-1/2 max-w-[58%] -translate-x-1/2 text-center"><h1 className="text-lg font-semibold tracking-tight sm:text-xl">Преподаватели</h1><p className="mt-1 hidden text-sm text-slate-400 sm:block">Список преподавателей, их дисциплин и учебных групп</p></div>
            <div className="flex flex-1 justify-end"><Link href="/" className="hidden items-center gap-2 rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm font-medium text-slate-600 transition hover:bg-slate-50 sm:flex"><ArrowLeft className="h-4 w-4" /> На главную</Link></div>
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
                          <TeacherConditionsForm
                            teacher={teacher}
                            rooms={rooms}
                            editable={profileLoaded && (profileRole === "admin" || profileTeacherId === teacher.id)}
                            onSaved={(conditions) => setTeachers((items) => items.map((item) => item.id === teacher.id ? { ...item, ...conditions } : item))}
                          />
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
      <span className={"text-emerald-600"}>{icon}</span>
      <span>{label}</span>
      {active && <span className="ml-auto h-1.5 w-1.5 rounded-full bg-white" />}
    </Link>
  );
}


function TeacherConditionsForm({ teacher, rooms, editable, onSaved }: {
  teacher: Teacher; rooms: Room[]; editable: boolean; onSaved: (value: Conditions) => void;
}) {
  const [draft, setDraft] = useState<Conditions>({
    earliest_start_pair: teacher.earliest_start_pair ?? 1,
    max_floor: teacher.max_floor ?? null,
    prefer_near_entrance: teacher.prefer_near_entrance ?? false,
    preferred_rooms_by_type: teacher.preferred_rooms_by_type ?? {},
  });
  useEffect(() => {
    setDraft({ earliest_start_pair: teacher.earliest_start_pair ?? 1,
      max_floor: teacher.max_floor ?? null, prefer_near_entrance: teacher.prefer_near_entrance ?? false,
      preferred_rooms_by_type: teacher.preferred_rooms_by_type ?? {} });
  }, [teacher.id]);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [failed, setFailed] = useState(false);
  const field = "mt-2 block w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm disabled:opacity-60";
  async function save(event: React.FormEvent) {
    event.preventDefault();
    if (!editable || saving) return;
    setSaving(true); setMessage(""); setFailed(false);
    try {
      const response = await fetch(`${API}/teachers/${teacher.id}/conditions`, {
        method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(draft),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(typeof result.detail === "string" ? result.detail : "Не удалось сохранить условия.");
      const verifyResponse = await fetch(`${API}/teachers/`, { cache: "no-store" });
      if (!verifyResponse.ok) throw new Error("Настройки отправлены, но не удалось проверить их сохранение в базе.");
      const persistedTeachers: Teacher[] = await verifyResponse.json();
      const persisted = persistedTeachers.find((item) => item.id === teacher.id);
      if (!persisted) throw new Error("Не удалось найти преподавателя после сохранения.");
      const expected = draft.preferred_rooms_by_type;
      const actual = persisted.preferred_rooms_by_type ?? {};
      const same = ["Лекция", "Практика", "Лабораторная"].every((type) =>
        JSON.stringify([...(expected[type] ?? [])].sort((a, b) => a - b)) ===
        JSON.stringify([...(actual[type] ?? [])].sort((a, b) => a - b))
      );
      if (!same) throw new Error("Сервер не подтвердил сохранение выбранных аудиторий.");
      const confirmed = { earliest_start_pair: persisted.earliest_start_pair, max_floor: persisted.max_floor,
        prefer_near_entrance: persisted.prefer_near_entrance, preferred_rooms_by_type: actual };
      setDraft(confirmed);
      onSaved(confirmed);
      setMessage(result.affected_entries
        ? `Условия сохранены. В текущем расписании ${result.affected_entries} занятий нарушают ограничения. Выполните оптимизацию обеих недель и проверьте результат.`
        : "Условия сохранены. Они будут учтены при следующем составлении и оптимизации расписания.");
    } catch (error) {
      setFailed(true); setMessage(error instanceof Error ? error.message : "Ошибка сохранения.");
    } finally { setSaving(false); }
  }
  return <form onSubmit={save} className="mt-5 rounded-xl border border-slate-200 bg-white p-4">
    <h3 className="text-sm font-semibold text-slate-900">Условия расписания</h3>
    <p className="mt-1 text-xs leading-5 text-slate-500">Действуют каждый учебный день, на обеих неделях. Сохранение условий не изменяет занятия автоматически.</p>
    <fieldset disabled={!editable || saving} className="mt-4 space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="text-sm font-medium">Начинать занятия не раньше
          <select value={draft.earliest_start_pair} onChange={(event) => setDraft({ ...draft, earliest_start_pair: Number(event.target.value) })} className={field}>
            <option value={1}>1-й пары — 08:30</option><option value={2}>2-й пары — 10:15</option><option value={3}>3-й пары — 12:00</option>
          </select>
        </label>
        <label className="text-sm font-medium">Максимальный этаж
          <select value={draft.max_floor ?? ""} onChange={(event) => setDraft({ ...draft, max_floor: event.target.value ? Number(event.target.value) : null })} className={field}>
            <option value="">Без ограничения</option><option value={1}>Не выше 1-го этажа</option><option value={2}>Не выше 2-го этажа</option><option value={3}>Не выше 3-го этажа</option><option value={4}>Не выше 4-го этажа</option>
          </select>
        </label>
      </div>
      <label className="flex items-start gap-3 text-sm"><input type="checkbox" className="mt-1 h-4 w-4" checked={draft.prefer_near_entrance} onChange={(event) => setDraft({ ...draft, prefer_near_entrance: event.target.checked })} />
        <span>Предпочитать аудитории ближе ко входу<span className="mt-1 block text-xs leading-5 text-slate-500">Вход у охраны Главного корпуса. Среди подходящих аудиторий выбираются ближайшие по времени пути. Переходы между парами могут стать длиннее.</span></span>
      </label>
      <p className="text-xs leading-5 text-slate-500">Время начала и этаж — обязательные ограничения. Если подходящей аудитории или свободного времени нет, система покажет причину. Оптимизация переносит ранние занятия на свободные пары того же дня; при неудаче потребуется пересоставить расписание.</p>
    </fieldset>
      <section className="mt-4 space-y-3" aria-label="Предпочтения по аудиториям">
        <h4 className="text-sm font-semibold">Предпочтительные аудитории по типу занятия</h4>
        {!editable && <p role="alert" className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">Выбор аудиторий сейчас недоступен: профиль преподавателя не совпадает с этой карточкой. Для изменения выберите свой профиль или профиль администратора на главной странице.</p>}
        {!rooms.length && <p role="alert" className="rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-800">Список аудиторий пуст. Проверьте подключение к API аудиторий.</p>}
        <p className="text-xs leading-5 text-slate-500">Можно выбрать несколько равнозначных вариантов. Пустой список означает любую подходящую аудиторию. Выбранные аудитории имеют приоритет перед близостью ко входу и сокращением переходов, но не отменяют требования к оборудованию, вместимости, этажу и допустимым перерывам. Если они недоступны, система подберёт другую подходящую аудиторию.</p>
        {[["Лекция", "Лекции"], ["Практика", "Практические занятия"], ["Лабораторная", "Лабораторные занятия"]].map(([type, label]) =>
          <RoomPreferencePicker key={type} label={label} rooms={rooms} disabled={!editable || saving}
            selected={draft.preferred_rooms_by_type[type] ?? []}
            onChange={(ids) => setDraft((value) => ({ ...value, preferred_rooms_by_type: { ...value.preferred_rooms_by_type, [type]: ids } }))} />
        )}
      </section>
    <fieldset disabled={!editable || saving} className="mt-4">
      {editable && <div className="flex flex-wrap gap-3">
        <button type="submit" className="rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-medium text-white disabled:opacity-50">{saving ? "Сохраняем…" : "Сохранить условия"}</button>
        <button type="button" onClick={() => { setDraft({ earliest_start_pair: 1, max_floor: null, prefer_near_entrance: false, preferred_rooms_by_type: {} }); setMessage("Ограничения сброшены в форме. Нажмите «Сохранить условия»."); setFailed(false); }} className="rounded-xl border border-slate-300 px-4 py-2.5 text-sm">Сбросить</button>
      </div>}
    </fieldset>
    {message && <p role={failed ? "alert" : "status"} className={`mt-3 text-sm ${failed ? "text-red-700" : "text-slate-700"}`}>{message}</p>}
  </form>;
}


function RoomPreferencePicker({ label, rooms, selected, onChange, disabled }: {
  label: string; rooms: Room[]; selected: number[]; disabled: boolean; onChange: (ids: number[]) => void;
}) {
  const [query, setQuery] = useState("");
  const ordered = [...rooms].sort((a, b) => Number(selected.includes(b.id)) - Number(selected.includes(a.id)) || a.name.localeCompare(b.name, "ru", { numeric: true }));
  const normalize = (value: string) => value.toLocaleLowerCase("ru").replace(/ё/g, "е").replace(/[‐‑–—−]/g, "-").replace(/\s+/g, "");
  const terms = query.trim().split(/\s+/).filter(Boolean).map(normalize);
  const visible = ordered.filter((room) => terms.every((term) => normalize(`${room.name} ${room.building}`).includes(term)));
  return <div className="rounded-xl border border-slate-200 bg-slate-50">
    <div className="px-4 py-3 text-sm font-semibold">{label} · {selected.length ? `Выбрано: ${selected.length}` : "Любая подходящая"}</div>
    <div className="space-y-3 px-4 pb-4">
      {selected.length > 0 && <p className="text-xs text-slate-600">{rooms.filter((room) => selected.includes(room.id)).map((room) => room.name).join(", ")}</p>}
      <input type="search" aria-label={`Поиск аудитории: ${label}`} placeholder="Номер аудитории или корпус…" onKeyDown={(event) => { if (event.key === "Enter") event.preventDefault(); }} value={query} onChange={(event) => setQuery(event.target.value)} className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm" />
      <p role="status" className="text-xs text-slate-500">Найдено: {visible.length} · Выбрано: {selected.length}{disabled ? " · Только просмотр" : ""}</p>
      <div className="max-h-60 space-y-1 overflow-y-auto">
        {visible.map((room) => <label key={room.id} className="flex items-center gap-3 rounded-lg p-2 text-sm hover:bg-white">
          <input type="checkbox" disabled={disabled} checked={selected.includes(room.id)} onChange={(event) => onChange(event.target.checked ? Array.from(new Set([...selected, room.id])) : selected.filter((id) => id !== room.id))} className="h-4 w-4" />
          <span><strong>{room.name}</strong><span className="block text-xs text-slate-500">{room.building} · этаж {room.floor} · мест: {room.capacity}</span></span>
        </label>)}
        {!visible.length && <p className="py-2 text-sm text-slate-500">Аудитории не найдены.</p>}
      </div>
      {selected.length > 0 && <button type="button" disabled={disabled} onClick={() => onChange([])} className="text-sm font-medium text-slate-700 underline">Снять выбор для этого типа</button>}
    </div>
  </div>;
}
