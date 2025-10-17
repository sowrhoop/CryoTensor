from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import types
from typing import Any, Dict, Optional

from pydantic import BaseModel, ValidationError, create_model

from open_webui.env import SRC_LOG_LEVELS, PIP_OPTIONS, PIP_PACKAGE_INDEX_OPTIONS
from open_webui.models.functions import Functions
from open_webui.models.tools import Tools
from open_webui.sandbox import SandboxExecutor, SandboxInvocationError, get_sandbox_executor

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])


JSON_TYPE_MAP = {
    "string": str,
    "number": float,
    "integer": int,
    "boolean": bool,
    "array": list,
    "object": dict,
}


def extract_frontmatter(content: str) -> Dict[str, Any]:
    """
    Extract frontmatter as a dictionary from the provided content string.
    """
    frontmatter: Dict[str, Any] = {}
    frontmatter_started = False
    frontmatter_ended = False
    frontmatter_pattern = re.compile(r"^\s*([a-z_]+):\s*(.*)\s*$", re.IGNORECASE)

    try:
        lines = content.splitlines()
        if len(lines) < 1 or lines[0].strip() != '"""':
            return {}

        frontmatter_started = True

        for line in lines[1:]:
            if '"""' in line:
                if frontmatter_started:
                    frontmatter_ended = True
                    break

            if frontmatter_started and not frontmatter_ended:
                match = frontmatter_pattern.match(line)
                if match:
                    key, value = match.groups()
                    frontmatter[key.strip()] = value.strip()

    except Exception as exc:  # pragma: no cover
        log.exception("Failed to extract frontmatter: %s", exc)
        return {}

    return frontmatter


def replace_imports(content: str) -> str:
    """
    Replace legacy import paths in the content.
    """
    replacements = {
        "from utils": "from open_webui.utils",
        "from apps": "from open_webui.apps",
        "from main": "from open_webui.main",
        "from config": "from open_webui.config",
    }

    for old, new in replacements.items():
        content = content.replace(old, new)

    return content


def _schema_to_model(name: str, schema: Optional[Dict[str, Any]]) -> Optional[type[BaseModel]]:
    if not schema:
        return None

    properties = schema.get("properties", {})
    required = set(schema.get("required", []))
    fields: Dict[str, tuple[Any, Any]] = {}

    for field_name, definition in properties.items():
        field_type = JSON_TYPE_MAP.get(definition.get("type", "string"), Any)
        default = definition.get("default")
        if field_name in required and default is None:
            default_val = ...
        else:
            default_val = default

        description = definition.get("description")
        if description:
            fields[field_name] = (
                field_type,
                (default_val if default_val is not None else ...) if default_val is not ... else default_val,
            )
        else:
            fields[field_name] = (field_type, default_val)

    model = create_model(name, **fields)  # type: ignore[arg-type]
    model.__doc__ = schema.get("description")
    return model


