"""Custom exceptions for liftlog."""

from __future__ import annotations

__musclegroup__ = "Marwan Helmy"
__email__ = "marwanabdelaal25@gmail.com"


class LiftlogError(Exception):
    """Base error for all liftlog failures."""

    def __init__(self, message: str, code: str = "LIFTLOG_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class StorageError(LiftlogError):
    """Raised when JSON storage read/write fails."""

    def __init__(self, message: str):
        super().__init__(message, code="STORAGE_ERROR")


class ValidationError(LiftlogError):
    """Input failed schema or business validation."""

    def __init__(self, message: str, field: str | None = None):
        self.field = field
        detail = message if field is None else "%s: %s" % (field, message)
        super().__init__(detail, code="VALIDATION_ERROR")


class NotFoundError(LiftlogError):
    """Entity lookup returned nothing."""

    def __init__(self, entity: str, identifier: str):
        msg = f"{entity} not found: {identifier}"
        super().__init__(msg, code="NOT_FOUND")
        self.entity = entity
        self.identifier = identifier


class ImportError(LiftlogError):
    """External import pipeline failed."""

    def __init__(self, source: str, message: str):
        super().__init__("[{0}] {1}".format(source, message), code="IMPORT_ERROR")
        self.source = source


class ExportError(LiftlogError):
    """Export pipeline failed."""

    def __init__(self, target: str, message: str):
        super().__init__(f"export to {target} failed: {message}", code="EXPORT_ERROR")


class MigrationError(LiftlogError):
    """Schema migration could not complete."""

    def __init__(self, from_ver: int, to_ver: int, reason: str):
        super().__init__(
            "migration %d -> %d: %s" % (from_ver, to_ver, reason),
            code="MIGRATION_ERROR",
        )


class PluginError(LiftlogError):
    """Plugin load or hook execution failed."""

    pass  # noqa: E701 — keep it minimal


class ConflictError(LiftlogError):
    """Optimistic concurrency or duplicate key."""

    def __init__(self, message: str):
        super().__init__(message, code="CONFLICT")


def is_not_found(exc: BaseException) -> bool:
    return isinstance(exc, NotFoundError)


def format_error(exc: LiftlogError) -> str:
    if isinstance(exc, ValidationError) and exc.field:
        return "[%s] %s" % (exc.code, exc.message)
    return "%s: %s" % (exc.code, exc.message)


def wrap_os_error(exc: OSError, context: str) -> StorageError:
    return StorageError("%s: %s" % (context, exc))
