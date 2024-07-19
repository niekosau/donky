from donky.podman_cli import PodmanContainer
import os
import logging
import time
import threading


class Container():

    def __init__(
            self,
            image: str,
            tag: str,
            registry: str,
            engine: str,
            **kwargs):
        self.image = image
        self.image_tag = tag
        self.registry = registry
        if engine.lower() == "podman":
            image = {
                "image": image,
                "tag": tag
            }
            self.container = PodmanContainer(
                socket=f"/run/user/{os.getuid()}/podman/podman.sock",
                registry=self.registry,
                image=image,
                **kwargs
                )

        elif engine.lower() == "docker":
            raise ValueError("Docker currently not supported")
        else:
            raise ValueError("Unsupoorted container engine")
        self._logger = logging.getLogger("Donky")

    @property
    def status(self) -> str:
        self.container.container.reload()
        return self.container.container.status

    @property
    def name(self) -> str:
        return self.container.container.name

    def reload(self) -> None:
        self.container.container.reload()

    def stop(self) -> None:
        self.reload()
        if self.container.container.status == "running":
            self._logger.info(f"Stopping container {self.name}")
            self.container.container.stop()
        self.reload()

    def start(self) -> None:
        self.reload()
        if self.container.container.start != "running":
            self._logger.info(f"Starting container: {self.name}")
            self.container.container.start()

    def wait(
            self,
            state: str = "running",
            interval: int = 1,
            timeout: int = 3600) -> None:
        self._logger.info(f"Waiting {self.name} to enter state: {state}")
        wait_thread = threading.Thread(
            target=self.container.container.wait,
            kwargs={
                "condition": state,
                "interval": f"{interval}s"
            })
        wait_thread.start()
        for i in range(timeout):
            self._logger.debug(f"waiting for: {i+1}")
            time.sleep(1)
            if int(i + 1) is int(timeout):
                self.container.container.kill()
                print(threading.active_count())
                wait_thread.join()
                print(threading.active_count())
                raise TimeoutError("Tiemout exceeded")
            if not wait_thread.is_alive():
                break
        self._logger.debug("Waiting finished")
