"use client";
import Link from "next/link";
import BrandLogo from "@/components/BrandLogo";
import { useAppearance } from "@/components/Appearance";
export default function SettingsPage() {
  const { preferences, update } = useAppearance();
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

              <SidebarItem
                  icon={Sparkles}
                  label="Оптимизация"
                  href="/optimization"
                />

            </div>

            <div className="mb-3 mt-8 px-3 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
              Система
            </div>

            <div className="space-y-1">

              <SidebarItem
                icon={Settings}
                label="Настройки"
                href="/settings"
              />
              <SidebarItem
                icon={Info}
                label="О системе"
                href="/about-system"
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
                  admin@usurt.ru
                </div>

              </div>

            </div>

          </div>

        </aside>
        
        <div className="min-w-0 flex-1">
          <header className="flex h-[88px] items-center justify-center border-b border-slate-200 bg-white">
            <h1 className="text-xl font-semibold">
              Настройки
            </h1>
          </header><main className="p-5 sm:p-8">
            <section className="max-w-3xl space-y-6 rounded-2xl border border-slate-200 bg-white p-6">
              <h2 className="text-lg font-semibold">
                Внешний вид
              </h2>
              <label className="block">
                Оформление
                <select className="mt-2 block w-full rounded-xl border border-slate-200 p-3" value={preferences.palette} onChange={e=>update({palette:e.target.value as 'strict'|'soft'})}>
                  <option value="strict">
                    Строгое — ВУЗ
                  </option>
                  <option value="soft">
                    Мягкое — команда
                  </option>
                </select>
              </label>
              <label className="block">
                Тема
                <select className="mt-2 block w-full rounded-xl border border-slate-200 p-3" value={preferences.theme} onChange={e=>update({theme:e.target.value as 'light'|'dark'})}>
                  <option value="light">
                    Светлая
                  </option>
                  <option value="dark">
                    Тёмная
                  </option>
                </select>
              </label>
              <label className="block">
                Плотность на телефоне
                <select className="mt-2 block w-full rounded-xl border border-slate-200 p-3" value={preferences.density} onChange={e=>update({density:e.target.value as 'compact'|'airy'})}>
                  <option value="compact">
                    Компактная
                  </option>
                  <option value="airy">
                    Просторная
                  </option>
                </select>
              </label>
              <p className="text-sm text-slate-500">
                На компьютере используется сбалансированная плотность. Настройки сохраняются в этом браузере.
              </p>
            </section>
          </main>
        </div>
      </div>;
      }
