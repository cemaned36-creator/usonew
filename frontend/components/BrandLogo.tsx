"use client";
import { useAppearance } from "./Appearance";
import Image from "next/image";
import Link from "next/link";

export default function BrandLogo() {
  const { preferences } = useAppearance();
  return (
    <Link
      href="/"
      aria-label="УрГУПС — Оптимизатор расписания by AlyaIT"
      className="brand-logo-link flex h-[88px] min-h-[88px] w-full items-center gap-3 overflow-hidden border-b border-slate-200 px-3"
    >
      <Image
        src={preferences.palette === "soft" ? "/alyait-logo.png" : "/urguups-logo.jpg.jpg"}
        alt={preferences.palette === "soft" ? "Логотип AlyaIT" : "Логотип УрГУПС"}
        width={116}
        height={72}
        priority
        className="brand-image h-[68px] w-[112px] shrink-0 object-contain"
      />
      <div className="min-w-0">
        <div className="text-[11px] font-semibold leading-snug text-slate-900">
          Оптимизатор расписания
        </div>
        <div className="mt-1 text-[10px] leading-snug text-slate-400">
          by AlyaIT
        </div>
      </div>
    </Link>
  );
}

