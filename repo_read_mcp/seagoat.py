import docker
from docker import errors
import tarfile
import io
import atexit
import hashlib
import re
from typing import Dict, List, Union

import docker.client
from docker.models.containers import Container
from docker.models.images import Image


class Seagoat:
    repo_path: str
    dockerfile_base_path: str
    docker_client: docker.client.DockerClient
    image: Image | None
    container: Container | None
    tag: str

    def __init__(self, repo_path: str, dockerfile_base_path: str = "repo_read_mcp/templates/Dockerfile.seagoat.base") -> None:
        self.repo_path = repo_path
        self.dockerfile_base_path = dockerfile_base_path
        self.docker_client = docker.from_env()
        self.image = None
        self.container = None
        
        build_context = self._create_build_context()
        self.tag = self._create_image_tag(build_context)

        self.image = self._get_or_build_image(build_context)

        self._run_container()

        atexit.register(self.cleanup)

    def _create_image_tag(self, build_context: io.BytesIO) -> str:
        build_context.seek(0)
        hasher = hashlib.sha256()
        hasher.update(build_context.read())
        context_hash = hasher.hexdigest()
        build_context.seek(0)  # Reset buffer for build
        return f"repo_read_mcp/test:{context_hash[:16]}"

    def _read_dockerfile_template(self, path: str) -> bytes:
        with open(path, 'rb') as f:
            return f.read()

    def _create_build_context(self) -> io.BytesIO:
        dockerfile_content = self._read_dockerfile_template(self.dockerfile_base_path)
        tar_buffer = io.BytesIO()
        with tarfile.open(fileobj=tar_buffer, mode='w') as tar:
            # Add Dockerfile
            df_info = tarfile.TarInfo(name='Dockerfile')
            df_info.size = len(dockerfile_content)
            tar.addfile(df_info, io.BytesIO(dockerfile_content))
            
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
            )
        except errors.ContainerError as e:
            print(f"Failed to run container: {e}")
            raise

    def search(self, query: str) -> List[Dict[str, Union[str, int]]]:
        if not self.container:
            raise Exception("Container is not running.")

        exec_result = self.container.exec_run(["seagoat", query])
        
        
        if exec_result.exit_code != 0:
            print(f"Error executing search: {exec_result.output.decode('utf-8')}")
            return []

        return self._parse_search_results(exec_result.output.decode('utf-8'))

    def _parse_search_results(self, output: str) -> List[Dict[str, Union[str, int]]]:
        # debug
        print('output', output)
        return []
        
        
        results: List[Dict[str, Union[str, int]]] = []
        
        # Regex to capture score, file path, line numbers, and the first line of code
        # The output format seems to be: score, path:start-end, code
        # The code can span multiple lines.
        
        # Split output into blocks for each result
        # A new result block starts with a line that has a similarity score.
        result_blocks = []
        current_block = ""
        for line in output.strip().split('\n'):
            # A new result starts with something like "0.42     ..."
            if re.match(r'^\d+\.\d+\s+', line):
                if current_block:
                    result_blocks.append(current_block)
                current_block = line + '\n'
            else:
                current_block += line + '\n'
        if current_block:
            result_blocks.append(current_block)

        for block in result_blocks:
            lines = block.strip().split('\n')
            first_line = lines[0]
            
            match = re.match(r'^(?P<score>\d+\.\d+)\s+(?P<file>.+?):(?P<start_line>\d+)-(?P<end_line>\d+)\s+(?P<code>.*)', first_line)
            
            if not match:
                # sometimes the code part is on the next line
                 match = re.match(r'^(?P<score>\d+\.\d+)\s+(?P<file>.+?):(?P<start_line>\d+)-(?P<end_line>\d+)', first_line)
                 if match:
                    code = '\n'.join(lines[1:])
                 else:
                    continue
            else:
                code = match.group('code')
                if len(lines) > 1:
                    code += '\n' + '\n'.join(l.lstrip() for l in lines[1:])


            if match:
                results.append({
                    'file': match.group('file').strip(),
                    'start_line': int(match.group('start_line')),
                    'end_line': int(match.group('end_line')),
                    'code': code.strip()
                })

        return results

    def cleanup(self) -> None:
        if self.container:
            print(f"Stopping and removing container {self.container.id[:12] if self.container.id else self.container.name}...")
            try:
                self.container.stop()
                self.container.remove()
            except errors.NotFound:
                pass # Already gone
        # The image is intentionally not removed to allow caching across runs.
