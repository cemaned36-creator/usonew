import Image from "next/image";
import Link from "next/link";

export default function BrandLogo() {
  return (
    <Link
      href="/"
      aria-label="УрГУПС — Оптимизатор расписания by AlyaIT"
      className="flex min-h-[88px] w-full items-center gap-3 overflow-hidden border-b border-slate-200 px-3"
    >
      <Image
        src="/urguups-logo.jpg.jpg"
        alt="Логотип УрГУПС"
        width={116}
        height={72}
        priority
        className="h-[68px] w-[112px] shrink-0 object-contain"
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
