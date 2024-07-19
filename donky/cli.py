import argparse
import json
from donky.obfuscator import Obfuscator
from donky.containers import Container
from donky.config import (
    parse_config,
    Donky,
    Obfuscators
)
from donky.helpers import create_mysql_container, restore_backup
from donky.backups import resolve_backup
import time
import logging


parser = argparse.ArgumentParser(
    epilog="Depersonalization tool"
)
parser.add_argument(
    "-c",
    "--config",
    help="Path to config file",
    default="/etc/donky/donky.conf"
)
subparsers = parser.add_subparsers(dest="command")


def argument(*name_or_flags, **kwards) -> list:
    return (list(name_or_flags), kwards)


def command(args=[], parent=subparsers, cmd_aliases=None):
    if cmd_aliases is None:
        cmd_aliases = []

    def decorator(func):
        parser = parent.add_parser(
            func.__name__.replace("_", "-"),
            description=func.__doc__,
            aliases=cmd_aliases
        )
        for arg in args:
            parser.add_argument(*arg[0], **arg[1])
        parser.set_defaults(func=func)
    return decorator


def update_obfuscator(obfuscator: Obfuscator, data: dict) -> None:
    for key, value in data.items():
        obfuscator.__setattr__(key, value)


@command(
    [
        argument(
            "obfuscator",
            help="Section from config file which to exececute"
        )
    ]
)
def obfuscate(args: argparse.Namespace) -> None:
    config = parse_config(args.config)
    _logger = logging.getLogger("Donky")
    _logger.info("Starting Donky")
    _logger.trace(f"cli arguments:\n {json.dumps(args.__dict__, indent=2, default=str)}")
    _logger.trace(f"Config:\n{json.dumps(config.__dict__, indent=2, default=str)}")
    if args.obfuscator == "all":
        _logger.warning("Not implemented")
        return
    if args.obfuscator not in config.obfuscators.keys():
        raise ValueError(f"No config section for {args.obfuscator}")
    _logger.info(f"Obfuscating {args.obfuscator}")
    obfuscator: Obfuscators = config.obfuscators.pop(args.obfuscator)
    _logger.trace(f"Obfuscator:\n{json.dumps(obfuscator.__dict__, indent=2)}")
    mysql_con_name = f"mysql_{args.obfuscator}"
    _logger.info("Resolving backup")
    backup = resolve_backup(
            backup_type=obfuscator.backup_type,
            backup_path=obfuscator.backup_source,
            name_pattern=obfuscator.search_name)
    update_obfuscator(obfuscator=obfuscator, data=backup)
    _logger.debug(f"Obfuscator:\n{json.dumps(obfuscator.__dict__, indent=2)}")
    _logger.info("Creating mysql container")
    mysql_container = create_mysql_container(
            name=mysql_con_name,
            engine=config.container_engine,
            con_data=obfuscator.__dict__)
    mysql_container.stop()
    _logger.info("Creating xtrbakuo container")
    restore = restore_backup(
            name=f"xtrabackup_{args.obfuscator}",
            backup_file=obfuscator.backup_file,
            volumes_from=mysql_con_name,
            version=obfuscator.tool_version,
            registry=obfuscator.registry,
            engine=config.container_engine)
    _logger.debug("Starting backup restore")
    restore.start()
    restore.wait(state="exited")
    _logger.debug("Restore finished")


def main() -> None:
    """
    Main function were everyhting is starting
    """
    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        exit()
    args.func(args)


if __name__ == "__main__":
    main()
