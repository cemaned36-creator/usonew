"use client";

import LessonTypeBadge from "@/components/LessonTypeBadge";
import { useId, useMemo, useState } from "react";
import { ArrowRight, Clock3, DoorOpen, GraduationCap, Users } from "lucide-react";

type TransitionMetrics = {
  minutes: number | null;
  unknown_transitions: number;
  transition_count: number;
  known_minutes?: number;
  insufficient_breaks?: number;
  issues?: { previous_entry_id: number; current_entry_id: number; required_minutes: number | null; available_minutes: number; kind: string }[];
};

type ReportChange = {
  entry_id: number;
  lesson_id: number;
  subject_name: string | null;
  lesson_type?: string | null;
  teacher_id: number;
  teacher_name: string | null;
  groups: { id: number; name: string; subgroup_number: number }[];
  weekday: number;
  change_types: ("room" | "time")[];
  before: { room_id: number; room_name: string; start_time: string; end_time: string };
  after: { room_id: number; room_name: string; start_time: string; end_time: string };
  reason: string;
  reason_verified: boolean;
  reasons?: { code: string; verified: boolean; text: string }[];
  adjacent_transitions?: {
    before: TransitionMetrics;
    after: TransitionMetrics;
    saved_minutes: number | null;
    additive: boolean;
  };
};

type GroupScheduleLesson = {
  entry_id: number;
  lesson_id: number;
  pair_number: number | null;
  start_time: string;
  end_time: string;
  room_name: string | null;
  teacher_name: string | null;
  subject_name: string | null;
  lesson_type?: string | null;
  changed: boolean;
};

type GroupScheduleDay = {
  weekday: number;
  lessons: GroupScheduleLesson[];
};

type GroupTimetable = {
  before: GroupScheduleDay[];
  after: GroupScheduleDay[];
};

type GroupDayQuality = {
  weekday: number;
  lessons: number;
  occupied_pairs: number;
  windows: number | null;
  span_minutes: number;
  teaching_minutes?: number;
  first_pair: number | null;
  last_pair: number | null;
  unknown_pair_entries: number;
};

type GroupWeekQuality = {
  days_with_lessons: number;
  lesson_entries: number;
  occupied_pairs: number;
  windows: number | null;
  span_minutes: number;
  weekly_span_minutes?: number;
  average_day_span_minutes?: number;
  longest_day_span_minutes?: number;
  teaching_minutes?: number;
  latest_pair: number | null;
  unknown_pair_entries: number;
  days: GroupDayQuality[];
};

export type OptimizationDetailedReport = {
  version: number;
  summary: {
    changed_entries: number;
    room_changes: number;
    time_changes: number;
    affected_teachers: number;
    affected_groups: number;
    transition_time_before: number | null;
    transition_time_after: number | null;
    time_saved: number | null;
    transition_metrics_complete: boolean;
    insufficient_breaks_before?: number;
    insufficient_breaks_after?: number;
  };
  teachers: {
    teacher_id: number;
    teacher_name: string | null;
    changes_count: number;
    before: TransitionMetrics;
    after: TransitionMetrics;
    delta_minutes: number | null;
    time_saved: number | null;
  }[];
  groups: {
    group_id: number;
    group_name: string | null;
    changes_count: number;
    entry_ids: number[];
    before?: GroupWeekQuality;
    after?: GroupWeekQuality;
    window_delta?: number | null;
    span_delta_minutes?: number;
    impact?: "improved" | "worsened" | "mixed" | "unchanged" | "unknown";
    timetable?: GroupTimetable;
  }[];
  student_impact?: { improved: number; worsened: number; mixed: number; unchanged: number; unknown: number };
  student_warnings?: {
    group_id: number;
    group_name: string | null;
    impact: string;
    window_delta: number | null;
    span_delta_minutes: number;
  }[];
  changes: ReportChange[];
};

const DAYS = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"];
type Tab = "summary" | "teachers" | "groups" | "changes";
const tabs: { id: Tab; title: string }[] = [
  { id: "summary", title: "Общий итог" },
  { id: "teachers", title: "Преподаватели" },
  { id: "groups", title: "Группы" },
  { id: "changes", title: "Журнал изменений" },
];
const duration = (minutes: number) => {
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest === 0 ? `${hours} ч` : hours === 0 ? `${rest} мин` : `${hours} ч ${rest} мин`;
};
const metric = (minutes: number | null) => minutes == null ? "Не рассчитано" : `${minutes} мин`;
const savings = (value: number | null) =>
  value == null ? "Не рассчитано" : value > 0 ? `−${value} мин` : value < 0 ? `+${Math.abs(value)} мин` : "Без изменений";

