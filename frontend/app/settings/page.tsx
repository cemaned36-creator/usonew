
"use client";

import Link from "next/link";
import type { ComponentType } from "react";
import {
  LayoutDashboard,
  CalendarDays,
  GraduationCap,
  DoorOpen,
  Sparkles,
  Settings,
  Info,
} from "lucide-react";

import BrandLogo from "@/components/BrandLogo";
import { useAppearance } from "@/components/Appearance";

type SidebarItemProps = {
  icon: ComponentType<{ className?: string; size?: number }>;
  label: string;
  href: string;
  active?: boolean;
};


function SidebarItem({
  icon: Icon,
  label,
  href,
}: SidebarItemProps) {
  const pathname = usePathname();
  const { preferences } = useAppearance();

  const active =
    href === "/"
      ? pathname === "/"
      : pathname === href || pathname.startsWith(`${href}/`);

  const isStrict = preferences.palette === "strict";

  const activeStyles = isStrict
    ? "bg-[#009241]/10 text-[#009241]"
    : "bg-[#FF6F61]/10 text-[#FF6F61]";

  const inactiveStyles =
    "text-slate-600 hover:bg-slate-50 hover:text-slate-900";

  return (
    <Link
      href={href}
      aria-current={active ? "page" : undefined}
      className={`flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-medium transition-colors ${
        active ? activeStyles : inactiveStyles
      }`}
    >
      <Icon size={19} />
      <span>{label}</span>
    </Link>
  );
}


export default function SettingsPage() {
  const { preferences, update } = useAppearance();

  return (
    <div className="min-h-screen bg-[#f7f8fa] text-slate-900">
      <div className="flex min-h-screen">

        {/* SIDEBAR */}
        <aside className="hidden w-[250px] shrink-0 border-r border-slate-200 bg-white lg:flex lg:flex-col">

          {/* Логотип */}
          <BrandLogo />

          {/* Навигация */}
          <nav className="flex-1 px-3 py-5">

            <div className="mb-3 px-3 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
              Основное
            </div>

            <div className="space-y-1">
              <SidebarItem
                icon={LayoutDashboard}
                label="Главная страница"
                href="/"
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
                href="/rooms"
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
                active
              />

              <SidebarItem
                icon={Info}
                label="О системе"
                href="/about-system"
              />
            </div>
          </nav>

          {/* Профиль пользователя */}
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

        {/* ОСНОВНОЕ СОДЕРЖИМОЕ */}
        <div className="min-w-0 flex-1">

          {/* Заголовок */}
          <header className="flex h-[88px] items-center justify-center border-b border-slate-200 bg-white">
            <h1 className="text-xl font-semibold">
              Настройки
            </h1>
          </header>

          {/* Настройки внешнего вида */}
          <main className="p-5 sm:p-8">
            <section className="max-w-3xl space-y-6 rounded-2xl border border-slate-200 bg-white p-6">

              <h2 className="text-lg font-semibold">
                Внешний вид
              </h2>

              {/* Оформление */}
              <label className="block">
                <span className="text-sm font-medium">
                  Оформление
                </span>

                <select
                  className="mt-2 block w-full rounded-xl border border-slate-200 bg-white p-3"
                  value={preferences.palette}
                  onChange={(e) =>
                    update({
                      palette: e.target.value as "strict" | "soft",
                    })
                  }
                >
                  <option value="strict">
                    Строгое — ВУЗ
                  </option>

                  <option value="soft">
                    Мягкое — команда
                  </option>
                </select>
              </label>

              {/* Тема */}
              <label className="block">
                <span className="text-sm font-medium">
                  Тема
                </span>

                <select
                  className="mt-2 block w-full rounded-xl border border-slate-200 bg-white p-3"
                  value={preferences.theme}
                  onChange={(e) =>
                    update({
                      theme: e.target.value as "light" | "dark",
                    })
                  }
                >
                  <option value="light">
                    Светлая
                  </option>

                  <option value="dark">
                    Тёмная
                  </option>
                </select>
              </label>

              {/* Плотность на телефоне */}
              <label className="block">
                <span className="text-sm font-medium">
                  Плотность на телефоне
                </span>

                <select
                  className="mt-2 block w-full rounded-xl border border-slate-200 bg-white p-3"
                  value={preferences.density}
                  onChange={(e) =>
                    update({
                      density: e.target.value as "compact" | "airy",
                    })
                  }
                >
                  <option value="compact">
                    Компактная
                  </option>

                  <option value="airy">
                    Просторная
                  </option>
                </select>
              </label>

              {/* Информация */}
              <p className="text-sm text-slate-500">
                На компьютере используется сбалансированная
                плотность. Настройки сохраняются в этом браузере.
              </p>

            </section>
          </main>
        </div>
      </div>
    </div>
  );
}
