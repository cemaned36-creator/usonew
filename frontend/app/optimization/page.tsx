
"use client";

import { useState } from "react";

type OptimizationResult = {
  changes: unknown[];
  changes_count: number;
  transition_time_before: number;
  transition_time_after: number;
  time_saved: number;
  unknown_routes: unknown[];
  saved_to_database: boolean;
};

export default function OptimizationPage() {
  const [result, setResult] = useState<OptimizationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function runOptimizationPreview() {
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL;

      if (!apiUrl) {
        throw new Error("Не задан NEXT_PUBLIC_API_URL для frontend.");
      }

      const response = await fetch(
        `${apiUrl.replace(/\/$/, "")}/optimization/preview`
      );

      if (!response.ok) {
        throw new Error(`Ошибка API: HTTP ${response.status}`);
      }

      const data: OptimizationResult = await response.json();
      setResult(data);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Не удалось получить результат."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto max-w-4xl p-6">
      <h1 className="mb-2 text-2xl font-bold">
        Оптимизация расписания
      </h1>

      <p className="mb-6 text-gray-600">
        Предварительный расчёт сокращения времени переходов преподавателей
        между аудиториями. Изменения в базе данных не сохраняются.
      </p>

      <button
        onClick={runOptimizationPreview}
        disabled={loading}
        className="rounded-lg bg-blue-600 px-5 py-3 text-white disabled:opacity-50"
      >
        {loading ? "Выполняется расчёт..." : "Запустить оптимизацию"}
      </button>

      {error && (
        <p className="mt-4 text-red-600" role="alert">
          {error}
        </p>
      )}

      {result && (
        <section className="mt-6 space-y-3 rounded-lg border p-5">
          <h2 className="text-xl font-semibold">Результат расчёта</h2>

          <p>Найдено изменений: {result.changes_count}</p>
          <p>Время переходов до: {result.transition_time_before} мин.</p>
          <p>Время переходов после: {result.transition_time_after} мин.</p>
          <p>Экономия времени: {result.time_saved} мин.</p>
          <p>Неизвестных маршрутов: {result.unknown_routes.length}</p>

          <p className="text-sm text-gray-600">
            {result.saved_to_database
              ? "Изменения сохранены в базе данных."
              : "Это предварительный просмотр. База данных не изменена."}
          </p>

          {result.changes.length > 0 && (
            <pre className="overflow-x-auto rounded bg-gray-100 p-3 text-sm text-gray-900">
              {JSON.stringify(result.changes, null, 2)}
            </pre>
          )}
        </section>
      )}
    </main>
  );
}
