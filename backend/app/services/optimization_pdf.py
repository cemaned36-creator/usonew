"""Read-only PDF rendering of a preview or a saved optimization snapshot."""
from datetime import datetime
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether

FONT_DIR = Path(__file__).resolve().parents[1] / 'assets' / 'fonts'
for name, filename in [('USO', 'DejaVuSans.ttf'), ('USO-Bold', 'DejaVuSans-Bold.ttf')]:
    pdfmetrics.registerFont(TTFont(name, str(FONT_DIR / filename)))
pdfmetrics.registerFontFamily('USO', normal='USO', bold='USO-Bold', italic='USO', boldItalic='USO-Bold')
DAYS = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
TYPES = {'Практика': 'Практическое занятие', 'Лабораторная': 'Лабораторное занятие'}
IMPACT = {'improved': 'Улучшено', 'worsened': 'Ухудшено', 'mixed': 'Смешанный эффект', 'unchanged': 'Без изменений', 'unknown': 'Не определено'}


def minutes(value):
    return 'Не рассчитано' if value is None else f'{value} мин'


def duration(value):
    if value is None:
        return 'Не указано'
    value = int(value)
    return f'{value // 60} ч {value % 60:02d} мин'


def date_label(value):
    if not value:
        return 'Не указана'
    dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if dt.tzinfo is None:
        from datetime import timezone
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(ZoneInfo('Asia/Yekaterinburg')).strftime('%d.%m.%Y %H:%M')


