"""Register team-monitor hooks in ~/.claude/settings.json.

Detects platform, resolves the plugin path, and writes hook entries
directly into the user's Claude Code settings so they fire on every
session. Run this once after installing the plugin.
"""

import json
import os
import sys

PLUGIN_ROOT = os.environ.get('CLAUDE_PLUGIN_ROOT') or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETTINGS_PATH = os.path.join(os.path.expanduser('~'), '.claude', 'settings.json')

# Marker so uninstall can find our hooks
MARKER = 'team-monitor-plugin'


def get_python_cmd():
    """Return the platform-appropriate python command."""
    if sys.platform == 'win32':
        return 'python'
    return 'python3'


def build_hook_command(script_name):
    """Build a hook command string with the resolved plugin path."""
    py = get_python_cmd()
    script_path = os.path.join(PLUGIN_ROOT, 'hooks', script_name)
    # Normalize path separators
    script_path = script_path.replace('\\', '/')
    return f'{py} "{script_path}"'


def build_hooks_config():
    """Build the hooks dict for all team-monitor events."""
    return {
        'PostToolUse': [
            {
                '_plugin': MARKER,
                'hooks': [
                    {
                        'type': 'command',
                        'command': build_hook_command('posttooluse_hook.py'),
                    }
                ],
            }
        ],
        'SubagentStart': [
            {
                '_plugin': MARKER,
                'hooks': [
                    {
                        'type': 'command',
                        'command': build_hook_command('subagentstart_hook.py'),
                    }
                ],
            }
        ],
        'Stop': [
            {
                '_plugin': MARKER,
                'hooks': [
                    {
                        'type': 'command',
                        'command': build_hook_command('stop_hook.py'),
                    }
                ],
            }
        ],
        'SubagentStop': [
            {
                '_plugin': MARKER,
                'hooks': [
                    {
                        'type': 'command',
                        'command': build_hook_command('stop_hook.py'),
                    }
                ],
            }
        ],
        'Notification': [
            {
                '_plugin': MARKER,
                'hooks': [
                    {
                        'type': 'command',
                        'command': build_hook_command('notification_hook.py'),
                    }
                ],
            }
        ],
    }


def load_settings():
    """Load existing settings or return empty dict."""
    if os.path.exists(SETTINGS_PATH):
        with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_settings(settings):
    """Write settings back to disk."""
    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
    with open(SETTINGS_PATH, 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=2)
        f.write('\n')


def remove_existing_hooks(settings):
    """Remove any previously installed team-monitor hooks."""
    hooks = settings.get('hooks', {})
    for event_name in list(hooks.keys()):
        entries = hooks[event_name]
        if isinstance(entries, list):
            hooks[event_name] = [
                e for e in entries
                if not (isinstance(e, dict) and e.get('_plugin') == MARKER)
            ]
            # Clean up empty arrays
            if not hooks[event_name]:
                del hooks[event_name]
    if not hooks:
        settings.pop('hooks', None)


def install():
    """Install team-monitor hooks into ~/.claude/settings.json."""
    settings = load_settings()

    # Remove any old team-monitor hooks first
    remove_existing_hooks(settings)

    # Merge new hooks
    if 'hooks' not in settings:
        settings['hooks'] = {}

    new_hooks = build_hooks_config()
    for event_name, entries in new_hooks.items():
        if event_name not in settings['hooks']:
            settings['hooks'][event_name] = []
        settings['hooks'][event_name].extend(entries)

    save_settings(settings)

    print(f'Team Monitor hooks installed successfully.')
    print(f'Plugin path: {PLUGIN_ROOT}')
    print(f'Python command: {get_python_cmd()}')
    print(f'Settings file: {SETTINGS_PATH}')
    print(f'')
    print(f'Restart Claude Code for hooks to take effect.')


if __name__ == '__main__':
    install()