export default function OptimizationReport({ report }: { report: OptimizationDetailedReport }) {
  const [tab, setTab] = useState<Tab>("summary");
  const [teacherFilter, setTeacherFilter] = useState("");
  const teacherOptionsId = useId();
  const [teacherSearch, setTeacherSearch] = useState("");
  const [showTeacherSuggestions, setShowTeacherSuggestions] = useState(false);
  const [groupFilter, setGroupFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("all");
  const [dayFilter, setDayFilter] = useState("all");
  const selectedChanges = useMemo(
    () => report.changes.filter(change =>
      (!teacherFilter || String(change.teacher_id) === teacherFilter) &&
      (!groupFilter || change.groups.some(group => String(group.id) === groupFilter)) &&
      (typeFilter === "all" || change.change_types.includes(typeFilter as "room" | "time")) &&
      (dayFilter === "all" || String(change.weekday) === dayFilter)
    ),
    [report.changes, teacherFilter, groupFilter, typeFilter, dayFilter],
  );
  const changedTeachers = report.teachers.filter(item => item.changes_count > 0 || item.before.unknown_transitions > 0 || item.after.unknown_transitions > 0 || (item.before.insufficient_breaks ?? 0) > 0 || (item.after.insufficient_breaks ?? 0) > 0);
  const allTeacherOptions = report.teachers.filter(item => item.changes_count > 0);
  const filteredTeachers = allTeacherOptions.filter(item => (item.teacher_name ?? `Преподаватель #${item.teacher_id}`).toLocaleLowerCase("ru").includes(teacherSearch.trim().toLocaleLowerCase("ru")));

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4 sm:p-6">
      <div className="mb-5">
        <h2 className="text-lg font-semibold text-slate-900">Подробный обзор изменений</h2>
        <p className="mt-1 text-sm text-slate-500">
          Сравнение рассчитано для предварительного плана. Пока изменения не подтверждены, база данных не меняется.
        </p>
      </div>
      <div role="tablist" aria-label="Разделы отчёта" className="mb-5 flex flex-wrap gap-2">
        {tabs.map(item => (
          <button key={item.id} type="button" role="tab" aria-selected={tab === item.id}
            onClick={() => setTab(item.id)}
            className={`rounded-xl px-3 py-2 text-sm font-semibold transition ${tab === item.id ? "bg-slate-900 text-white" : "border border-slate-200 text-slate-600 hover:bg-slate-50"}`}>
            {item.title}
          </button>
        ))}
      </div>

      {tab === "summary" && (
        <div className="space-y-5">
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            {[
              ["Изменено занятий", String(report.summary.changed_entries)],
              ["Заменено аудиторий", String(report.summary.room_changes)],
              ["Перенесено по времени", String(report.summary.time_changes)],
              ["Затронуто групп", String(report.summary.affected_groups)],
            ].map(([title, value]) => (
              <div key={title} className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                <p className="text-xs text-slate-500">{title}</p>
                <p className="mt-2 text-2xl font-bold text-slate-900">{value}</p>
              </div>
            ))}
          </div>
          <div className="grid gap-3 sm:grid-cols-3">
            <SummaryMetric label="Переходы до" value={metric(report.summary.transition_time_before)} />
            <SummaryMetric label="Переходы после" value={metric(report.summary.transition_time_after)} />
            <SummaryMetric label="Изменение времени" value={savings(report.summary.time_saved)} />
          </div>
          {!report.summary.transition_metrics_complete && (
            <p className="rounded-xl bg-amber-50 p-3 text-sm text-amber-800">
              В одной из версий расписания есть переходы с неизвестным временем. Полная сумма для этой версии и экономия не рассчитаны. Доступный показатель другой версии сохранён.
            </p>
          )}
          {((report.summary.insufficient_breaks_before ?? 0) > 0 || (report.summary.insufficient_breaks_after ?? 0) > 0) && (
            <p className="rounded-xl bg-amber-50 p-3 text-sm text-amber-800">Переходов с недостаточным перерывом: до — {report.summary.insufficient_breaks_before ?? 0}, после — {report.summary.insufficient_breaks_after ?? 0}. В этих случаях путь занимает больше времени, чем перерыв между парами. Время пути учтено в итогах; сохранить план можно только после проверки всех ограничений.</p>
          )}
          {report.student_impact && (
            <div className="space-y-3 rounded-xl border border-slate-200 p-4">
              <h3 className="text-sm font-semibold text-slate-800">Влияние на расписания групп</h3>
              <div className="flex flex-wrap gap-2 text-xs">
                <span className="rounded-lg bg-emerald-50 px-3 py-2 text-emerald-800">Улучшено: {report.student_impact.improved}</span>
                <span className="rounded-lg bg-rose-50 px-3 py-2 text-rose-800">Ухудшено: {report.student_impact.worsened}</span>
                <span className="rounded-lg bg-slate-100 px-3 py-2">Без изменений: {report.student_impact.unchanged}</span>
                <span className="rounded-lg bg-amber-50 px-3 py-2 text-amber-800">Смешанный эффект: {report.student_impact.mixed}</span>
                {report.student_impact.unknown > 0 && <span className="rounded-lg bg-slate-100 px-3 py-2">Неизвестно: {report.student_impact.unknown}</span>}
              </div>
              {report.student_impact.mixed > 0 && <p className="text-xs leading-5 text-slate-600">Смешанный эффект: у группы стало меньше окон, но выросла суммарная длительность учебных дней за неделю, или наоборот.</p>}
              {!!report.student_warnings?.length && (
                <div role="status" className="rounded-xl bg-amber-50 p-3 text-xs leading-5 text-amber-900">
                  <p className="font-semibold">Есть ухудшения в расписаниях групп</p>
                  {report.student_warnings.map(warning => (
                    <p key={warning.group_id} className="mt-1">
                      {warning.group_name ?? `Группа #${warning.group_id}`}: 
                      {warning.window_delta != null && warning.window_delta > 0 ? ` +${warning.window_delta} окон` : ""}
                      {warning.span_delta_minutes > 0 ? ` +${duration(warning.span_delta_minutes)} учебного времени` : ""}
                    </p>
                  ))}
                  <p className="mt-2 text-amber-800">Это предупреждение, не запрет на сохранение. Условия преподавателей остаются приоритетными.</p>
                </div>
              )}
            </div>
          )}
          <div className="rounded-xl border border-slate-200 p-4 text-sm text-slate-700">
            <strong>Преподавателей с изменениями:</strong> {report.summary.affected_teachers}.
            Подробные персональные показатели доступны на соседней вкладке.
          </div>
        </div>
      )}

      {tab === "teachers" && (
        <div className="space-y-3">
          {!changedTeachers.length && <p className="text-sm text-slate-500">Изменений и проблем с переходами преподавателей нет.</p>}
          {changedTeachers.map(teacher => (
            <div key={teacher.teacher_id} className="rounded-xl border border-slate-200 p-4">
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2 text-sm font-semibold">
                  <GraduationCap className="h-4 w-4 text-emerald-700" />
                  {teacher.teacher_name ?? `Преподаватель #${teacher.teacher_id}`}
                </div>
                <span className="rounded-lg bg-slate-100 px-2.5 py-1 text-xs">{teacher.changes_count} занятий изменено</span>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <SummaryMetric label="До" value={metric(teacher.before.minutes)} />
                <SummaryMetric label="После" value={metric(teacher.after.minutes)} />
                <SummaryMetric label="Экономия / рост" value={savings(teacher.time_saved)} />
              </div>
            </div>
          ))}
        </div>
      )}

      {tab === "groups" && (
        <div className="space-y-4">
          <p className="text-sm leading-6 text-slate-500">
            Окно — свободная пара между занятиями. Длительность учебного дня —
            от начала первой до конца последней пары, включая перемены.
            Параллельные подгруппы считаются одним занятым временным слотом.
            «Учебная неделя» — сумма длительностей дней, а не продолжительность одного дня.
            Чистое время занятий не включает перемены и окна.
          </p>
          {!report.groups.length && <p className="text-sm text-slate-500">Изменений в расписаниях групп нет.</p>}
          {report.groups.map(group => (
            <article key={group.group_id} className="rounded-xl border border-slate-200 p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="flex items-center gap-2 text-sm font-semibold">
                  <Users className="h-4 w-4 text-emerald-700" />
                  {group.group_name ?? `Группа #${group.group_id}`}
                </h3>
                <span className={`rounded-lg px-2.5 py-1 text-xs font-medium ${
                  group.impact === "improved" ? "bg-emerald-50 text-emerald-800" :
                  group.impact === "worsened" ? "bg-rose-50 text-rose-800" :
                  "bg-slate-100 text-slate-600"
                }`}>
                  {group.impact === "improved" ? "Улучшено" :
                    group.impact === "worsened" ? "Ухудшено" :
                    group.impact === "mixed" ? "Смешанный эффект" :
                    group.impact === "unknown" ? "Не все пары распознаны" : "Без изменений"}
                </span>
              </div>
              <p className="mt-2 text-sm text-slate-600">Изменено занятий: {group.changes_count}</p>
              {group.timetable && <GroupTimetableComparison timetable={group.timetable} />}
              {group.before && group.after && (
                <details className="mt-3 rounded-xl border border-slate-200 p-3">
                  <summary className="cursor-pointer text-sm font-semibold text-slate-800">Показатели группы: окна и длительность занятий</summary>
                  <div className="mt-3 space-y-3">
                  <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                    <SummaryMetric label="Окон до" value={group.before.windows == null ? "—" : String(group.before.windows)} />
                    <SummaryMetric label="Окон после" value={group.after.windows == null ? "—" : String(group.after.windows)} />
                    <SummaryMetric label="Неделя до (с переменами)" value={duration(group.before.weekly_span_minutes ?? group.before.span_minutes)} />
                    <SummaryMetric label="Неделя после (с переменами)" value={duration(group.after.weekly_span_minutes ?? group.after.span_minutes)} />
                    <SummaryMetric label="Средний учебный день до" value={group.before.average_day_span_minutes == null ? "—" : duration(group.before.average_day_span_minutes)} />
                    <SummaryMetric label="Средний учебный день после" value={group.after.average_day_span_minutes == null ? "—" : duration(group.after.average_day_span_minutes)} />
                    <SummaryMetric label="Самый длинный день до" value={group.before.longest_day_span_minutes == null ? "—" : duration(group.before.longest_day_span_minutes)} />
                    <SummaryMetric label="Самый длинный день после" value={group.after.longest_day_span_minutes == null ? "—" : duration(group.after.longest_day_span_minutes)} />
                    <SummaryMetric label="Чистое время занятий до" value={group.before.teaching_minutes == null ? "—" : duration(group.before.teaching_minutes)} />
                    <SummaryMetric label="Чистое время занятий после" value={group.after.teaching_minutes == null ? "—" : duration(group.after.teaching_minutes)} />
                  </div>
                  <details className="rounded-xl border border-slate-200 p-3">
                    <summary className="cursor-pointer text-sm font-medium text-slate-700">Сравнение по дням недели</summary>
                    <div className="mt-3 space-y-2">
                      {group.before.days.map(day => {
                        const next = group.after!.days.find(item => item.weekday === day.weekday);
                        if (!next || (!day.lessons && !next.lessons)) return null;
                        return (
                          <div key={day.weekday} className="rounded-lg bg-slate-50 p-3 text-xs text-slate-700">
                            <p className="font-semibold">{DAYS[day.weekday]}</p>
                            <p className="mt-1">Окна: {day.windows ?? "—"} → {next.windows ?? "—"}</p>
                            <p>Длительность дня (с переменами): {duration(day.span_minutes)} → {duration(next.span_minutes)}</p>
                            <p>Чистое время занятий: {day.teaching_minutes == null ? "—" : duration(day.teaching_minutes)} → {next.teaching_minutes == null ? "—" : duration(next.teaching_minutes)}</p>
                            <p>Первая / последняя пара: {day.first_pair ?? "—"} / {day.last_pair ?? "—"} → {next.first_pair ?? "—"} / {next.last_pair ?? "—"}</p>
                          </div>
                        );
                      })}
                    </div>
                  </details>
                  </div>
                </details>
              )}
              <button type="button" onClick={() => { setGroupFilter(String(group.group_id)); setTab("changes"); }}
                className="mt-3 text-sm font-medium text-emerald-700 underline">
                Посмотреть изменения группы
              </button>
            </article>
          ))}
        </div>
      )}

      {tab === "changes" && (
        <div className="space-y-4">
          <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
            <div className="relative min-w-0">
              <label htmlFor={teacherOptionsId} className="sr-only">Поиск преподавателя</label>
              <input id={teacherOptionsId} type="text" value={teacherSearch}
                onChange={event => { setTeacherSearch(event.target.value); setTeacherFilter(""); setShowTeacherSuggestions(true); }}
                onFocus={() => setShowTeacherSuggestions(true)}
                onBlur={() => { setTimeout(() => setShowTeacherSuggestions(false), 150); }}
                onKeyDown={event => { if (event.key === "Escape") setShowTeacherSuggestions(false); }}
                placeholder="Поиск преподавателя..." autoComplete="off"
                className="block w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm font-medium text-slate-900 outline-none transition placeholder:text-slate-400 hover:border-slate-400 focus:border-slate-900 focus:ring-2 focus:ring-slate-900/10" />
              {showTeacherSuggestions && teacherSearch.trim() !== "" && (
                <div className="absolute left-0 right-0 top-full z-20 mt-1 max-h-60 overflow-y-auto rounded-xl border border-slate-200 bg-white py-1 shadow-lg">
                  {filteredTeachers.length > 0 ? filteredTeachers.map(teacher => (
                    <button key={teacher.teacher_id} type="button"
                      className="block w-full px-4 py-3 text-left text-sm text-slate-700 hover:bg-slate-100"
                      onMouseDown={event => event.preventDefault()}
                      onClick={() => {
                        setTeacherFilter(String(teacher.teacher_id));
                        setTeacherSearch(teacher.teacher_name ?? `Преподаватель #${teacher.teacher_id}`);
                        setShowTeacherSuggestions(false);
                      }}>
                      {teacher.teacher_name ?? `Преподаватель #${teacher.teacher_id}`}
                    </button>
                  )) : <p className="px-4 py-3 text-sm text-slate-500">Преподаватели не найдены</p>}
                </div>
              )}
              {teacherFilter && <button type="button"
                onClick={() => { setTeacherFilter(""); setTeacherSearch(""); setShowTeacherSuggestions(false); }}
                className="mt-2 text-xs text-blue-600 hover:text-blue-800">Показать всех преподавателей</button>}
            </div>
            <select aria-label="Фильтр по группе" value={groupFilter} onChange={e => setGroupFilter(e.target.value)}
              className="min-w-0 rounded-xl border border-slate-300 bg-white p-2.5 text-sm">
              <option value="">Все группы</option>
              {report.groups.map(item => <option key={item.group_id} value={item.group_id}>{item.group_name ?? item.group_id}</option>)}
            </select>
            <select aria-label="Фильтр по типу" value={typeFilter} onChange={e => setTypeFilter(e.target.value)}
              className="rounded-xl border border-slate-300 bg-white p-2.5 text-sm">
              <option value="all">Все изменения</option>
              <option value="room">Изменение аудитории</option>
              <option value="time">Изменение времени</option>
            </select>
            <select aria-label="Фильтр по дню" value={dayFilter} onChange={e => setDayFilter(e.target.value)}
              className="rounded-xl border border-slate-300 bg-white p-2.5 text-sm">
              <option value="all">Все дни</option>
              {DAYS.map((day, index) => <option key={day} value={index}>{day}</option>)}
            </select>
          </div>
          <p className="text-xs text-slate-500">Найдено изменений: {selectedChanges.length}</p>
          {!selectedChanges.length && <p className="text-sm text-slate-500">По выбранным фильтрам изменений нет.</p>}
          {selectedChanges.map(change => (
            <article key={change.entry_id} className="rounded-xl border border-slate-200 p-4">
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <div>
                  <h3 className="font-semibold text-slate-900">{change.subject_name ?? `Занятие #${change.lesson_id}`}</h3>
                  <div className="mt-1"><LessonTypeBadge type={change.lesson_type} /></div>
                  <p className="mt-1 text-xs text-slate-500">
                    {DAYS[change.weekday] ?? `День ${change.weekday}`} · {change.teacher_name ?? `Преподаватель #${change.teacher_id}`}
                  </p>
                  <p className="mt-2 inline-block rounded-lg bg-emerald-50 px-3 py-1.5 text-sm font-bold text-emerald-900">{change.groups.map(group => group.name + (group.subgroup_number ? ` (подгруппа ${group.subgroup_number})` : "")).join(", ")}</p>
                </div>
                <div className="flex flex-wrap gap-1">
                  {change.change_types.includes("time") && <span className="rounded-lg bg-amber-50 px-2 py-1 text-xs text-amber-800">Время</span>}
                </div>
              </div>
              <div className="grid gap-2 sm:grid-cols-[1fr_auto_1fr] sm:items-center">
                <Assignment label="До" room={change.before.room_name} start={change.before.start_time} end={change.before.end_time} />
                <ArrowRight className="mx-auto hidden h-4 w-4 text-slate-400 sm:block" />
                <Assignment label="После" room={change.after.room_name} start={change.after.start_time} end={change.after.end_time} />
              </div>
              {change.reasons?.length ? (
                <div className="mt-3 rounded-xl border border-slate-200 bg-slate-50 p-3">
                  <h4 className="text-xs font-semibold text-slate-700">Проверяемые причины и результаты</h4>
                  <ul className="mt-2 space-y-1 text-xs leading-5 text-slate-600">
                    {change.reasons.map((reason, index) => <li key={`${reason.code}-${index}`}>• {reason.text}</li>)}
                  </ul>
                  {change.adjacent_transitions && (
                    <div className="mt-2 border-t border-slate-200 pt-2 text-xs text-slate-600">
                      <p>Переходы непосредственно до и после занятия: {metric(change.adjacent_transitions.before.minutes)} → {metric(change.adjacent_transitions.after.minutes)}.</p>
                      <TransitionProblems stats={change.adjacent_transitions.before} label="До" />
                      <TransitionProblems stats={change.adjacent_transitions.after} label="После" />
                      <p className="mt-1 text-slate-500">Один переход может быть показан в двух соседних карточках. Не складывайте эти значения: общий итог учитывает каждый переход один раз.</p>
                    </div>
                  )}
                </div>
              ) : (
                <p className="mt-3 text-xs text-slate-500">
                  Оптимизация с учётом условий преподавателя и логистики переходов.
                  Причина конкретного назначения в старом отчёте не зафиксирована.
                </p>
              )}
            </article>
          ))}
          {(teacherSearch || teacherFilter || groupFilter || typeFilter !== "all" || dayFilter !== "all") && (
            <button type="button" className="text-sm font-medium text-emerald-700 underline"
              onClick={() => { setTeacherFilter(""); setTeacherSearch(""); setShowTeacherSuggestions(false); setGroupFilter(""); setTypeFilter("all"); setDayFilter("all"); }}>
              Сбросить фильтры
            </button>
          )}
        </div>
      )}
    </section>
  );
}

function SummaryMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 rounded-xl bg-slate-50 p-3">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-1 break-words text-base font-bold text-slate-900 sm:text-lg">{value}</p>
    </div>
  );
}

function Assignment({ label, room, start, end }: { label: string; room: string; start: string; end: string }) {
  const pairs = [["08:30", "10:05"], ["10:15", "11:50"], ["12:00", "13:35"], ["14:30", "16:05"], ["16:15", "17:50"], ["18:00", "19:35"]];
  const pair = pairs.findIndex(([from, to]) => from === start.slice(0, 5) && to === end.slice(0, 5));
  return (
    <div className="rounded-xl bg-slate-50 p-3">
      <span className="text-xs font-semibold text-slate-500">{label}</span>
      <p className="mt-1 flex items-center gap-1 text-sm font-medium"><Clock3 className="h-3.5 w-3.5" />{pair >= 0 ? `${pair + 1}-я пара · ` : "Вне сетки пар · "}{start}–{end}</p>
      <p className="mt-1 flex items-center gap-1 text-sm text-slate-600"><DoorOpen className="h-3.5 w-3.5" />{room}</p>
    </div>
  );
}

function GroupTimetableColumn({ title, days, optimized }: {
  title: string;
  days: GroupScheduleDay[];
  optimized: boolean;
}) {
  return (
    <div className="min-w-0 overflow-hidden rounded-xl border border-slate-200 bg-white">
      <h4 className={`border-b border-slate-200 px-3 py-3 text-sm font-semibold ${
        optimized ? "bg-emerald-50 text-emerald-800" : "bg-slate-50 text-slate-800"
      }`}>{title}</h4>
      <div className="space-y-3 p-2 sm:p-3">
        {days.map(day => (
          <section key={day.weekday} className="overflow-hidden rounded-xl border border-slate-100">
            <div className="flex items-center justify-between bg-slate-50 px-3 py-2">
              <span className="text-xs font-semibold">{DAYS[day.weekday] ?? day.weekday}</span>
              <span className="text-xs text-slate-500">{day.lessons.length} занятий</span>
            </div>
            {!day.lessons.length ? (
              <p className="px-3 py-3 text-xs text-slate-400">Занятий нет</p>
            ) : (
              <div className="divide-y divide-slate-100">
                {day.lessons.map(lesson => (
                  <div key={lesson.entry_id} className={`grid grid-cols-[60px_minmax(0,1fr)] gap-3 px-3 py-3 ${
                    lesson.changed ? (optimized ? "bg-emerald-50" : "bg-amber-50") : ""
                  }`}>
                    <div className="text-xs">
                      <p className="font-semibold">{lesson.pair_number == null ? "—" : `${lesson.pair_number}-я пара`}</p>
                      <p className="mt-1 text-slate-600">{lesson.start_time}</p>
                      <p className="text-slate-400">{lesson.end_time}</p>
                    </div>
                    <div className="min-w-0 space-y-1">
                      <p className="break-words text-sm font-semibold">{lesson.subject_name ?? `Занятие #${lesson.lesson_id}`}</p>
                      <LessonTypeBadge type={lesson.lesson_type} />
                      <p className="break-words text-xs text-slate-500">{lesson.teacher_name ?? "Преподаватель не указан"}</p>
                      <p className="text-xs font-medium text-slate-700">Аудитория: {lesson.room_name ?? "—"}</p>
                      {lesson.changed && <p className="text-xs font-semibold text-emerald-800">Изменено</p>}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        ))}
      </div>
    </div>
  );
}

function TransitionProblems({ stats, label }: { stats: TransitionMetrics; label: string }) {
  if (!(stats.insufficient_breaks || stats.unknown_transitions)) return null;
  return <div className="mt-2 rounded-lg bg-amber-50 p-3 text-xs text-amber-800">
    <p>{label}: неизвестных переходов — {stats.unknown_transitions}; недостаточных перерывов — {stats.insufficient_breaks ?? 0}.</p>
    {stats.unknown_transitions > 0 && stats.known_minutes != null && <p className="mt-1">Известная часть: {stats.known_minutes} мин (не полная сумма).</p>}
    {stats.issues?.map(issue => <p key={`${issue.previous_entry_id}-${issue.current_entry_id}`} className="mt-1">Записи #{issue.previous_entry_id} → #{issue.current_entry_id}: {issue.required_minutes == null ? "маршрут или время доступа неизвестны" : `нужно ${issue.required_minutes} мин, доступно ${issue.available_minutes} мин`}.</p>)}
  </div>;
}

function GroupTimetableComparison({ timetable }: { timetable: GroupTimetable }) {
  const signature = (day?: GroupScheduleDay) => JSON.stringify((day?.lessons ?? [])
    .map(lesson => [lesson.entry_id, lesson.start_time, lesson.end_time, lesson.room_name, lesson.teacher_name, lesson.subject_name])
    .sort((a, b) => Number(a[0]) - Number(b[0])));
  const weekdays = [...new Set([...timetable.before, ...timetable.after].map(day => day.weekday))]
    .filter(weekday => signature(timetable.before.find(day => day.weekday === weekday)) !== signature(timetable.after.find(day => day.weekday === weekday)))
    .sort((a, b) => a - b);
  const days = (source: GroupScheduleDay[]) => weekdays.map(weekday => source.find(day => day.weekday === weekday) ?? { weekday, lessons: [] });
  return <details open className="mt-3 rounded-xl border border-slate-200 p-3">
    <summary className="cursor-pointer text-sm font-semibold text-slate-800">Сравнить расписание: слева до, справа после</summary>
    {weekdays.length ? <div className="mt-3 grid items-start gap-3 2xl:grid-cols-2">
      <GroupTimetableColumn title="До оптимизации" days={days(timetable.before)} optimized={false} />
      <GroupTimetableColumn title="После оптимизации" days={days(timetable.after)} optimized />
    </div> : <p className="mt-3 text-sm text-slate-500">Расписание группы не изменилось.</p>}
  </details>;
}
