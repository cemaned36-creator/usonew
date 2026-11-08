from datetime import datetime, timezone
from io import BytesIO
from types import SimpleNamespace as NS
import pytest
from fastapi import HTTPException
from pypdf import PdfReader
from app.routers.optimization import PreviewPdfRequest, export_preview_pdf, export_history_pdf
from app.services.optimization_pdf import render_optimization_pdf


def report():
    return {'week_type': 'odd', 'teacher_id': None,
            'summary': {'transition_time_before': None, 'transition_time_after': 0, 'time_saved': None},
            'teachers': [], 'groups': [], 'changes': []}


def text(pdf):
    return '\n'.join(page.extract_text() for page in PdfReader(BytesIO(pdf)).pages)


def test_preview_is_downloadable_never_claims_applied_and_preserves_unknown():
    payload = PreviewPdfRequest(week_type='odd', detailed_report=report(), warnings=['<b>Проверка & кириллица</b>'])
    response = export_preview_pdf(payload)
    assert response.media_type == 'application/pdf'
    assert 'attachment;' in response.headers['content-disposition']
    assert response.headers['cache-control'] == 'no-store'
    result = text(response.body)
    assert 'ПРЕДВАРИТЕЛЬНЫЙ ПЛАН' in result and 'НЕ ПРИМЕНЁН' in result
    assert 'Не рассчитано' in result and '0 мин' in result
    assert '<b>Проверка & кириллица</b>' in result


def test_wrong_preview_scope_and_malformed_report_rejected():
    with pytest.raises(HTTPException) as exc:
        export_preview_pdf(PreviewPdfRequest(week_type='even', detailed_report=report()))
    assert exc.value.status_code == 422
    with pytest.raises(HTTPException):
        export_preview_pdf(PreviewPdfRequest(week_type='odd', detailed_report={**report(), 'groups': 'bad'}))


def test_historical_and_reverted_exports_use_saved_snapshot_without_recalculation():
    now = datetime(2026, 11, 7, tzinfo=timezone.utc)
    run = NS(id=7, week_type='odd', teacher_id=None, teacher_name=None, created_at=now,
             restored_at=None, before_entries=[], after_entries=[], metrics={'detailed_report': report()})
    db = NS(get=lambda model, identity: run if identity == 7 else None)
    applied = export_history_pdf(7, 'odd', None, db)
    assert 'ОПТИМИЗАЦИЯ ПРИМЕНЕНА' in text(applied.body)
    run.restored_at = now
    assert 'ОПТИМИЗАЦИЯ ОТМЕНЕНА' in text(export_history_pdf(7, 'odd', None, db).body)
    with pytest.raises(HTTPException) as exc:
        export_history_pdf(7, 'even', None, db)
    assert exc.value.status_code == 409
    with pytest.raises(HTTPException) as exc:
        export_history_pdf(99, 'odd', None, db)
    assert exc.value.status_code == 404
    run.metrics = {'transition_time_before': 10, 'transition_time_after': 2, 'time_saved': 8}
    assert '8 мин' in text(export_history_pdf(7, 'odd', None, db).body)


def test_long_cyrillic_report_has_all_changes_and_multiple_pages():
    changes = []
    for i in range(45):
        changes.append({'entry_id': i, 'subject_name': 'Социальные и психологические аспекты профессиональной деятельности',
            'teacher_name': 'Балакин Сергей Владимирович', 'weekday': i % 6,
            'groups': [{'name':'ИТси-215', 'subgroup_number':1}], 'lesson_type':'Лекция',
            'before': {'start_time':'08:30', 'end_time':'10:05', 'room_name':'Б2-113'},
            'after': {'start_time':'10:15', 'end_time':'11:50', 'room_name':'Б1-11'},
            'reasons': [{'text':'Сокращено время перехода.'}]})
    pdf = render_optimization_pdf({**report(), 'changes':changes}, week_type='odd')
    reader = PdfReader(BytesIO(pdf))
    assert len(reader.pages) > 2
    extracted = text(pdf)
    assert all(f'Запись #{i}:' in extracted for i in range(45))
    assert 'ИТси-215' in extracted and 'Балакин' in extracted
