"use client";

import { useMemo, useState } from "react";
import { ArrowRight, Clock3, DoorOpen, GraduationCap, Users } from "lucide-react";

type TransitionMetrics = {
  minutes: number | null;
  unknown_transitions: number;
  transition_count: number;
};

type ReportChange = {
  entry_id: number;
  lesson_id: number;
  subject_name: string | null;
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
const metric = (minutes: number | null) => minutes == null ? "Не рассчитано" : `${minutes} мин`;
const savings = (value: number | null) =>
  value == null ? "Не рассчитано" : value > 0 ? `−${value} мин` : value < 0 ? `+${Math.abs(value)} мин` : "Без изменений";

export default function OptimizationReport({ report }: { report: OptimizationDetailedReport }) {
  const [tab, setTab] = useState<Tab>("summary");
  const [teacherFilter, setTeacherFilter] = useState("");
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
  const changedTeachers = report.teachers.filter(item => item.changes_count > 0);
  const allTeacherOptions = report.teachers.filter(item => item.changes_count > 0);

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
              Для части переходов отсутствует корректный маршрут или не хватает времени.
              Итоговые минуты и экономия не рассчитываются, чтобы не показывать ошибочные значения.
            </p>
          )}
          <div className="rounded-xl border border-slate-200 p-4 text-sm text-slate-700">
            <strong>Преподавателей с изменениями:</strong> {report.summary.affected_teachers}.
            Подробные персональные показатели доступны на соседней вкладке.
          </div>
        </div>
      )}

      {tab === "teachers" && (
        <div className="space-y-3">
          {!changedTeachers.length && <p className="text-sm text-slate-500">Изменённых занятий преподавателей нет.</p>}
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
              {(teacher.before.unknown_transitions > 0 || teacher.after.unknown_transitions > 0) && (
                <p className="mt-2 text-xs text-amber-700">Есть переходы без подтверждённого времени; показатели могут быть неполными.</p>
              )}
            </div>
          ))}
        </div>
      )}

      {tab === "groups" && (
        <div className="grid gap-3 md:grid-cols-2">
          {!report.groups.length && <p className="text-sm text-slate-500">Изменений в расписаниях групп нет.</p>}
          {report.groups.map(group => (
            <div key={group.group_id} className="rounded-xl border border-slate-200 p-4">
              <div className="flex items-center gap-2 text-sm font-semibold">
                <Users className="h-4 w-4 text-emerald-700" />
                {group.group_name ?? `Группа #${group.group_id}`}
              </div>
              <p className="mt-2 text-sm text-slate-600">Изменено занятий: {group.changes_count}</p>
              <p className="mt-1 text-xs text-slate-400">Записи: {group.entry_ids.join(", ")}</p>
              <button type="button" onClick={() => { setGroupFilter(String(group.group_id)); setTab("changes"); }}
                className="mt-3 text-sm font-medium text-emerald-700 underline">
                Посмотреть изменения группы
              </button>
            </div>
          ))}
        </div>
      )}

      {tab === "changes" && (
        <div className="space-y-4">
          <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
            <select aria-label="Фильтр по преподавателю" value={teacherFilter} onChange={e => setTeacherFilter(e.target.value)}
              className="min-w-0 rounded-xl border border-slate-300 bg-white p-2.5 text-sm">
              <option value="">Все преподаватели</option>
              {allTeacherOptions.map(item => <option key={item.teacher_id} value={item.teacher_id}>{item.teacher_name ?? item.teacher_id}</option>)}
            </select>
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
                  <p className="mt-1 text-xs text-slate-500">
                    {DAYS[change.weekday] ?? `День ${change.weekday}`} · {change.teacher_name ?? `Преподаватель #${change.teacher_id}`}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">{change.groups.map(group => group.name + (group.subgroup_number ? ` (подгруппа ${group.subgroup_number})` : "")).join(", ")}</p>
                </div>
                <div className="flex flex-wrap gap-1">
                  {change.change_types.includes("room") && <span className="rounded-lg bg-blue-50 px-2 py-1 text-xs text-blue-800">Аудитория</span>}
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
                      <p className="mt-1 text-slate-500">Эти локальные показатели могут пересекаться с показателями соседних занятий и не суммируются.</p>
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
          {(teacherFilter || groupFilter || typeFilter !== "all" || dayFilter !== "all") && (
            <button type="button" className="text-sm font-medium text-emerald-700 underline"
              onClick={() => { setTeacherFilter(""); setGroupFilter(""); setTypeFilter("all"); setDayFilter("all"); }}>
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
  return (
    <div className="rounded-xl bg-slate-50 p-3">
      <span className="text-xs font-semibold text-slate-500">{label}</span>
      <p className="mt-1 flex items-center gap-1 text-sm font-medium"><Clock3 className="h-3.5 w-3.5" />{start}–{end}</p>
      <p className="mt-1 flex items-center gap-1 text-sm text-slate-600"><DoorOpen className="h-3.5 w-3.5" />{room}</p>
    </div>
  );
}
