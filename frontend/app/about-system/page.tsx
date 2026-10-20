"use client";

import Link from "next/link";
import BrandLogo from "@/components/BrandLogo";
import { ArrowLeft, CalendarDays, GraduationCap, Info, Settings, Sparkles, Users } from "lucide-react";

const alyaLogo = "data:image/webp;base64,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";

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
              <img src={alyaLogo} alt="Логотип AlyaIT" className="mx-auto mt-6 h-auto w-full max-w-[320px] object-contain" />
            </section>
          </div>
        </main>
      </div>
    </div>
  );
}
