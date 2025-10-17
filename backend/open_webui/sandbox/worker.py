import json
import sys
import traceback
from types import ModuleType
from typing import Any, Dict


def _load_tools_instance(content: str) -> tuple[ModuleType, Any]:
    """
    Execute the provided tool content inside this isolated worker process and
    return both the transient module and an instantiated ``Tools`` object.
    """
    module = ModuleType("maestro_tool")
    exec(compile(content, "<sandboxed-tool>", "exec"), module.__dict__)

    if not hasattr(module, "Tools"):
        raise RuntimeError("The provided tool does not define a 'Tools' class")

    tools_cls = getattr(module, "Tools")
    tools_instance = tools_cls()
    return module, tools_instance


def _describe_tool(content: str) -> Dict[str, Any]:
    from open_webui.utils.tools import get_tool_specs

    module, tools_instance = _load_tools_instance(content)
    specs = get_tool_specs(tools_instance)

    metadata: Dict[str, Any] = {
        "has_valves": hasattr(module, "Valves"),
        "has_user_valves": hasattr(module, "UserValves"),
        "attributes": {
            "file_handler": bool(getattr(module, "file_handler", False)),
            "citation": getattr(module, "citation", None),
        },
    }

    if hasattr(module, "Valves"):
        valves = getattr(module, "Valves")
        if hasattr(valves, "model_json_schema"):
            metadata["valves_schema"] = valves.model_json_schema()
        elif hasattr(valves, "schema"):
            metadata["valves_schema"] = valves.schema()

    if hasattr(module, "UserValves"):
        user_valves = getattr(module, "UserValves")
        if hasattr(user_valves, "model_json_schema"):
            metadata["user_valves_schema"] = user_valves.model_json_schema()
        elif hasattr(user_valves, "schema"):
            metadata["user_valves_schema"] = user_valves.schema()

    callable_docs: Dict[str, str] = {}
    for attribute in dir(tools_instance):
        if attribute.startswith("__"):
            continue
        candidate = getattr(tools_instance, attribute)
        if callable(candidate):
            callable_docs[attribute] = getattr(candidate, "__doc__", "") or ""

    metadata["docs"] = callable_docs
    return {
        "specs": specs,
        "metadata": metadata,
    }


def _invoke_tool(
    content: str,
    function_name: str,
    params: Dict[str, Any],
    extra_params: Dict[str, Any],
    valves_data: Dict[str, Any],
    user_valves_data: Dict[str, Any],
) -> Any:
    module, tools_instance = _load_tools_instance(content)

    # Apply Valves configuration if available
    if hasattr(module, "Valves"):
        valves_cls = getattr(module, "Valves")
        if valves_data:
            tools_instance.valves = valves_cls(**valves_data)
        else:
            tools_instance.valves = valves_cls()

    if hasattr(module, "UserValves"):
        user_valves_cls = getattr(module, "UserValves")
        if user_valves_data:
            tools_instance.user_valves = user_valves_cls(**user_valves_data)
        else:
            tools_instance.user_valves = user_valves_cls()

    if not hasattr(tools_instance, function_name):
        raise RuntimeError(f"Tool does not expose function '{function_name}'")

    target = getattr(tools_instance, function_name)
    if not callable(target):
        raise RuntimeError(f"Attribute '{function_name}' is not callable")

    # Inject extra params that are not part of the function signature
    call_kwargs = dict(params)
    call_kwargs.update({k: v for k, v in extra_params.items() if k not in call_kwargs})
    return target(**call_kwargs)


def main() -> None:
    try:
        request = json.load(sys.stdin)
        action = request.get("action")
        content = request.get("content", "")
        if not content:
            raise ValueError("Tool content is required")

        if action == "describe":
            result = _describe_tool(content)
        elif action == "invoke":
            function_name = request.get("function_name")
            if not function_name:
                raise ValueError("function_name is required for invoke calls")
            params = request.get("params") or {}
            extra_params = request.get("extra_params") or {}
            valves = request.get("valves") or {}
            user_valves = request.get("user_valves") or {}
            value = _invoke_tool(
                content,
                function_name,
                params,
                extra_params,
                valves,
                user_valves,
            )
            try:
                json.dumps(value)
            except TypeError:
                value = repr(value)
            result = {"value": value}
        else:
            raise ValueError(f"Unsupported action '{action}'")

        json.dump({"ok": True, "result": result}, sys.stdout)
    except Exception as exc:  # pragma: no cover - defensive
        traceback.print_exc()
        json.dump(
            {
                "ok": False,
                "error": str(exc),
                "traceback": traceback.format_exc(),
            },
            sys.stdout,
        )


if __name__ == "__main__":
    main()
