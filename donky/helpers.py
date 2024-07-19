import subprocess
import os
import pwd
import grp
from donky.containers import Container
import logging
import json


def podman_start_user_service() -> None:
    """
    Start podman user service, so socket file created that will be used later
    """
    command = []
    command.append("/usr/bin/systemctl")
    command.append("start")
    command.append("--user")
    command.append("podman")
    podman_user_service = subprocess.Popen(command)
    podman_user_service.communicate()


def get_user_id() -> int:
    """
    Get user id for podman socket path
    """
    return os.getuid()


def drop_user_privileges(user: str) -> int:
    """
    Change user privileges
    """
    pw = pwd.getpwnam(user)
    if pw.pw_uid == os.getuid():
        return pw.pw_uid
    u_gids = [pw.pw_gid]
    for group in grp.getgrall():
        if pw.pw_name in group.gr_mem:
            u_gids.append(group.gr_gid)
    os.setgroups(u_gids)
    os.setgid(pw.pw_gid)
    os.setuid(pw.pw_uid)
    os.environ["HOME"] = pw.pw_dir
    return pw.pw_uid


def create_mysql_container(
        con_data: dict,
        name: str,
        engine: str) -> Container:
    _logger = logging.getLogger("Donky")
    config: dict = {}
    volume = {
        "name": name,
        "bind": "/var/lib/mysql",
        "mode": "rw",
        "force": True
    }
    cont_config = {
        "name": name,
        "ports": {
            "3306/tcp": "3306"
        },
        "environment": {
            "MYSQL_ALLOW_EMPTY_PASSWORD": "true"
        },
        "bootstrap": True
    }

    config["volume"] = volume
    config["container"] = cont_config
    config["command"] = ["mysqld", "--skip-grant-tables"]
    _logger.trace(f"Container additional config:\n{json.dumps(config, indent=2)}")
    container = Container(
        image=con_data.pop("image"),
        tag=con_data.pop("server_version"),
        registry=con_data.pop("registry"),
        engine=engine,
        **config)
    return container


def restore_backup(
        name: str,
        backup_file: str,
        registry: str,
        version: float,
        volumes_from: str,
        engine: str) -> Container:
    _logger = logging.getLogger("Donky")
    backup_file_name = os.path.basename(backup_file)
    backup_path = backup_file.rstrip(backup_file_name)
    xtrabackup_container = {
        "name": name,
        "image": "perconalab/percona-xtrabackup",
        "registry": registry,
        "tag": version
    }
    x_container = {
        "name": name,
        "recreate": False,
    }
    mount = {
        "source": backup_path,
        "target": "/backup",
    }
    command = f"""
        /usr/bin/rm -rf /var/lib/mysql/* &&
        /usr/bin/cat /backup/{backup_file_name} | /usr/bin/xbstream -x --directory /var/lib/mysql &&
        xtrabackup --decompress --parallel 4 --remove-original --target-dir=/var/lib/mysql &&
        xtrabackup --prepare --target-dir=/var/lib/mysql &&
        chown -R 999:999 /var/lib/mysql/*
        """
    xtrabackup_container["mount"] = mount
    xtrabackup_container["container"] = x_container
    xtrabackup_container["command"] = ["/bin/sh", "-c", command]
    xtrabackup_container["volumes_from"] = [volumes_from]
    xtrabackup_container["user"] = "root"
    _logger.trace(f"Xtrabackup container config:\n{json.dumps(xtrabackup_container, indent=2)}")
    xtrabackup = Container(engine=engine, **xtrabackup_container)
    return xtrabackup


def check_xtrabackup_version() -> None:
    pass