def render_optimization_pdf(report, *, week_type, teacher_id=None, teacher_name=None,
                            history=None, warnings=None, constraint_issues=None, can_apply=None):
    """No queries, recalculation or writes. History status comes only from the DB endpoint."""
    out = BytesIO()
    doc = SimpleDocTemplate(out, pagesize=A4, rightMargin=36, leftMargin=36,
                            topMargin=40, bottomMargin=40, title='УСО - Отчёт об оптимизации', author='УСО')
    body = ParagraphStyle('body', fontName='USO', fontSize=9, leading=13, spaceAfter=5, alignment=TA_LEFT)
    small = ParagraphStyle('small', parent=body, fontSize=8, leading=11, spaceAfter=0)
    heading = ParagraphStyle('heading', parent=body, fontName='USO-Bold', fontSize=14, leading=19, spaceBefore=14, spaceAfter=9, keepWithNext=True)
    title = ParagraphStyle('title', parent=heading, fontSize=21, leading=27)
    story = []

    def p(value, style=body):
        return Paragraph(escape(str(value if value is not None else 'Не указано')).replace('\n', '<br/>'), style)

    def line(value):
        story.append(p(value))

    def section(value):
        story.append(p(value, heading))

    def table(headers, rows, widths=None):
        if not rows:
            line('Нет данных для отображения.')
            return
        data = [[p(x, small) for x in headers]] + [[p(x, small) for x in row] for row in rows]
        t = Table(data, colWidths=widths, repeatRows=1, hAlign='LEFT')
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e6f0ed')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), .35, colors.HexColor('#d4dedb')),
            ('LEFTPADDING', (0, 0), (-1, -1), 7), ('RIGHTPADDING', (0, 0), (-1, -1), 7),
            ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.extend([t, Spacer(1, 8)])

    status = 'ПРЕДВАРИТЕЛЬНЫЙ ПЛАН - НЕ ПРИМЕНЁН'
    if history:
        status = 'ОПТИМИЗАЦИЯ ПРИМЕНЕНА - ИСТОРИЧЕСКИЙ СНИМОК'
        if history.get('restored_at'):
            status = 'ОПТИМИЗАЦИЯ ОТМЕНЕНА - ИСТОРИЧЕСКИЙ СНИМОК'
    story.append(p('Отчёт об оптимизации расписания', title))
    line(status)
    line(('Нечётная' if week_type == 'odd' else 'Чётная') + ' неделя')
    teachers = report.get('teachers', [])
    selected_name = teacher_name or next((t.get('teacher_name') for t in teachers if t.get('teacher_id') == teacher_id), None)
    line(f'Область: {selected_name or ("Преподаватель #" + str(teacher_id) if teacher_id else "Все преподаватели")}')
    line('Сформирован: ' + datetime.now(ZoneInfo('Asia/Yekaterinburg')).strftime('%d.%m.%Y %H:%M') + ' (Екатеринбург)')
    if history:
        line(f'Операция №{history["id"]}. Применена: {date_label(history.get("created_at"))}.')
        if history.get('restored_at'):
            line('Отменена: ' + date_label(history['restored_at']))
        line('Показатели отражают сохранённый снимок, а не текущее состояние расписания.')
    else:
        line('Экспортирован показанный предварительный расчёт. Скачивание PDF не сохраняет назначения.')
        if can_apply is not None:
            line('Проверка плана на момент расчёта: ' + ('пройдена.' if can_apply else 'план нельзя применить. См. предупреждения.'))
    line('Время переходов включает получение и возврат ключей. Спорткомплекс исключён из оптимизации переходов.')
    summary = report.get('summary', {})
    section('Общий результат')
    table(['Показатель', 'До', 'После'], [
        ['Время переходов', minutes(summary.get('transition_time_before')), minutes(summary.get('transition_time_after'))],
        ['Недостаточные перерывы', summary.get('insufficient_breaks_before', 'Нет данных'), summary.get('insufficient_breaks_after', 'Нет данных')],
        ['Неизвестные переходы', summary.get('unknown_transitions_before', 'Нет данных'), summary.get('unknown_transitions_after', 'Нет данных')],
    ], [245, 139, 139])
    line('Экономия времени: ' + minutes(summary.get('time_saved')) + '. Отрицательное значение означает рост времени.')
    line(f'Изменено занятий: {summary.get("changed_entries", 0)}; аудиторий: {summary.get("room_changes", 0)}; переносов по времени: {summary.get("time_changes", 0)}.')
    line(f'Затронуто преподавателей: {summary.get("affected_teachers", 0)}; групп: {summary.get("affected_groups", 0)}.')
    section('Предупреждения и ограничения')
    notices = list(warnings or []) + [x.get('reason', '') for x in (constraint_issues or [])]
    if summary.get('insufficient_breaks_before') or summary.get('insufficient_breaks_after'):
        notices.append('Недостаточный перерыв: время пути известно и учтено в сумме, но превышает интервал между занятиями.')
    if summary.get('transition_metrics_complete') is False:
        notices.append('Есть переходы с неизвестным временем. Неполные суммы не заменены нулём.')
    for warning in report.get('student_warnings', []):
        notices.append(f'{warning.get("group_name") or "Группа"}: {IMPACT.get(warning.get("impact"), "Изменение показателей")}; изменение числа окон: {warning.get("window_delta")}; изменение длительности недели: {minutes(warning.get("span_delta_minutes"))}.')
    for notice in dict.fromkeys(notices):
        if notice:
            line(notice)
    if not notices:
        line('В сохранённых данных отчёта предупреждений нет.')
    line('Смешанный эффект: количество окон уменьшилось, а длительность учебной недели выросла, или наоборот.')

    section('Показатели преподавателей')
    table(['Преподаватель', 'До', 'После', 'Экономия'], [
        [t.get('teacher_name') or f'#{t.get("teacher_id")}', minutes(t.get('before', {}).get('minutes')), minutes(t.get('after', {}).get('minutes')), minutes(t.get('time_saved'))]
        for t in teachers], [235, 96, 96, 96])

    def lesson_text(lesson):
        if not lesson:
            return 'Нет занятия'
        pair = lesson.get('pair_number')
        typ = lesson.get('lesson_type')
        return (f'{str(pair) + "-я пара" if pair else "Вне сетки пар"} | {lesson.get("start_time", "")} - {lesson.get("end_time", "")}\n'
                f'{lesson.get("subject_name") or "Занятие #" + str(lesson.get("lesson_id"))}\n'
                f'{TYPES.get(typ, typ) or "Тип занятия не указан"}\n'
                f'{lesson.get("teacher_name") or ""}\nАудитория: {lesson.get("room_name") or "Не указана"}')

    def timetable(data):
        if not data:
            line('Полное сравнение расписаний в этом старом снимке не сохранено. См. журнал изменений.')
            return
        before = {d['weekday']: d.get('lessons', []) for d in data.get('before', [])}
        after = {d['weekday']: d.get('lessons', []) for d in data.get('after', [])}
        changed = False
        for day in sorted(set(before) | set(after)):
            left, right = before.get(day, []), after.get(day, [])
            if left == right:
                continue
            changed = True
            line(DAYS[day])
            rows = [[lesson_text(left[i] if i < len(left) else None), lesson_text(right[i] if i < len(right) else None)] for i in range(max(len(left), len(right)))]
            table(['До оптимизации', 'После оптимизации'], rows, [261.5, 261.5])
        if not changed:
            line('Расписание не изменилось.')

    for teacher in teachers:
        if not teacher.get('changes_count'):
            continue
        story.append(PageBreak())
        section('Преподаватель: ' + (teacher.get('teacher_name') or str(teacher.get('teacher_id'))))
        timetable(teacher.get('timetable'))

    for group in report.get('groups', []):
        story.append(PageBreak())
        section('Группа: ' + (group.get('group_name') or str(group.get('group_id'))))
        line('Показатели окон и длительности: ' + IMPACT.get(group.get('impact'), 'Не определено'))
        b, a = group.get('before') or {}, group.get('after') or {}
        table(['Показатель', 'До', 'После'], [
            ['Количество окон', b.get('windows', 'Нет данных'), a.get('windows', 'Нет данных')],
            ['Учебная неделя с переменами', duration(b.get('weekly_span_minutes', b.get('span_minutes'))), duration(a.get('weekly_span_minutes', a.get('span_minutes')))],
            ['Средний учебный день', duration(b.get('average_day_span_minutes')), duration(a.get('average_day_span_minutes'))],
            ['Самый длинный день', duration(b.get('longest_day_span_minutes')), duration(a.get('longest_day_span_minutes'))],
            ['Чистое время занятий', duration(b.get('teaching_minutes')), duration(a.get('teaching_minutes'))],
        ], [245, 139, 139])
        line('Неделя - сумма длительностей учебных дней; длительность дня включает перемены и окна.')
        timetable(group.get('timetable'))

    story.append(PageBreak())
    section('Журнал изменений')
    changes = report.get('changes', [])
    if not changes:
        line('Изменений занятий нет.')
    for c in changes:
        block_start = len(story)
        section(f'Запись #{c.get("entry_id")}: {c.get("subject_name") or "Занятие"}')
        line(f'{DAYS[c.get("weekday", 0)]} | {c.get("teacher_name") or "Преподаватель не указан"}')
        typ = c.get('lesson_type')
        line('Тип: ' + (TYPES.get(typ, typ) or 'Не указан'))
        line('Группы: ' + ', '.join(str(g.get('name', g.get('id'))) + (f' (подгруппа {g["subgroup_number"]})' if g.get('subgroup_number') else '') for g in c.get('groups', [])))
        def assignment(x):
            from datetime import time
            from app.services.lesson_times import get_lesson_pair
            try:
                pair = get_lesson_pair(time.fromisoformat(x.get('start_time', '')), time.fromisoformat(x.get('end_time', '')))
            except ValueError:
                pair = None
            label = f'{pair}-я пара | ' if pair else ''
            return label + f'{x.get("start_time", "")} - {x.get("end_time", "")}\nАудитория: {x.get("room_name", x.get("room_id", "Не указана"))}'
        table(['До', 'После'], [[assignment(c.get('before', {})), assignment(c.get('after', {}))]], [261.5, 261.5])
        reasons = c.get('reasons') or [{'text': c.get('reason') or 'Причина в старом снимке не сохранена.'}]
        for reason in reasons:
            line(reason.get('text', ''))
        adjacent = c.get('adjacent_transitions')
        if adjacent:
            line('Соседние переходы: ' + minutes(adjacent.get('before', {}).get('minutes')) + ' → ' + minutes(adjacent.get('after', {}).get('minutes')))
        block = story[block_start:]
        del story[block_start:]
        story.append(KeepTogether(block))
    line('Один переход может быть показан в двух карточках. Общий итог учитывает каждый переход один раз.')

    def footer(canvas, document):
        canvas.setFont('USO', 8)
        canvas.setFillColor(colors.HexColor('#64746e'))
        canvas.drawString(36, 22, 'УСО | ' + ('Предварительный план' if not history else f'История №{history["id"]}'))
        canvas.drawRightString(A4[0] - 36, 22, f'Страница {document.page}')
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return out.getvalue()
