"""Serialize load-lexical runs that share one canonical store."""

import logging
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Connection, create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import NullPool

_LOG = logging.getLogger(__name__)
# ASCII "ARXL", beside the projection catalog's "ARXP". The keys must differ: the
# build takes the catalog key from its own session while this lock is held.
LOAD_LOCK_KEY = 1095915596
_ACQUIRE_SQL = "SELECT pg_try_advisory_lock(:key)"
_RELEASE_SQL = "SELECT pg_advisory_unlock(:key)"


class LexicalLoadBusyError(RuntimeError):
    """Raised when another load-lexical run owns the canonical store."""


@contextmanager
def exclusive_lexical_load(url: str) -> Iterator[None]:
    """Own the canonical store for one load, build and verify; refuse when already owned.

    The lock lives on a dedicated autocommit session, so no transaction stays open
    while the build runs, and process death releases it with the session.
    """
    engine = create_engine(url, poolclass=NullPool, isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as connection, hold_load_lock(connection):
            yield
    finally:
        engine.dispose()


@contextmanager
def hold_load_lock(connection: Connection) -> Iterator[None]:
    """Hold the load lock on ``connection`` for the body, then release it."""
    acquired = connection.execute(text(_ACQUIRE_SQL), {"key": LOAD_LOCK_KEY}).scalar()
    if not acquired:
        raise LexicalLoadBusyError("another load-lexical run owns the canonical store")
    _LOG.info("load-lexical acquired store lock key=%d", LOAD_LOCK_KEY)
    try:
        yield
    finally:
        try:
            connection.execute(text(_RELEASE_SQL), {"key": LOAD_LOCK_KEY})
        except SQLAlchemyError:
            _LOG.warning("load-lexical store lock release failed; session close releases it")
