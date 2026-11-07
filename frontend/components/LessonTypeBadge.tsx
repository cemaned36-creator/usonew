const labels: Record<string, string> = {
  "лекция": "Лекция",
  "практика": "Практическое занятие",
  "практическое": "Практическое занятие",
  "практическое занятие": "Практическое занятие",
  "лабораторная": "Лабораторное занятие",
  "лабораторное": "Лабораторное занятие",
  "лабораторное занятие": "Лабораторное занятие",
};

export default function LessonTypeBadge({ type }: { type?: string | null }) {
  const value = type?.trim();
  const label = value ? labels[value.toLocaleLowerCase("ru")] ?? value : "Тип занятия не указан";
  return <span className="inline-flex rounded-lg border border-slate-200 bg-slate-50 px-2 py-1 text-xs font-medium text-slate-700">{label}</span>;
}
