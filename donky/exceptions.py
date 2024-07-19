class ContainerNotCreated(Exception):
    """
    Container not created exception
    """


class VolumeAlreadyExistt(Exception):
    """
    Volume already exists exception
    """


class BackupEncryptedError(Exception):
    """
    Exception if backupo encrypted
    """


class IncrementalBackupError(Exception):
    """
    Exception if backup is incremental
    """


class PartialBackupError(Exception):
    """
    Exception for partial backups
    """


class BackupNotFoundError(Exception):
    """
    Backup not found exception
    """
