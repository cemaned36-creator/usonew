"use client";

import Link from "next/link";
import BrandLogo from "@/components/BrandLogo";
import {
  ArrowLeft,
  BookOpen,
  CalendarDays,
  GraduationCap,
  Info,
  Settings,
  Sparkles,
  Users,
} from "lucide-react";

export default function AboutSystemPage() {
  return (
    <div className="min-h-screen bg-[#f7f8fa] text-slate-900">
      <div className="flex min-h-screen">
        <aside className="hidden w-[250px] shrink-0 flex-col border-r border-slate-200 bg-white lg:flex">
          <BrandLogo />
          <nav className="flex-1 px-3 py-5">
            <p className="mb-3 px-3 text-[11px] font-semibold uppercase tracking-wider text-slate-400">Основное</p>
            <div className="space-y-1">
              <Link href="/" className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-slate-500 transition hover:bg-slate-50 hover:text-slate-900"><GraduationCap className="h-[18px] w-[18px] text-emerald-600" />Главная страница</Link>
              <Link href="/weekly-schedule" className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-slate-500 transition hover:bg-slate-50 hover:text-slate-900"><CalendarDays className="h-[18px] w-[18px] text-emerald-600" />Расписание</Link>
              <Link href="/teachers" className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-slate-500 transition hover:bg-slate-50 hover:text-slate-900"><Users className="h-[18px] w-[18px] text-emerald-600" />Преподаватели</Link>
              <Link href="/optimization" className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-slate-500 transition hover:bg-slate-50 hover:text-slate-900"><Sparkles className="h-[18px] w-[18px] text-emerald-600" />Оптимизация</Link>
            </div>
            <p className="mb-3 mt-8 px-3 text-[11px] font-semibold uppercase tracking-wider text-slate-400">Система</p>
            <div className="space-y-1">
              <Link href="#" className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-slate-500 transition hover:bg-slate-50 hover:text-slate-900"><Settings className="h-[18px] w-[18px]" />Настройки</Link>
              <Link href="/about-system" aria-current="page" className="flex items-center gap-3 rounded-xl bg-slate-900 px-3 py-2.5 text-sm font-medium text-white"><Info className="h-[18px] w-[18px] text-emerald-400" />О системе<span className="ml-auto h-1.5 w-1.5 rounded-full bg-white" /></Link>
            </div>
          </nav>
          <div className="border-t border-slate-200 p-4"><div className="rounded-xl bg-slate-50 p-3"><div className="text-sm font-medium text-slate-800">University Schedule Optimizer</div><div className="mt-1 text-xs text-slate-400">Управление расписанием</div></div></div>
        </aside>

        <main className="min-w-0 flex-1">
          <header className="flex min-h-[88px] items-center justify-between border-b border-slate-200 bg-white px-5 py-4 sm:px-8">
            <div className="flex-1" />
            <div className="text-center"><h1 className="text-lg font-semibold tracking-tight sm:text-xl">О системе</h1><p className="mt-1 hidden text-sm text-slate-400 sm:block">University Schedule Optimizer</p></div>
            <div className="flex flex-1 justify-end"><Link href="/" className="hidden items-center gap-2 rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm font-medium text-slate-600 transition hover:bg-slate-50 sm:flex"><ArrowLeft className="h-4 w-4" />На главную</Link></div>
          </header>

          <div className="mx-auto max-w-5xl space-y-5 px-5 py-6 sm:px-8">
            <section className="rounded-2xl border border-slate-200 bg-white p-6 sm:p-8">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-50"><BookOpen className="h-6 w-6 text-emerald-700" /></div>
              <h2 className="mt-5 text-xl font-semibold">University Schedule Optimizer</h2>
              <p className="mt-3 max-w-3xl text-sm leading-7 text-slate-600">Система управления и оптимизации университетского расписания. Она помогает просматривать занятия по дням недели, работать с данными преподавателей и учебных групп, импортировать расписание из Excel и анализировать варианты распределения занятий по аудиториям.</p>
            </section>
            <section className="grid gap-4 sm:grid-cols-2">
              <div className="rounded-2xl border border-slate-200 bg-white p-5"><CalendarDays className="h-5 w-5 text-emerald-700" /><h3 className="mt-3 text-sm font-semibold">Недельное расписание</h3><p className="mt-2 text-sm leading-6 text-slate-500">Просмотр занятий по дням, выбор недели, фильтрация по преподавателю, ручное добавление и импорт из Excel.</p><Link href="/weekly-schedule" className="mt-4 inline-flex text-sm font-medium text-slate-800 hover:text-emerald-700">Перейти к расписанию →</Link></div>
              <div className="rounded-2xl border border-slate-200 bg-white p-5"><Users className="h-5 w-5 text-emerald-700" /><h3 className="mt-3 text-sm font-semibold">Преподаватели</h3><p className="mt-2 text-sm leading-6 text-slate-500">Поиск преподавателей и просмотр связанных с ними дисциплин и учебных групп.</p><Link href="/teachers" className="mt-4 inline-flex text-sm font-medium text-slate-800 hover:text-emerald-700">Открыть преподавателей →</Link></div>
              <div className="rounded-2xl border border-slate-200 bg-white p-5 sm:col-span-2"><Sparkles className="h-5 w-5 text-emerald-700" /><h3 className="mt-3 text-sm font-semibold">Оптимизация расписания</h3><p className="mt-2 text-sm leading-6 text-slate-500">Подбор подходящих аудиторий и анализ переходов преподавателей между занятиями для выбранного типа недели.</p><Link href="/optimization" className="mt-4 inline-flex text-sm font-medium text-slate-800 hover:text-emerald-700">Перейти к оптимизации →</Link></div>
            </section>
            <p className="px-1 text-xs text-slate-400">Информация на этой странице описывает основные возможности приложения.</p>
          </div>
        </main>
      </div>
    </div>
  );
}
