import Image from "next/image";
import Link from "next/link";

export default function BrandLogo() {
  return (
    <Link
      href="/"
      aria-label="УрГУПС — Оптимизатор расписания by AlyaIT"
      className="flex h-[76px] items-center gap-3 border-b border-slate-200 px-4"
    >
      <Image
        src="/urguups-logo.jpg.jpg"
        alt="Логотип УрГУПС"
        width={100}
        height={64}
        priority
        className="h-14 w-[100px] shrink-0 object-contain"
      />
      <div className="min-w-0">
        <div className="text-xs font-semibold leading-snug text-slate-900">
          Оптимизатор расписания
        </div>
        <div className="mt-1 text-[11px] leading-snug text-slate-400">
          by AlyaIT
        </div>
      </div>
    </Link>
  );
}
