"""Remove team-monitor hooks from ~/.claude/settings.json.

Cleanly removes only the hooks installed by team-monitor,
leaving all other hooks untouched.
"""

import json
import os
import sys

SETTINGS_PATH = os.path.join(os.path.expanduser('~'), '.claude', 'settings.json')
MARKER = 'team-monitor-plugin'


def uninstall():
    """Remove team-monitor hooks from settings."""
    if not os.path.exists(SETTINGS_PATH):
        print('No settings file found. Nothing to uninstall.')
        return

    with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
        settings = json.load(f)

    hooks = settings.get('hooks', {})
    removed = 0

    for event_name in list(hooks.keys()):
        entries = hooks[event_name]
        if isinstance(entries, list):
            original_count = len(entries)
            hooks[event_name] = [
                e for e in entries
                if not (isinstance(e, dict) and e.get('_plugin') == MARKER)
            ]
            removed += original_count - len(hooks[event_name])
            if not hooks[event_name]:
                del hooks[event_name]

    if not hooks:
        settings.pop('hooks', None)

    with open(SETTINGS_PATH, 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=2)
        f.write('\n')

    if removed > 0:
        print(f'Removed {removed} team-monitor hook(s) from {SETTINGS_PATH}')
        print('Restart Claude Code for changes to take effect.')
    else:
        print('No team-monitor hooks found. Nothing to remove.')


if __name__ == '__main__':
    uninstall()
