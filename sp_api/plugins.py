"""
Plugin system for SP-API SDK.

Provides an extensible architecture for adding custom API modules,
hooks, and middleware without modifying core code.
"""

import importlib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class PluginMeta:
    """Metadata for a plugin."""

    def __init__(self, name, version="1.0.0", author="", description="",
                 requires=None):
        self.name = name
        self.version = version
        self.author = author
        self.description = description
        self.requires = requires or []

    def __repr__(self):
        return f"PluginMeta({self.name!r} v{self.version})"


class PluginHook:
    """Hook point for plugin event listeners."""

    def __init__(self, name):
        self.name = name
        self._listeners = []

    def register(self, fn, priority=0):
        """Register a listener with optional priority (lower = earlier)."""
        self._listeners.append((priority, fn))
        self._listeners.sort(key=lambda x: x[0])

    def unregister(self, fn):
        """Remove a listener."""
        self._listeners = [(p, f) for p, f in self._listeners if f is not fn]

    def fire(self, *args, **kwargs):
        """Fire the hook, calling all listeners in priority order."""
        results = []
        for _, fn in self._listeners:
            try:
                result = fn(*args, **kwargs)
                results.append(result)
            except Exception as e:
                logger.error("Hook %s listener error: %s", self.name, e)
        return results

    def __len__(self):
        return len(self._listeners)

    def __repr__(self):
        return f"PluginHook({self.name!r}, listeners={len(self._listeners)})"


class SPAPIPlugin:
    """
    Base class for SP-API plugins.

    Subclass this to create custom plugins:

        class MyPlugin(SPAPIPlugin):
            meta = PluginMeta("my-plugin", "1.0.0")

            def on_load(self, client):
                # Add methods to client
                client.my_custom_method = self.custom_method

            def on_request(self, method, path, params, body):
                # Modify requests before sending
                return method, path, params, body

            def on_response(self, response, path):
                # Process responses
                return response

            def custom_method(self):
                return "Hello from plugin!"
    """

    meta = PluginMeta("base-plugin")

    def on_load(self, client):
        """Called when plugin is loaded into a client."""
        pass

    def on_unload(self, client):
        """Called when plugin is removed from a client."""
        pass

    def on_request(self, method, path, params, body):
        """
        Called before each API request.
        Return (method, path, params, body) — modified or original.
        """
        return method, path, params, body

    def on_response(self, response, path):
        """
        Called after each API response.
        Return the (possibly modified) response.
        """
        return response

    def on_error(self, error, path):
        """Called when an API request fails."""
        pass


