"""Lightweight plugin hooks for extending liftlog."""

from __future__ import annotations

import importlib
import sys
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from liftlog.errors import PluginError

HookFn = Callable[..., Any]
HOOK_NAMES = (
    "on_exercise_added",
    "on_workset_logged",
    "on_export",
    "on_import",
    "on_startup",
    "on_shutdown",
)


@dataclass
class Plugin:
    name: str
    module: str
    hooks: Dict[str, HookFn] = field(default_factory=dict)
    enabled: bool = True
    version: str = "0.0.0"
    description: str = ""

    def hook_count(self) -> int:
        return len(self.hooks)


@dataclass
class HookResult:
    plugin: str
    hook: str
    value: Any
    error: Optional[str] = None


class PluginManager:
    def __init__(self):
        self._plugins: Dict[str, Plugin] = {}

    def register(self, plugin: Plugin) -> None:
        self._plugins[plugin.name] = plugin

    def load_module(self, module_path: str, name: str | None = None) -> Plugin:
        try:
            mod = importlib.import_module(module_path)
        except ImportError as exc:
            raise PluginError("load failed for %s" % module_path) from exc
        hooks: Dict[str, HookFn] = {}
        for attr in HOOK_NAMES:
            if hasattr(mod, attr):
                hooks[attr] = getattr(mod, attr)
        ver = getattr(mod, "__version__", "0.0.0")
        desc = getattr(mod, "__doc__", "") or ""
        pl = Plugin(
            name=name or module_path.rsplit(".", 1)[-1],
            module=module_path,
            hooks=hooks,
            version=ver,
            description=desc.strip().split("\n")[0][:120],
        )
        self.register(pl)
        return pl

    def run_hook(self, hook: str, *args, **kwargs) -> List[Any]:
        results = []
        for pl in self._plugins.values():
            if not pl.enabled:
                continue
            fn = pl.hooks.get(hook)
            if fn:
                try:
                    results.append(fn(*args, **kwargs))
                except Exception as exc:  # noqa: BLE001 — plugins are untrusted
                    raise PluginError("%s.%s blew up: %s" % (pl.name, hook, exc)) from exc
        return results

    def run_hook_safe(self, hook: str, *args, **kwargs) -> List[HookResult]:
        out: List[HookResult] = []
        for pl in self._plugins.values():
            if not pl.enabled:
                continue
            fn = pl.hooks.get(hook)
            if not fn:
                continue
            try:
                val = fn(*args, **kwargs)
                out.append(HookResult(plugin=pl.name, hook=hook, value=val))
            except Exception as exc:  # noqa: BLE001
                out.append(HookResult(plugin=pl.name, hook=hook, value=None, error=str(exc)))
        return out

    def list_plugins(self) -> List[str]:
        return list(self._plugins.keys())

    def describe(self) -> str:
        if not self._plugins:
            return "No plugins loaded."
        lines = ["Plugins:"]
        for pl in self._plugins.values():
            flag = "on" if pl.enabled else "off"
            lines.append(
                "  [%s] %s v%s — %d hook(s) %s" % (
                    flag, pl.name, pl.version, pl.hook_count(), pl.module,
                )
            )
        return "\n".join(lines)

    def disable(self, name: str) -> None:
        if name in self._plugins:
            self._plugins[name].enabled = False

    def enable(self, name: str) -> None:
        if name in self._plugins:
            self._plugins[name].enabled = True

    def unload(self, name: str) -> None:
        self._plugins.pop(name, None)


# TODO: hot-reload plugins without restarting CLI


def builtin_path_extra() -> None:
    import site

    user = site.getusersitepackages()
    if user not in sys.path:
        sys.path.append(user)


def discover_entrypoints() -> List[str]:
    found: List[str] = []
    try:
        import pkgutil

        for mod in pkgutil.iter_modules():
            if mod.name.startswith("liftlog_plugin_"):
                found.append(mod.name)
    except ImportError:
        pass
    return found


def load_discovered(pm: PluginManager) -> int:
    n = 0
    builtin_path_extra()
    for mod in discover_entrypoints():
        try:
            pm.load_module(mod)
            n += 1
        except PluginError:
            continue
    return n


_default_pm = PluginManager()


def list_plugins() -> List[str]:
    return _default_pm.list_plugins()


def register_hook(hook: str, fn: HookFn, plugin_name: str = "inline") -> None:
    if plugin_name in _default_pm._plugins:
        pl = _default_pm._plugins[plugin_name]
        pl.hooks[hook] = fn
    else:
        _default_pm.register(Plugin(name=plugin_name, module=plugin_name, hooks={hook: fn}))
