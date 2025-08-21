"""Tests for liftlog.plugins."""

import sys
import types

import pytest
from liftlog.errors import PluginError
from liftlog.plugins import Plugin, PluginManager, builtin_path_extra


def test_register_plugin():
    pm = PluginManager()
    pl = Plugin(name="demo", module="demo")
    pm.register(pl)
    assert "demo" in pm.list_plugins()


def test_load_module_with_hook(tmp_path, monkeypatch):
    mod = types.ModuleType("fake_plugin")

    def on_exercise_added(exercise):
        return exercise.title

    mod.on_exercise_added = on_exercise_added
    sys.modules["fake_plugin"] = mod
    pm = PluginManager()
    pl = pm.load_module("fake_plugin", name="fake")
    assert "on_exercise_added" in pl.hooks
    sys.modules.pop("fake_plugin", None)


def test_load_module_missing():
    pm = PluginManager()
    with pytest.raises(PluginError):
        pm.load_module("definitely_not_a_real_module_xyz")


def test_run_hook_collects_results():
    pm = PluginManager()
    pl = Plugin(name="p", module="m", hooks={"on_export": lambda **kw: 42})
    pm.register(pl)
    assert pm.run_hook("on_export") == [42]


def test_run_hook_skips_disabled():
    pm = PluginManager()
    pl = Plugin(name="p", module="m", hooks={"on_export": lambda: 1}, enabled=False)
    pm.register(pl)
    assert pm.run_hook("on_export") == []


def test_run_hook_unknown_hook():
    pm = PluginManager()
    pm.register(Plugin(name="p", module="m"))
    assert pm.run_hook("nope") == []


def test_run_hook_plugin_exception():
    pm = PluginManager()

    def boom():
        raise RuntimeError("fail")

    pm.register(Plugin(name="bad", module="m", hooks={"on_exercise_added": boom}))
    with pytest.raises(PluginError):
        pm.run_hook("on_exercise_added")


def test_list_plugins_empty():
    assert PluginManager().list_plugins() == []


def test_plugin_defaults():
    pl = Plugin(name="x", module="y")
    assert pl.enabled is True
    assert pl.hooks == {}


def test_load_module_default_name():
    mod = types.ModuleType("pkg.myplugin")
    mod.on_workset_logged = lambda s: s
    sys.modules["pkg.myplugin"] = mod
    pm = PluginManager()
    pl = pm.load_module("pkg.myplugin")
    assert pl.name == "myplugin"
    sys.modules.pop("pkg.myplugin", None)


def test_run_hook_multiple_plugins():
    pm = PluginManager()
    pm.register(Plugin(name="a", module="m", hooks={"on_export": lambda: 1}))
    pm.register(Plugin(name="b", module="m", hooks={"on_export": lambda: 2}))
    assert pm.run_hook("on_export") == [1, 2]


def test_builtin_path_extra_runs():
    builtin_path_extra()  # shouldn't raise


def test_on_export_hook_only():
    mod = types.ModuleType("exp")
    mod.on_export = lambda fmt: fmt
    sys.modules["exp"] = mod
    pm = PluginManager()
    pl = pm.load_module("exp")
    assert "on_export" in pl.hooks
    sys.modules.pop("exp", None)


def test_plugin_name_stored():
    pl = Plugin(name="custom", module="mod")
    assert pl.name == "custom"


def test_register_overwrites():
    pm = PluginManager()
    pm.register(Plugin(name="x", module="a"))
    pm.register(Plugin(name="x", module="b"))
    assert len(pm.list_plugins()) == 1


def test_run_hook_passes_args():
    seen = {}

    def capture(*args, **kwargs):
        seen["kwargs"] = kwargs

    pm = PluginManager()
    pm.register(Plugin(name="p", module="m", hooks={"on_exercise_added": capture}))
    pm.run_hook("on_exercise_added", title="T")
    assert seen["kwargs"]["title"] == "T"


def test_hooks_optional_attrs():
    mod = types.ModuleType("minimal")
    sys.modules["minimal"] = mod
    pl = PluginManager().load_module("minimal")
    assert pl.hooks == {}
    sys.modules.pop("minimal", None)


def test_plugin_error_from_load():
    with pytest.raises(PluginError):
        PluginManager().load_module("no_such_module_abc123")

from liftlog.plugins import HookResult, discover_entrypoints, load_discovered


def test_run_hook_safe():
    pm = PluginManager()
    pm.register(Plugin(name="p", module="m", hooks={"on_export": lambda: 99}))
    results = pm.run_hook_safe("on_export")
    assert results[0].value == 99


def test_run_hook_safe_catches_error():
    pm = PluginManager()

    def boom():
        raise RuntimeError("x")

    pm.register(Plugin(name="bad", module="m", hooks={"on_export": boom}))
    res = pm.run_hook_safe("on_export")
    assert res[0].error


def test_describe_empty():
    assert "No plugins" in PluginManager().describe()


def test_describe_loaded():
    pm = PluginManager()
    pm.register(Plugin(name="demo", module="m", version="1.0.0"))
    assert "demo" in pm.describe()


def test_disable_enable_unload():
    pm = PluginManager()
    pm.register(Plugin(name="p", module="m", hooks={"on_export": lambda: 1}))
    pm.disable("p")
    assert pm.run_hook("on_export") == []
    pm.enable("p")
    assert pm.run_hook("on_export") == [1]
    pm.unload("p")
    assert pm.list_plugins() == []


def test_hook_count():
    pl = Plugin(name="x", module="y", hooks={"on_export": lambda: None})
    assert pl.hook_count() == 1


def test_discover_entrypoints_list():
    assert isinstance(discover_entrypoints(), list)


def test_load_discovered():
    pm = PluginManager()
    assert load_discovered(pm) >= 0


def test_load_module_version_doc():
    import sys
    import types

    mod = types.ModuleType("verplug")
    mod.__version__ = "2.0"
    mod.__doc__ = "A test plugin"
    sys.modules["verplug"] = mod
    pl = PluginManager().load_module("verplug")
    assert pl.version == "2.0"
    sys.modules.pop("verplug", None)
