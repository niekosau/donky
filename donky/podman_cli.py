import podman
import time
import os
import subprocess
import logging
from donky.exceptions import ContainerNotCreated, VolumeAlreadyExistt
import json


class PodmanContainer():

    def __init__(
            self,
            socket: str,
            registry: str,
            **kwargs):
        self.client = podman.PodmanClient()
        self.image: podman.domain.images.Image = None
        self.container: podman.domain.containers.Container = None
        self.volume: podman.domain.volumes.Volume = None
        self._logger = logging.getLogger("Donky")
        self.socket = socket
        self.registry = registry
        if not os.path.exists(socket):
            self._logger.debug("Starting podman servise for current user")
            command = []
            command.append("/usr/bin/systemctl")
            command.append("start")
            command.append("--user")
            command.append("podman")
            subprocess.Popen(command).communicate()
        self.container_config = {}
        if "image" in kwargs.keys():
            self.image = self.__init_image(**kwargs.pop("image"))
            self.container_config["image"] = self.image.short_id
        if "volume" in kwargs.keys():
            self.volume = self.__init_volume(**kwargs.pop("volume"))
        if "mount" in kwargs.keys():
            self.__init_mount(**kwargs.pop("mount"))
        if "command" in kwargs.keys():
            self._logger.info("Updating container command")
            self.container_config["command"] = kwargs.pop("command")
        if "volumes_from" in kwargs.keys():
            self.container_config["volumes_from"] = kwargs.pop("volumes_from")
        if "user" in kwargs.keys():
            self.container_config["user"] = kwargs.pop("user")
        if "container" in kwargs.keys():
            self.container = self.__init_container(**kwargs.pop("container"))

    def __init_mount(
            self,
            source: str,
            target: str,
            read_only: bool = True) -> None:
        self._logger.info("Updating mount config")
        mount = {
            "type": "bind",
            "source": source,
            "target": target,
            "read_only": read_only
        }
        self.container_config["mounts"] = [mount]

    def __init_container(
            self,
            name: str,
            ports: dict = None,
            bootstrap: bool = False,
            bootstrap_wait: int = 20,
            environment: dict = None,
            recreate: bool = False,
            command: str = None) -> podman.domain.containers.Container:
        if recreate:
            if self.client.containers.exists(key=name):
                self._logger.warning(f"Removing container: {name}")
                self.client.containers.remove(container_id=name)
        self._logger.info(f"Creating container: {name}")
        self.container_config["name"] = name
        if ports is not None:
            self.container_config["ports"] = ports
        if environment is not None:
            self.container_config["environment"] = environment
        self._logger.debug(f"Container config:\n{json.dumps(self.container_config, indent=2)}")
        container = self.client.containers.create(**self.container_config)
        if bootstrap:
            self._logger.info("Bootstraping container")
            container.start()
            self._logger.debug(f"Bootstrap sleep for: {bootstrap_wait}")
            time.sleep(bootstrap_wait)
        return container

    def __init_image(self, image: str, tag: str) -> podman.domain.images.Image:
        image = f"{self.registry}/{image}"
        self._logger.info(f"Updating image: {image}:{tag}")
        return self.client.images.pull(repository=image, tag=tag)

    def __init_volume(
            self,
            name: str,
            bind: str,
            mode: str = "ro",
            force: bool = False) -> podman.domain.volumes.Volume:
        volume_data = {
            name: {
                "bind": bind,
                "mode": mode,
                "device": "/backups/podman-volumes/"
                }
            }
        if self.client.volumes.exists(name):
            if not force:
                raise VolumeAlreadyExistt(f"Volume: {name} already exists")
            self._logger.warning(f"volume {name} exists, force removing")
            self.client.volumes.remove(name=name, force=force)
        self._logger.info(f"Creating volume: {name}")
        volume = self.client.volumes.create(name=name)
        self.container_config["volumes"] = volume_data
        return volume

    def _resolve_image(self, image: str, tag: str) -> None:
        self.get_image(image=image, tag=tag, registry=self.registry)
        self.container_config["image"] = self.image.short_id

    def get_container(self, id: str) -> podman.domain.containers.Container:
        self._logger.debug(f"Checking for container: {id}")
        return self.client.containers.get(id)

    def create_container(
            self,
            name: str,
            image: str,
            tag: str,
            command: list = None) -> podman.domain.containers.Container:
        self._resolve_image(image=image, tag=tag)
        self.container_config["name"] = name
        if command is not None:
            self.container_config["command"] = command
        self._logger.info(f"Creating container: {name}")
        self._logger.debug(f"Container config:\n{json.dumps(self.container_config, indent=2)}")
        self.container = self.client.containers.create(**self.container_config)

    def get_volume(self, volume_name: str) -> podman.domain.volumes.Volume:
        self._logger.debug(f"Getting volume: {volume_name}")
        return self.client.volumes.get(volume_id=volume_name)

    def create_volume(
            self,
            volume_name: str,
            mount_point: str,
            recreate: bool = False,
            force: bool = False,
            mode: str = 'ro') -> podman.domain.volumes.Volume:
        volume_data = {
            volume_name: {
                "bind": mount_point,
                "mode": mode
                }
            }
        try:
            volume = self.get_volume(volume_name=volume_name)
            if recreate:
                if force:
                    self._logger.warning(f"Force removing volume: {volume.id}")
                else:
                    self._logger.info(f"Removing volume: {volume.id}")
                volume.remove(force=force)
                volume.reload()
            if volume:
                raise VolumeAlreadyExistt(f"Volume with name {volume_name} already exists")
        except podman.errors.exceptions.NotFound:
            self._logger.debug(f"Creating volume: {volume_name}")
            self.volume = self.client.volumes.create(name=volume_name)
            self.container_config["volumes"] = volume_data

    def get_image(self, image: str, tag: str, registry: str) -> podman.domain.images.Image:
        self._logger.debug(f"Getting image: {registry}/{image}:{tag}")
        try:
            self.image = self.client.images.get(name=image)
        except podman.errors.exceptions.ImageNotFound:
            self._logger.debug("Downloading image")
            repository = f"{registry}/{image}"
            self.image = self.client.images.pull(repository=repository, tag=tag)

    def start_container(self) -> None:
        if self.container is None:
            raise ContainerNotCreated("Container not created")
        self._logger.info(f"Starting container: {self.container.name}")
        self.container.reload()
        if self.container.status != "running":
            self._logger.debug(f"Container {self.container.name} not running, starting")
            self.container.start()

    def stop_container(self) -> None:
        self._logger.debug(f"Stopping container: {self.container.name}")
        self.container.reload()
        if self.container.status == "running":
            self.container.stop()
