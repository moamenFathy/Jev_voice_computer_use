"""
JEV Tool Subsystem & Registry Initialization.
"""

from src.tools.base import BaseTool, ToolRegistry, tool_registry
from src.tools.app_launch_tool import AppLaunchTool
from src.tools.ui_interaction_tool import ClickUIElementTool, TypeTextTool, InAppSearchTool
from src.tools.web_tool import WebNavigationTool, GoogleSearchTool
from src.tools.media_tool import (
    YouTubeMusicTool,
    YouTubeTool,
    SpotifyTool,
    AnghamiTool,
    SoundCloudTool,
    MediaPlaybackTool,
)
from src.tools.system_tool import (
    VolumeTool,
    WindowManagementTool,
    DocumentShortcutTool,
    MathCalculateTool,
)

# Populate global tool registry
tool_registry.register(AppLaunchTool())
tool_registry.register(ClickUIElementTool())
tool_registry.register(TypeTextTool())
tool_registry.register(InAppSearchTool())
tool_registry.register(WebNavigationTool())
tool_registry.register(GoogleSearchTool())
tool_registry.register(YouTubeMusicTool())
tool_registry.register(YouTubeTool())
tool_registry.register(SpotifyTool())
tool_registry.register(AnghamiTool())
tool_registry.register(SoundCloudTool())
tool_registry.register(MediaPlaybackTool())
tool_registry.register(VolumeTool())
tool_registry.register(WindowManagementTool())
tool_registry.register(DocumentShortcutTool())
tool_registry.register(MathCalculateTool())

__all__ = [
    "BaseTool",
    "ToolRegistry",
    "tool_registry",
    "AppLaunchTool",
    "ClickUIElementTool",
    "TypeTextTool",
    "InAppSearchTool",
    "WebNavigationTool",
    "GoogleSearchTool",
    "YouTubeMusicTool",
    "YouTubeTool",
    "SpotifyTool",
    "AnghamiTool",
    "SoundCloudTool",
    "MediaPlaybackTool",
    "VolumeTool",
    "WindowManagementTool",
    "DocumentShortcutTool",
    "MathCalculateTool",
]
