"use client";
import { createContext, useContext, useEffect, useState, useSyncExternalStore, useMemo } from "react";
import Link from "next/link";
import { Menu, X } from "lucide-react";

type Preferences = { palette: "strict" | "soft"; theme: "light" | "dark"; density: "compact" | "airy" };
const defaults: Preferences = { palette: "strict", theme: "light", density: "compact" };
const Context = createContext<{ preferences: Preferences; update: (patch: Partial<Preferences>) => void }>({ preferences: defaults, update: () => {} });
let sessionValue = "{}";
const subscribe = (notify: () => void) => { window.addEventListener("uso-appearance", notify); window.addEventListener("storage", notify); return () => { window.removeEventListener("uso-appearance", notify); window.removeEventListener("storage", notify); }; };
const snapshot = () => { try { return localStorage.getItem("uso-appearance") || sessionValue; } catch { return sessionValue; } };
export const useAppearance = () => useContext(Context);
export default function Appearance({ children }: { children: React.ReactNode }) {
  const raw = useSyncExternalStore(subscribe, snapshot, () => "{}");
  const preferences = useMemo<Preferences>(() => {
    try { const p = JSON.parse(raw); return { palette: p?.palette === "soft" ? "soft" : "strict", theme: p?.theme === "dark" ? "dark" : "light", density: p?.density === "airy" ? "airy" : "compact" }; } catch { return defaults; }
  }, [raw]);
  const [menu, setMenu] = useState(false);
  useEffect(() => {
    Object.assign(document.documentElement.dataset, preferences);
  }, [preferences]);
  const update = (patch: Partial<Preferences>) => {
    const next = { ...preferences, ...patch };
    sessionValue = JSON.stringify(next);
    try { localStorage.setItem("uso-appearance", JSON.stringify(next)); } catch { /* Session settings still work. */ }
    window.dispatchEvent(new Event("uso-appearance"));
  };
  return <Context.Provider value={{ preferences, update }}>
    <div className="mobile-navigation"><button aria-label={menu ? "Закрыть меню" : "Открыть меню"} aria-expanded={menu} onClick={() => setMenu(!menu)}>{menu ? <X /> : <Menu />} Меню</button>
    {menu && <nav aria-label="Мобильная навигация">{[["/", "Главная страница"], ["/weekly-schedule", "Расписание"], ["/teachers", "Преподаватели"], ["/optimization", "Оптимизация"], ["/settings", "Настройки"], ["/about-system", "О системе"]].map(([href, label]) => <Link key={href} href={href} onClick={() => setMenu(false)}>{label}</Link>)}</nav>}</div>
    <svg width="0" height="0" aria-hidden="true" style={{position:"absolute"}}><defs><filter id="uso-clean-logo" colorInterpolationFilters="sRGB"><feColorMatrix in="SourceGraphic" type="matrix" values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  -2.126 -7.152 -0.722 0 9" result="mask"/><feComposite in="SourceGraphic" in2="mask" operator="in"/></filter><filter id="uso-white-logo" colorInterpolationFilters="sRGB"><feColorMatrix in="SourceGraphic" type="matrix" values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  -2.126 -7.152 -0.722 0 9"/></filter></defs></svg>
    {children}
  </Context.Provider>;
}

