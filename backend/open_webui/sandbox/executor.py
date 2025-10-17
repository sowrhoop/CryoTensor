import asyncio
import json
import os
import sys
import threading
from pathlib import Path
from typing import Any, Dict, Optional


class SandboxInvocationError(RuntimeError):
    """Raised when the sandboxed worker returns an error."""


class SandboxExecutor:
    """
    Helper that delegates tool loading and invocation to an isolated worker
    process.
    """

    def __init__(
        self,
        sandbox_binary: Optional[str] = None,
        python_executable: Optional[str] = None,
    ) -> None:
        self._sandbox_binary = sandbox_binary or os.getenv(
            "MAESTRO_SANDBOX_BIN", "maestro-sandbox"
        )
        self._python_executable = python_executable or sys.executable
        self._worker_module = "open_webui.sandbox.worker"

    async def _run_async(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the sandbox worker with the provided payload and return
        the decoded JSON response.
        """

        command = [
            self._sandbox_binary,
            "--",
            self._python_executable,
            "-m",
            self._worker_module,
        ]

        process: asyncio.subprocess.Process
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError:
            # Fallback to plain Python execution when the sandbox wrapper
            # is not available. This still executes in a separate process,
            # but without additional isolation.
            process = await asyncio.create_subprocess_exec(
                self._python_executable,
                "-m",
                self._worker_module,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

        request_bytes = json.dumps(payload).encode("utf-8")
        stdout, stderr = await process.communicate(request_bytes)
        if process.returncode != 0:
            message = stderr.decode("utf-8", errors="ignore").strip()
            if not message:
                message = stdout.decode("utf-8", errors="ignore").strip()
            raise SandboxInvocationError(
                f"Sandbox worker exited with status {process.returncode}: {message}"
            )

        try:
            response = json.loads(stdout.decode("utf-8"))
        except json.JSONDecodeError as exc:  # pragma: no cover
            raise SandboxInvocationError(
                f"Failed to decode sandbox response: {exc}"
            ) from exc

        if not isinstance(response, dict) or not response.get("ok", False):
            error_message = response.get("error", "Unknown sandbox error")
            raise SandboxInvocationError(error_message)

        return response.get("result", {})

    def _run_sync(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synchronous helper that executes the coroutine directly. This function
        is called only in contexts where no running event loop is expected.
        """
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self._run_async(payload))

        result: Dict[str, Any] = {}
        error: Optional[BaseException] = None

        def runner() -> None:
            nonlocal result, error
            try:
                result = asyncio.run(self._run_async(payload))
            except BaseException as exc:  # pragma: no cover - defensive
                error = exc

        thread = threading.Thread(target=runner, daemon=True)
        thread.start()
        thread.join()

        if error is not None:
            raise error

        return result

    def describe_tool(self, content: str) -> Dict[str, Any]:
        """
        Retrieve metadata for the provided tool content without executing it
        inside the current process.
        """
        payload = {"action": "describe", "content": content}
        return self._run_sync(payload)

    async def invoke_tool(
        self,
        content: str,
        function_name: str,
        params: Dict[str, Any],
        extra_params: Optional[Dict[str, Any]] = None,
        valves: Optional[Dict[str, Any]] = None,
        user_valves: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Invoke a single function from the tool. The call happens entirely inside
        the sandbox worker.
        """
        payload = {
            "action": "invoke",
            "content": content,
            "function_name": function_name,
            "params": params,
            "extra_params": extra_params or {},
            "valves": valves or {},
            "user_valves": user_valves or {},
        }
        result = await self._run_async(payload)
        return result.get("value")


_singleton_executor: Optional[SandboxExecutor] = None


def get_sandbox_executor() -> SandboxExecutor:
    global _singleton_executor
    if _singleton_executor is None:
        _singleton_executor = SandboxExecutor()
    return _singleton_executor
