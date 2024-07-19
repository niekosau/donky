import logging
import os
import re
import configparser
import json
from donky.exceptions import (
    BackupEncryptedError,
    IncrementalBackupError,
    PartialBackupError,
    BackupNotFoundError
)

SUPPORTED_BACKUP_TYPES = [
    "binary",
]
DEFAUL_IMAGE = "percona/percona-server"


def format_search(name: str, suffix: str) -> str:
    results = [name]
    results.append(".")
    results.append(suffix)
    return "".join(results)


def find_newest_file(files: list) -> str:
    return max(files, key=os.path.getctime)


def find_files_by_pattern(path: str, pattern: str) -> list:
    files = []
    for root, sub, file in os.walk(path):
        found = [f for f in file if re.match(pattern, f)]
        if len(found) == 0:
            continue
        if len(found) > 1:
            raise ValueError(f"Name patern: {pattern} matches more then one file in directory, plese adjust patern or check directory")
        file_path = f"{root}/{''.join(found)}"
        files.append(file_path)
    if len(files) == 0:
        raise ValueError(f"Name pattern: {pattern} doesn't match any file in location: {path}")
    return files


def binary_backup_info(path: str) -> dict:
    files = find_files_by_pattern(path=path, pattern="xtrabackup_info")
    file = find_newest_file(files=files)
    backup_info_parser = configparser.ConfigParser()
    with open(file, "r") as f:
        backup_info_parser.read_string("[backup_info]\n" + f.read())
    backup_info: dict = backup_info_parser.__dict__.get("_sections")["backup_info"]
    if backup_info.get("encrypted") != "N":
        raise BackupEncryptedError("Encrypted backups currently not supported")
    if backup_info.get("incremental") != "N":
        raise IncrementalBackupError("Incremental backups currently not supported")
    if backup_info.get("partial") != "N":
        raise PartialBackupError("Partial backup not supported")
    format: str = backup_info.get("format")
    compressed = True if backup_info.get("compressed") == "compressed" else False
    server_version = ".".join(backup_info.get("server_version").split(".")[:2])
    tool_version = ".".join(backup_info.get("tool_version").split(".")[:2])
    backup_info = {
        "backup_info_file": file,
        "server_version": server_version,
        "tool_version": tool_version,
        "format": format,
        "compressed": compressed
    }
    return backup_info


def binary_backup_file(path: str, format: str, name: str) -> str:
    search_name = format_search(name=name, suffix=format)
    backup_file = find_files_by_pattern(path=path, pattern=search_name)
    if len(backup_file) == 0:
        raise BackupNotFoundError(f"Backup with pattern {name} not found")
    if len(backup_file) > 1:
        raise ValueError(f"Too many files found by patter: {name}")
    return backup_file[0]


def binary_backups(path: str, pattern: str) -> dict:
    results = binary_backup_info(path=path)
    location = results.pop("backup_info_file").rstrip("/xtrabackup_info")
    format = results.get("format")
    results["backup_file"] = binary_backup_file(path=location, format=format, name=pattern)
    return results


def resolve_backup(
        backup_type: str,
        backup_path: str,
        name_pattern: str) -> dict:
    _logger = logging.getLogger("Donky")
    _logger.info(f"Resolving backup type: {backup_type}")
    if backup_type not in SUPPORTED_BACKUP_TYPES:
        raise ValueError(f"Unsuported backup type {backup_type}")
    if not os.path.isdir(backup_path):
        raise ValueError(f"Backup path {backup_path} not a directory")
    backup_info = binary_backups(path=backup_path, pattern=name_pattern)
    _logger.debug(f"Backup info:\n{json.dumps(backup_info, indent=2)}")
    backup_info["image"] = DEFAUL_IMAGE
    return backup_info
