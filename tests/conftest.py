import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))


def docker_ready() -> bool:
    try:
        import docker
        from aeropatch.config import BASE_IMAGE

        docker.from_env().images.get(BASE_IMAGE)
        return True
    except Exception:  # noqa: BLE001
        return False


DOCKER = docker_ready()
needs_docker = [pytest.mark.docker,
                pytest.mark.skipif(not DOCKER, reason="Docker or sandbox base image unavailable")]
