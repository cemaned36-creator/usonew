"use client";

import Link from "next/link";
import BrandLogo from "@/components/BrandLogo";
import { ArrowLeft, CalendarDays, GraduationCap, Info, Settings, Sparkles, Users } from "lucide-react";

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
        </aside>

        <main className="min-w-0 flex-1">
          <header className="flex min-h-[88px] items-center justify-between border-b border-slate-200 bg-white px-5 py-4 sm:px-8">
            <div className="flex-1" />
            <div className="text-center">
              <h1 className="text-lg font-semibold tracking-tight sm:text-xl">О системе</h1>
              <p className="mt-1 hidden text-sm text-slate-400 sm:block">Оптимизатор расписания УрГУПС</p>
            </div>
            <div className="flex flex-1 justify-end"><Link href="/" className="hidden items-center gap-2 rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm font-medium text-slate-600 transition hover:bg-slate-50 sm:flex"><ArrowLeft className="h-4 w-4" />На главную</Link></div>
          </header>

          <div className="mx-auto max-w-4xl px-5 py-8 sm:px-8">
            <section className="rounded-2xl border border-slate-200 bg-white p-6 sm:p-9">
              <h2 className="text-xl font-semibold">Оптимизатор расписания УрГУПС</h2>
              <p className="mt-4 text-sm leading-7 text-slate-600 sm:text-base">
                Система управления и оптимизации университетского расписания. Она помогает просматривать занятия по дням недели, работать с данными преподавателей и учебных групп, импортировать расписание из Excel и анализировать варианты распределения занятий по аудиториям, учитывая требования к помещениям и переходы преподавателей между корпусами.
              </p>
            </section>

            <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-6 text-center sm:p-9">
              <p className="text-sm leading-7 text-slate-600 sm:text-base">
                Система разработана и развернута командой AlyaIT, факультета ЭТФ УрГУПС 2026 г.
              </p>
              <img src="/alya-it-logo.png.png" alt="Логотип AlyaIT" className="mx-auto mt-6 h-auto w-full max-w-[320px] object-contain" />
            </section>
          </div>
        </main>
      </div>
    </div>
  );
}
