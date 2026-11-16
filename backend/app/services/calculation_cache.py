"""Read-only memoization scoped to one optimization calculation, never a session."""
from contextlib import contextmanager
from functools import wraps

_KEY = '_optimization_calculation_cache'


@contextmanager
def calculation_cache(db):
    previous = db.info.get(_KEY)
    db.info[_KEY] = {}
    try:
        yield
    finally:
        if previous is None:
            db.info.pop(_KEY, None)
        else:
            db.info[_KEY] = previous


def calculation_value(db, key, load):
    cache = db.info.get(_KEY)
    if cache is None:
        return load()
    if key not in cache:
        cache[key] = load()
    return cache[key]


def cached_calculation(func):
    @wraps(func)
    def wrapped(db):
        return calculation_value(db, func, lambda: func(db))
    return wrapped


def calculation_rows(db, model):
    return calculation_value(db, ('rows', model), lambda: db.query(model).order_by(model.id).all())
