"""Persistence evidence — schema DDL shipped inside each module.

`SHARED_DB` needs *store identity*, not just "this service talks to a database".
Two services both having a JDBC driver on the classpath says nothing; two
services writing to the same named schema says everything.

In PetClinic the connection URLs live in an external configuration repository
that is not part of this checkout, so the only in-snapshot source of store
identity is the DDL under `src/main/resources/db/<vendor>/schema.sql`. The MySQL
scripts name their schema (`CREATE DATABASE ... ; USE ...;`); the HSQLDB scripts
do not, and are recorded as unresolved rather than assumed distinct — assuming
distinct would manufacture a `SHARED_DB = 0` out of missing evidence.
"""

from __future__ import annotations

import os
import re

_CREATE_DATABASE_RE = re.compile(r"CREATE\s+DATABASE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`\"]?(\w+)", re.I)
_USE_RE = re.compile(r"^\s*USE\s+[`\"]?(\w+)", re.I | re.M)
_CREATE_TABLE_RE = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`\"]?(\w+)", re.I
)
_FOREIGN_KEY_RE = re.compile(r"REFERENCES\s+[`\"]?(\w+)", re.I)


def _schema_files(module_dir: str) -> list[tuple[str, str]]:
    """(vendor, absolute path) for every `db/<vendor>/schema.sql` in the module."""
    db_root = os.path.join(module_dir, "src", "main", "resources", "db")
    if not os.path.isdir(db_root):
        return []
    found = []
    for vendor in sorted(os.listdir(db_root)):
        path = os.path.join(db_root, vendor, "schema.sql")
        if os.path.isfile(path):
            found.append((vendor, path))
    return found


def read_module_schemas(module_name: str, module_dir: str, repo_root: str) -> dict:
    """Declared schemas of one module, split into resolved and unresolved.

    `vendor` doubles as the deployment profile: a module ships one DDL per
    backing store it can be deployed against, and which one is live is a
    deployment-time choice. Store identity is therefore only meaningful within
    a vendor, and `SHARED_DB` must be evaluated per vendor.
    """
    declarations: list[dict] = []
    unresolved: list[dict] = []
    for vendor, path in _schema_files(module_dir):
        rel = os.path.relpath(path, repo_root)
        with open(path, encoding="utf-8") as handle:
            sql = handle.read()

        tables = sorted(set(_CREATE_TABLE_RE.findall(sql)))
        referenced = sorted(set(_FOREIGN_KEY_RE.findall(sql)))
        names = _CREATE_DATABASE_RE.findall(sql) + _USE_RE.findall(sql)

        record = {
            "module": module_name,
            "vendor": vendor,
            "tables": tables,
            "referenced_tables": referenced,
            "foreign_tables": sorted(set(referenced) - set(tables)),
            "source": {"file": rel, "line": 1},
        }
        if names:
            declarations.append({**record, "store_name": sorted(set(names))[0]})
        else:
            unresolved.append(
                {
                    **record,
                    "reason": (
                        "schema DDL names no database; the JDBC URL that would "
                        "identify the store is not in this checkout"
                    ),
                }
            )
    return {"declarations": declarations, "unresolved": unresolved}