def _json_compatible(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except TypeError:
        if isinstance(value, BaseModel):
            return _json_compatible(value.model_dump())
        if isinstance(value, dict):
            return {k: _json_compatible(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [_json_compatible(v) for v in value]
        return repr(value)


class SandboxToolProxy:
    """
    Lightweight object that proxies tool execution through the sandbox
    executor. It mimics the attributes that the rest of the codebase expects.
    """

    def __init__(
        self,
        tool_id: str,
        content: str,
        describe_result: Dict[str, Any],
        executor: SandboxExecutor,
    ) -> None:
        self.id = tool_id
        self._content = content
        self._executor = executor
        self.specs = describe_result.get("specs", [])

        metadata = describe_result.get("metadata", {})
        attributes = metadata.get("attributes", {})
        self.file_handler = attributes.get("file_handler", False)
        self.citation = attributes.get("citation")

        self._docs: Dict[str, str] = metadata.get("docs", {})

        valves_model = _schema_to_model(
            f"{tool_id}_Valves", metadata.get("valves_schema")
        )
        if valves_model is not None:
            self.Valves = valves_model
        elif hasattr(self, "Valves"):
            delattr(self, "Valves")

        user_valves_model = _schema_to_model(
            f"{tool_id}_UserValves", metadata.get("user_valves_schema")
        )
        if user_valves_model is not None:
            self.UserValves = user_valves_model
        elif hasattr(self, "UserValves"):
            delattr(self, "UserValves")

        self.valves: Optional[BaseModel] = None
        self._user_valves: Dict[str, BaseModel] = {}

    @property
    def has_valves(self) -> bool:
        return hasattr(self, "Valves")

    @property
    def has_user_valves(self) -> bool:
        return hasattr(self, "UserValves")

    def set_valves(self, data: Dict[str, Any]) -> None:
        if not hasattr(self, "Valves"):
            self.valves = None
            return

        try:
            valves_cls = getattr(self, "Valves")
            self.valves = valves_cls(**(data or {}))
        except ValidationError as exc:
            raise ValueError(f"Invalid valves configuration: {exc}") from exc

    def set_user_valves(self, user_id: str, data: Dict[str, Any]) -> None:
        if not hasattr(self, "UserValves"):
            return
        try:
            user_valves_cls = getattr(self, "UserValves")
            self._user_valves[user_id] = user_valves_cls(**(data or {}))
        except ValidationError as exc:
            raise ValueError(f"Invalid user valves configuration: {exc}") from exc

    def get_user_valves_payload(self, user_id: str) -> Dict[str, Any]:
        if user_id not in self._user_valves:
            return {}
        return self._user_valves[user_id].model_dump()  # type: ignore[return-value]

    def get_doc(self, function_name: str) -> str:
        return self._docs.get(function_name, "")

    async def invoke(
        self,
        function_name: str,
        params: Dict[str, Any],
        extra_params: Dict[str, Any],
        user_id: Optional[str] = None,
    ) -> Any:
        valves_payload = self.valves.model_dump() if self.valves else {}
        user_valves_payload: Dict[str, Any] = {}
        if user_id is not None:
            user_valves_payload = self.get_user_valves_payload(user_id)

        try:
            return await self._executor.invoke_tool(
                self._content,
                function_name,
                _json_compatible(params),
                _json_compatible(extra_params),
                _json_compatible(valves_payload),
                _json_compatible(user_valves_payload),
            )
        except SandboxInvocationError as exc:
            raise RuntimeError(f"Sandbox invocation failed: {exc}") from exc


def install_frontmatter_requirements(requirements: str) -> None:
    if requirements:
        try:
            req_list = [req.strip() for req in requirements.split(",") if req.strip()]
            if not req_list:
                return
            log.info("Installing requirements: %s", " ".join(req_list))
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install"]
                + PIP_OPTIONS
                + req_list
                + PIP_PACKAGE_INDEX_OPTIONS
            )
        except Exception as exc:  # pragma: no cover
            log.error("Error installing packages: %s", " ".join(req_list))
            raise exc
    else:
        log.info("No requirements found in frontmatter.")


def load_tool_module_by_id(tool_id: str, content: Optional[str] = None):
    executor = get_sandbox_executor()

    if content is None:
        tool = Tools.get_tool_by_id(tool_id)
        if not tool:
            raise Exception(f"Toolkit not found: {tool_id}")
        content = tool.content
        content = replace_imports(content)
        Tools.update_tool_by_id(tool_id, {"content": content})
    else:
        frontmatter = extract_frontmatter(content)
        install_frontmatter_requirements(frontmatter.get("requirements", ""))

    describe_result = executor.describe_tool(content)
    proxy = SandboxToolProxy(tool_id, content, describe_result, executor)
    frontmatter = extract_frontmatter(content)
    log.info("Loaded tool %s via sandbox", tool_id)
    return proxy, frontmatter


def load_function_module_by_id(function_id: str, content: Optional[str] = None):
    """
    For now, function loading continues to use the original behaviour until
    a sandbox-aware proxy analogous to SandboxToolProxy is implemented.
    """
    if content is None:
        function = Functions.get_function_by_id(function_id)
        if not function:
            raise Exception(f"Function not found: {function_id}")
        content = function.content
        content = replace_imports(content)
        Functions.update_function_by_id(function_id, {"content": content})
    else:
        frontmatter = extract_frontmatter(content)
        install_frontmatter_requirements(frontmatter.get("requirements", ""))

    module_name = f"function_{function_id}"
    module = types.ModuleType(module_name)
    sys.modules[module_name] = module  # type: ignore[name-defined]

    temp_file = tempfile.NamedTemporaryFile(delete=False)  # type: ignore[name-defined]
    temp_file.close()
    try:
        with open(temp_file.name, "w", encoding="utf-8") as handle:
            handle.write(content)
        module.__dict__["__file__"] = temp_file.name

        exec(content, module.__dict__)
        frontmatter = extract_frontmatter(content)
        log.info("Loaded module: %s", module.__name__)

        if hasattr(module, "Pipe"):
            return module.Pipe(), "pipe", frontmatter
        if hasattr(module, "Filter"):
            return module.Filter(), "filter", frontmatter
        if hasattr(module, "Action"):
            return module.Action(), "action", frontmatter
        raise Exception("No Function class found in the module")
    except Exception as exc:
        log.error("Error loading function %s: %s", function_id, exc)
        del sys.modules[module_name]
        Functions.update_function_by_id(function_id, {"is_active": False})
        raise exc
    finally:
        os.unlink(temp_file.name)


def get_tool_module_from_cache(request, tool_id: str, load_from_db: bool = True):
    if load_from_db:
        tool = Tools.get_tool_by_id(tool_id)
        if not tool:
            raise Exception(f"Tool not found: {tool_id}")
        content = replace_imports(tool.content)
        if content != tool.content:
            Tools.update_tool_by_id(tool_id, {"content": content})

        cached_content = getattr(request.app.state, "TOOL_CONTENTS", {}).get(tool_id)
        cached_module = getattr(request.app.state, "TOOLS", {}).get(tool_id)
        if cached_module and cached_content == content:
            return cached_module, None

        tool_module, frontmatter = load_tool_module_by_id(tool_id, content)
        content_to_cache = content
    else:
        if hasattr(request.app.state, "TOOLS") and tool_id in request.app.state.TOOLS:
            return request.app.state.TOOLS[tool_id], None
        tool_module, frontmatter = load_tool_module_by_id(tool_id)
        latest_tool = Tools.get_tool_by_id(tool_id)
        content_to_cache = replace_imports(latest_tool.content)

    if not hasattr(request.app.state, "TOOLS"):
        request.app.state.TOOLS = {}
    if not hasattr(request.app.state, "TOOL_CONTENTS"):
        request.app.state.TOOL_CONTENTS = {}

    request.app.state.TOOLS[tool_id] = tool_module
    request.app.state.TOOL_CONTENTS[tool_id] = content_to_cache

    return tool_module, frontmatter


def get_function_module_from_cache(request, function_id: str, load_from_db: bool = True):
    if load_from_db:
        function = Functions.get_function_by_id(function_id)
        if not function:
            raise Exception(f"Function not found: {function_id}")
        content = replace_imports(function.content)
        if content != function.content:
            Functions.update_function_by_id(function_id, {"content": content})

        cached_content = getattr(request.app.state, "FUNCTION_CONTENTS", {}).get(
            function_id
        )
        cached_module = getattr(request.app.state, "FUNCTIONS", {}).get(function_id)
        if cached_module and cached_content == content:
            return cached_module, None, None

        function_module, function_type, frontmatter = load_function_module_by_id(
            function_id, content
        )
        content_to_cache = content
    else:
        if (
            hasattr(request.app.state, "FUNCTIONS")
            and function_id in request.app.state.FUNCTIONS
        ):
            return request.app.state.FUNCTIONS[function_id], None, None

        function_module, function_type, frontmatter = load_function_module_by_id(
            function_id
        )
        latest_function = Functions.get_function_by_id(function_id)
        content_to_cache = replace_imports(latest_function.content)

    if not hasattr(request.app.state, "FUNCTIONS"):
        request.app.state.FUNCTIONS = {}
    if not hasattr(request.app.state, "FUNCTION_CONTENTS"):
        request.app.state.FUNCTION_CONTENTS = {}

    request.app.state.FUNCTIONS[function_id] = function_module
    request.app.state.FUNCTION_CONTENTS[function_id] = content_to_cache

    return function_module, function_type, frontmatter


def install_tool_and_function_dependencies():
    """
    Install all dependencies for all admin tools and active functions as per
    their frontmatter requirements.
    """
    function_list = Functions.get_functions(active_only=True)
    tool_list = Tools.get_tools()

    all_dependencies = ""
    try:
        for function in function_list:
            frontmatter = extract_frontmatter(replace_imports(function.content))
            dependencies = frontmatter.get("requirements")
            if dependencies:
                all_dependencies += f"{dependencies}, "
        for tool in tool_list:
            if tool.user and tool.user.role == "admin":
                frontmatter = extract_frontmatter(replace_imports(tool.content))
                dependencies = frontmatter.get("requirements")
                if dependencies:
                    all_dependencies += f"{dependencies}, "

        install_frontmatter_requirements(all_dependencies.strip(", "))
    except Exception as exc:  # pragma: no cover
        log.error("Error installing requirements: %s", exc)