class PluginRegistry:
    """
    Registry and lifecycle manager for SP-API plugins.

    Usage:
        registry = PluginRegistry()
        registry.register(MyPlugin())
        registry.load_all(client)

        # Or load from a directory
        registry.load_from_directory("/path/to/plugins/")
    """

    def __init__(self):
        self._plugins = {}
        self._hooks = {
            "pre_request": PluginHook("pre_request"),
            "post_response": PluginHook("post_response"),
            "on_error": PluginHook("on_error"),
            "on_auth": PluginHook("on_auth"),
            "on_throttle": PluginHook("on_throttle"),
        }

    def register(self, plugin, priority=0):
        """
        Register a plugin.

        Args:
            plugin: SPAPIPlugin instance
            priority: Load priority (lower = earlier)
        """
        if not isinstance(plugin, SPAPIPlugin):
            raise TypeError(f"Expected SPAPIPlugin, got {type(plugin)}")

        name = plugin.meta.name
        if name in self._plugins:
            logger.warning("Plugin %s already registered, replacing", name)

        self._plugins[name] = (priority, plugin)

        # Register hooks
        if hasattr(plugin, "on_request"):
            self._hooks["pre_request"].register(plugin.on_request, priority)
        if hasattr(plugin, "on_response"):
            self._hooks["post_response"].register(plugin.on_response, priority)
        if hasattr(plugin, "on_error"):
            self._hooks["on_error"].register(plugin.on_error, priority)

        logger.info("Registered plugin: %s v%s", name, plugin.meta.version)

    def unregister(self, name):
        """Remove a plugin by name."""
        if name in self._plugins:
            _, plugin = self._plugins.pop(name)
            for hook in self._hooks.values():
                for method_name in ("on_request", "on_response", "on_error"):
                    method = getattr(plugin, method_name, None)
                    if method:
                        hook.unregister(method)
            logger.info("Unregistered plugin: %s", name)
        else:
            raise KeyError(f"Plugin not found: {name}")

    def load_all(self, client):
        """Load all registered plugins into a client."""
        sorted_plugins = sorted(self._plugins.values(), key=lambda x: x[0])
        for _, plugin in sorted_plugins:
            try:
                plugin.on_load(client)
                logger.info("Loaded plugin: %s", plugin.meta.name)
            except Exception as e:
                logger.error("Failed to load plugin %s: %s", plugin.meta.name, e)

    def unload_all(self, client):
        """Unload all plugins from a client."""
        for _, plugin in self._plugins.values():
            try:
                plugin.on_unload(client)
            except Exception as e:
                logger.error("Error unloading plugin %s: %s", plugin.meta.name, e)

    def fire_hook(self, hook_name, *args, **kwargs):
        """Fire a named hook."""
        hook = self._hooks.get(hook_name)
        if hook:
            return hook.fire(*args, **kwargs)
        return []

    def get_hook(self, hook_name):
        """Get a hook by name, creating it if needed."""
        if hook_name not in self._hooks:
            self._hooks[hook_name] = PluginHook(hook_name)
        return self._hooks[hook_name]

    def load_from_directory(self, directory):
        """
        Discover and load plugins from a directory.

        Looks for Python files with a `plugin` attribute that is
        an SPAPIPlugin subclass instance.
        """
        plugin_dir = Path(directory)
        if not plugin_dir.is_dir():
            logger.warning("Plugin directory not found: %s", directory)
            return

        for py_file in sorted(plugin_dir.glob("*.py")):
            if py_file.name.startswith("_"):
                continue
            try:
                spec = importlib.util.spec_from_file_location(
                    py_file.stem, py_file
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                plugin = getattr(module, "plugin", None)
                if isinstance(plugin, SPAPIPlugin):
                    self.register(plugin)
                else:
                    # Look for SPAPIPlugin subclass instances
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if isinstance(attr, SPAPIPlugin):
                            self.register(attr)
                            break
            except Exception as e:
                logger.error("Error loading plugin from %s: %s", py_file, e)

    @property
    def plugins(self):
        """List registered plugin names."""
        return list(self._plugins.keys())

    @property
    def plugin_count(self):
        return len(self._plugins)

    def get_plugin(self, name):
        """Get a plugin by name."""
        if name in self._plugins:
            return self._plugins[name][1]
        raise KeyError(f"Plugin not found: {name}")

    def __contains__(self, name):
        return name in self._plugins

    def __repr__(self):
        names = ", ".join(self._plugins.keys())
        return f"PluginRegistry([{names}])"


# ── Built-in Plugins ─────────────────────────────────────


class RequestLoggerPlugin(SPAPIPlugin):
    """Plugin that logs all API requests and responses."""

    meta = PluginMeta(
        "request-logger", "1.0.0",
        description="Logs all SP-API requests and responses",
    )

    def __init__(self, log_level=logging.DEBUG):
        self.log_level = log_level
        self.request_log = []

    def on_request(self, method, path, params, body):
        entry = {
            "method": method,
            "path": path,
            "params": params,
            "has_body": body is not None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.request_log.append(entry)
        logger.log(self.log_level, "SP-API %s %s", method, path)
        return method, path, params, body

    def on_response(self, response, path):
        logger.log(self.log_level, "SP-API response for %s: OK", path)
        return response

    def get_log(self, last_n=None):
        if last_n:
            return self.request_log[-last_n:]
        return self.request_log

    def clear_log(self):
        self.request_log.clear()


class CostTrackerPlugin(SPAPIPlugin):
    """Plugin that tracks estimated API costs."""

    meta = PluginMeta(
        "cost-tracker", "1.0.0",
        description="Tracks estimated SP-API usage costs",
    )

    # Approximate cost per call (varies by plan)
    DEFAULT_COST = 0.0001  # $0.0001 per call

    def __init__(self):
        self.total_calls = 0
        self.total_cost = 0.0
        self.calls_by_path = {}

    def on_request(self, method, path, params, body):
        self.total_calls += 1
        self.total_cost += self.DEFAULT_COST
        self.calls_by_path[path] = self.calls_by_path.get(path, 0) + 1
        return method, path, params, body

    def get_summary(self):
        return {
            "total_calls": self.total_calls,
            "estimated_cost_usd": round(self.total_cost, 6),
            "top_endpoints": sorted(
                self.calls_by_path.items(),
                key=lambda x: x[1],
                reverse=True,
            )[:10],
        }

    def reset(self):
        self.total_calls = 0
        self.total_cost = 0.0
        self.calls_by_path.clear()


class ResponseCachePlugin(SPAPIPlugin):
    """Plugin that caches responses to reduce API calls."""

    meta = PluginMeta(
        "response-cache", "1.0.0",
        description="Caches SP-API responses with TTL",
    )

    def __init__(self, default_ttl=300):
        self.default_ttl = default_ttl
        self._cache = {}
        self.hits = 0
        self.misses = 0

    def _cache_key(self, method, path, params, body):
        import hashlib
        key_str = f"{method}:{path}:{params}:{body}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def on_request(self, method, path, params, body):
        if method == "GET":
            key = self._cache_key(method, path, params, body)
            cached = self._cache.get(key)
            if cached:
                ts, data = cached
                if time.time() - ts < self.default_ttl:
                    self.hits += 1
                    return method, path, params, body
        self.misses += 1
        return method, path, params, body

    def on_response(self, response, path):
        return response

    def invalidate(self, path_pattern=None):
        if path_pattern:
            self._cache = {
                k: v for k, v in self._cache.items()
                if path_pattern not in k
            }
        else:
            self._cache.clear()

    @property
    def stats(self):
        total = self.hits + self.misses
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.hits / total if total else 0,
            "cache_size": len(self._cache),
        }
