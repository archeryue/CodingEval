"""Docker container management."""

from __future__ import annotations

import logging
from typing import Any

import docker
from docker.models.containers import Container
from docker.models.images import Image

from codingeval.core.config import DockerConfig

logger = logging.getLogger(__name__)


class DockerManager:
    """Manages Docker images and containers for evaluation."""

    def __init__(self, config: DockerConfig | None = None):
        self._config = config or DockerConfig()
        self._client: docker.DockerClient | None = None

    @property
    def client(self) -> docker.DockerClient:
        if self._client is None:
            self._client = docker.from_env()
        return self._client

    def build_image(self, dockerfile: str | None = None, tag: str | None = None) -> Image:
        """Build the base Docker image."""
        dockerfile = dockerfile or self._config.dockerfile
        tag = tag or self._config.base_image

        logger.info("Building Docker image %s from %s", tag, dockerfile)

        import os

        context_path = os.path.dirname(dockerfile)
        dockerfile_name = os.path.basename(dockerfile)

        image, build_log = self.client.images.build(
            path=context_path,
            dockerfile=dockerfile_name,
            tag=tag,
            rm=True,
        )

        for chunk in build_log:
            if "stream" in chunk:
                logger.debug(chunk["stream"].strip())

        logger.info("Built image: %s", tag)
        return image

    def ensure_image(self, tag: str | None = None) -> None:
        """Ensure the base image exists, building it if needed."""
        tag = tag or self._config.base_image
        try:
            self.client.images.get(tag)
            logger.debug("Image %s already exists", tag)
        except docker.errors.ImageNotFound:
            self.build_image(tag=tag)

    def create_container(
        self,
        image: str | None = None,
        name: str | None = None,
        volumes: dict[str, dict[str, str]] | None = None,
        environment: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> Container:
        """Create a new container."""
        image = image or self._config.base_image

        container_kwargs: dict[str, Any] = {
            "image": image,
            "detach": True,
            "tty": True,
            "mem_limit": self._config.memory_limit,
            "cpu_count": self._config.cpu_count,
        }

        if name:
            container_kwargs["name"] = name
        if volumes:
            container_kwargs["volumes"] = volumes
        if environment:
            container_kwargs["environment"] = environment
        if not self._config.network_enabled:
            container_kwargs["network_mode"] = "none"

        container_kwargs.update(kwargs)

        container = self.client.containers.create(**container_kwargs)
        logger.info("Created container: %s", container.short_id)
        return container

    def start_container(self, container: Container) -> None:
        """Start a container."""
        container.start()
        logger.debug("Started container: %s", container.short_id)

    def exec_in_container(
        self, container: Container, command: str, workdir: str = "/testbed"
    ) -> tuple[int, str]:
        """Execute a command in a running container."""
        exec_result = container.exec_run(
            cmd=["bash", "-c", command],
            workdir=workdir,
        )
        output = exec_result.output.decode("utf-8", errors="replace")
        return exec_result.exit_code, output

    def remove_container(self, container: Container, force: bool = True) -> None:
        """Remove a container."""
        container.remove(force=force)
        logger.debug("Removed container: %s", container.short_id)

    def cleanup(self) -> None:
        """Close the Docker client."""
        if self._client:
            self._client.close()
            self._client = None
