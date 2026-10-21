#!/usr/bin/env python3
"""Validate source teaching-load CSV and optionally export normalized preview CSVs.

This script never connects to PostgreSQL and never writes to Neon.
By default it only prints validation counts. Use --export-dir to write preview files.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

DETAIL_COLUMNS = [
    "Преподаватель",
    "Должность",
    "Факультет",
    "Группа",
    "Дисциплина",
    "Вид занятия",
    "Подгруппа",
    "Недели",
    "Пар в нечётную неделю",
    "Пар в чётную неделю",
    "Аудитории (по расписанию)",
    "Занятие ведётся совместно с группами",
]

OUTPUT_COLUMNS = [
    "source_row_number", "teacher_name", "teacher_position", "faculty",
    "group_name", "subject_name", "lesson_type", "subgroup", "weeks_label",
    "odd_pairs", "even_pairs", "source_room", "joint_groups",
]


def read_source(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(f"CSV-файл не найден: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, delimiter=";")
        missing = [name for name in DETAIL_COLUMNS if name not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(
                "Не найдены ожидаемые столбцы: " + ", ".join(missing)
                + ". Проверь, что используется подробный CSV с разделителем ';'."
            )
        return list(reader)


def clean(value: str | None) -> str:
    return (value or "").strip()


def normalize(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[str]]:
    result: list[dict[str, str]] = []
    errors: list[str] = []
    for source_number, row in enumerate(rows, start=1):
        odd_raw = clean(row.get("Пар в нечётную неделю"))
        even_raw = clean(row.get("Пар в чётную неделю"))
        try:
            odd = int(odd_raw or "0")
            even = int(even_raw or "0")
            if odd < 0 or even < 0:
                raise ValueError
        except ValueError:
            errors.append(
                f"строка {source_number}: число пар должно быть целым неотрицательным "
                f"(нечётная={odd_raw!r}, чётная={even_raw!r})"
            )
            odd, even = 0, 0

        record = {
            "source_row_number": str(source_number),
            "teacher_name": clean(row.get("Преподаватель")),
            "teacher_position": clean(row.get("Должность")),
            "faculty": clean(row.get("Факультет")),
            "group_name": clean(row.get("Группа")),
            "subject_name": clean(row.get("Дисциплина")),
            "lesson_type": clean(row.get("Вид занятия")),
            "subgroup": clean(row.get("Подгруппа")),
            "weeks_label": clean(row.get("Недели")),
            "odd_pairs": str(odd),
            "even_pairs": str(even),
            "source_room": clean(row.get("Аудитории (по расписанию)")),
            "joint_groups": clean(row.get("Занятие ведётся совместно с группами")),
        }
        for field in ("teacher_name", "group_name", "subject_name", "lesson_type", "weeks_label"):
            if not record[field]:
                errors.append(f"строка {source_number}: пустое обязательное поле {field}")
        result.append(record)
    return result, errors


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, delimiter=";", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--detail", required=True, type=Path,
                        help="Путь к подробному CSV с занятиями (разделитель ';').")
    parser.add_argument("--export-dir", type=Path, default=None,
                        help="Необязательная папка для выгрузки preview CSV. Без неё файлы не создаются.")
    args = parser.parse_args()

    try:
        source_rows = read_source(args.detail)
        normalized_rows, errors = normalize(source_rows)
    except (OSError, ValueError) as exc:
        print(f"ОШИБКА: {exc}", file=sys.stderr)
        return 2

    teachers: dict[str, dict[str, str]] = {}
    groups: dict[str, dict[str, str]] = {}
    subjects: set[str] = set()
    for row in normalized_rows:
        name = row["teacher_name"]
        if name:
            teachers.setdefault(name, {
                "name": name,
                "position": row["teacher_position"],
            })
        group = row["group_name"]
        if group:
            groups.setdefault(group, {
                "name": group,
                "faculty": row["faculty"],
                "students_count": "25",  # временное значение по согласованию пользователя
            })
        if row["subject_name"]:
            subjects.add(row["subject_name"])

    print("USO: предварительная проверка импорта учебной нагрузки")
    print("Режим: DRY RUN — база данных не подключается и не изменяется")
    print(f"Строк исходного CSV: {len(source_rows)}")
    print(f"Преподавателей: {len(teachers)}")
    print(f"Групп: {len(groups)}")
    print(f"Дисциплин: {len(subjects)}")
    print(f"Ошибок проверки: {len(errors)}")
    print("Временная численность каждой группы: 25 студентов")
    print("Дни недели и время занятий не создаются: их нет в исходном CSV.")

    if errors:
        for error in errors[:100]:
            print("ОШИБКА:", error)
        if len(errors) > 100:
            print(f"... ещё ошибок: {len(errors) - 100}")
        return 1

    if args.export_dir:
        out = args.export_dir
        write_csv(out / "teaching_load_preview.csv", OUTPUT_COLUMNS, normalized_rows)
        write_csv(out / "teachers_preview.csv", ["name", "position"], sorted(
            teachers.values(), key=lambda item: item["name"].casefold()))
        write_csv(out / "student_groups_preview.csv", ["name", "faculty", "students_count"], sorted(
            groups.values(), key=lambda item: item["name"].casefold()))
        write_csv(out / "subjects_preview.csv", ["name"], [
            {"name": name} for name in sorted(subjects, key=str.casefold)
        ])
        print(f"Preview CSV сохранены в: {out.resolve()}")

    print("Проверка завершена. Запись в БД не выполнялась.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
