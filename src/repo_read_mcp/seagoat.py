import docker
from docker import errors
import tarfile
import io
import atexit
import hashlib
import re
import time
from typing import Dict, List, Union

import docker.client
from docker.models.containers import Container
from docker.models.images import Image
import os


class Seagoat:
    repo_path: str
    dockerfile_base_path: str
    docker_client: docker.client.DockerClient
    image: Image | None
    container: Container | None
    tag: str
    ANALYSIS_COMPLETE_MESSAGE = "Analyzed all chunks!"
    BASE_IMAGE_TAG = "seagoat-base:latest"

    def __init__(self, repo_path: str, dockerfile_base_path: str = "src/repo_read_mcp/templates/Dockerfile.seagoat.base", run_script_path: str = "src/repo_read_mcp/templates/run.base.sh") -> None:
        self.repo_path = repo_path
        self.dockerfile_base_path = dockerfile_base_path
        self.run_script_path = run_script_path
        self.docker_client = docker.from_env()
        self.image = None
        self.container = None
        self.tag = ""

        atexit.register(self.cleanup)

    def prepare(self) -> None:
        """
        Builds the Docker image for the repository.
        """
        if self.image:
            return
        
        build_context = self._create_build_context()
        self.tag = self._create_image_tag(build_context)
        self.image = self._get_or_build_image(build_context)

    def run(self) -> None:
        """
        Builds the Docker image for the repository and runs the analysis container.
        This method must be called before performing any searches.
        """
        self.prepare()
        self._run_container()
        self._wait_for_analysis_completion()

    def _create_image_tag(self, build_context: io.BytesIO) -> str:
        build_context.seek(0)
        hasher = hashlib.sha256()
        hasher.update(build_context.read())
        context_hash = hasher.hexdigest()
        build_context.seek(0)  # Reset buffer for build
        return f"repo_read_mcp/seagoat:{context_hash[:16]}"

    def _create_build_context(self) -> io.BytesIO:
        with open(self.dockerfile_base_path, 'rb') as f:
            dockerfile_content = f.read()
        with open(self.run_script_path, 'rb') as f:
            run_script_content = f.read()

        tar_buffer = io.BytesIO()
        with tarfile.open(fileobj=tar_buffer, mode='w') as tar:
            # Add Dockerfile
            df_info = tarfile.TarInfo(name='Dockerfile')
            df_info.size = len(dockerfile_content)
            tar.addfile(df_info, io.BytesIO(dockerfile_content))

            # Add run script
            rs_info = tarfile.TarInfo(name='run.sh')
            rs_info.size = len(run_script_content)
            tar.addfile(rs_info, io.BytesIO(run_script_content))
            
            # Add repo content
            tar.add(self.repo_path, arcname='repo')
            
        tar_buffer.seek(0)
        return tar_buffer
    
    def _get_or_build_image(self, build_context: io.BytesIO) -> Image:
        """Gets an image from cache or builds a new one."""
        try:
            image = self.docker_client.images.get(self.tag)
            print(f"Found existing image for context: {self.tag}")
            return image
        except errors.ImageNotFound:
            print(f"Image not found. Building new image: {self.tag}")
            return self._build_image(build_context)

    def _build_image(self, context: io.BytesIO) -> Image:
        print(f"Building image {self.tag}...")
        try:
            image, logs = self.docker_client.images.build(
                fileobj=context,
                custom_context=True,
                tag=self.tag,
                rm=True,
            )
            for log in logs:
                if isinstance(log, dict):
                    stream = log.get('stream')
                    if stream and isinstance(stream, str):
                        print(stream, end='')
        except errors.BuildError as e:
            print("Failed to build image.")
            for log in e.build_log:
                if isinstance(log, dict):
                    stream = log.get('stream')
                    if stream and isinstance(stream, str):
                        print(stream)
            raise
        return image

    def _run_container(self) -> None:
        print(f"Running container from image {self.tag}...")
        try:
            self.container = self.docker_client.containers.run(
                self.tag,
                detach=True,
                remove=False,
            )
        except errors.ContainerError as e:
            print(f"Failed to run container: {e}")
            raise

    def _wait_for_analysis_completion(self, timeout: int = 300, poll_interval: float = 1.0) -> None:
        if not self.container:
            raise Exception("Container is not running.")

        print("Waiting for analysis to complete...")
        start_time = time.time()

        # Wait for the analysis to complete by polling logs
        last_log_output = ""
        while time.time() - start_time < timeout:
            self.container.reload()
            if self.container.status != 'running':
                logs = self.container.logs().decode('utf-8')
                print(f"Container stopped unexpectedly. Logs:\n{logs}")
                raise Exception("Container stopped unexpectedly during analysis.")

            all_logs = self.container.logs().decode('utf-8')
            new_logs = all_logs[len(last_log_output):]

            if new_logs:
                print(new_logs, end='')
                last_log_output = all_logs

            if self.ANALYSIS_COMPLETE_MESSAGE in all_logs:
                print("\nAnalysis complete.")
                return

            time.sleep(poll_interval)

        # If loop finishes, it's a timeout
        raise TimeoutError("Timeout waiting for container to analyze repository.")

    def search(self, query: str) -> List[Dict[str, Union[str, int]]]:
        if not self.container:
            raise Exception("Container is not running. Please call the .run() method on the Seagoat instance before searching.")

        exec_result = self.container.exec_run(["seagoat", query])
        
        
        if exec_result.exit_code != 0:
            print(f"Error executing search: {exec_result.output.decode('utf-8')}")
            return []

        return self._parse_search_results(exec_result.output.decode('utf-8'))

    def _parse_search_results(self, output: str) -> List[Dict[str, Union[str, int]]]:
        results: List[Dict[str, Union[str, int]]] = []
        current_chunk: Dict[str, Union[str, int]] | None = None

        for line in output.strip().split('\n'):
            if not line:
                continue

            parts = line.split(':', 2)
            if len(parts) < 3:
                continue

            file_path, line_num_str, code = parts
            try:
                line_num = int(line_num_str)
            except ValueError:
                continue

            if (current_chunk and
                    current_chunk['file'] == file_path and
                    isinstance(current_chunk['end_line'], int) and
                    current_chunk['end_line'] + 1 == line_num):
                # This line is a continuation of the current chunk
                current_chunk['end_line'] = line_num
                current_chunk['code'] = str(current_chunk['code']) + '\n' + code
            else:
                # This line starts a new chunk
                if current_chunk:
                    results.append(current_chunk)
                
                current_chunk = {
                    'file': file_path,
                    'start_line': line_num,
                    'end_line': line_num,
                    'code': code,
                }

        if current_chunk:
            results.append(current_chunk)

        return results

    def cleanup(self) -> None:
        if self.container:
            print(f"Stopping and removing container {self.container.id[:12] if self.container.id else self.container.name}...")
            try:
                self.container.stop()
                # self.container.remove()
            except errors.NotFound:
                pass # Already gone
        # The image is intentionally not removed to allow caching across runs.
