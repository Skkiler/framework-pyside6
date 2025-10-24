<p align="center">
  <img src="app/assets/icons/app/app.ico" width="96" alt="App Icon" />
</p>

<p align="center">
  <a href="README.md">Ler em Português</a>
</p>

# UI Exec Framework (PySide6)

Modern foundation for desktop apps with Python + PySide6. It includes a frameless window, hierarchical routing, a themed system (QSS + JSON) with smooth animations, toasts and a Notification Center, plus a CLI to speed up development.

---

## Table of Contents

- [Overview](#overview)
- [Installation (PyPI) & Quick Start](#installation-pypi--quick-start)
- [Architecture](#architecture)
- [Install & Setup](#install--setup)
- [Run & Shortcuts](#run--shortcuts)
- [Pages & Routing](#pages--routing)
  - [Manifest](#manifest-appassetspages_manifestjson)
  - [Auto-discovery](#auto-discovery-apppages)
  - [Dependency Injection](#dependency-injection)
  - [Router Features](#router-features)
- [Themes (QSS + JSON)](#themes-qss--json)
  - [Structure & Example](#structure--example)
  - [ThemeService](#themeservice)
  - [Editor & Panel](#editor--panel)
  - [QSS Placeholders](#qss-placeholders-qss_renderer)
- [Toasts & Notifications](#toasts--notifications)
  - [APIs](#apis)
  - [Notification Center](#notification-center-right-push-panel)
  - [Example](#example)
- [CLI](#cli)
  - [new page](#new-page)
  - [new subpage](#new-subpage)
  - [examples](#examples)
  - [manifest-update](#manifest-update)
  - [clean-pages](#clean-pages)
- [Manual Page Creation](#manual-page-creation-without-cli)
- [Manual Subpages](#manual-subpages-without-cli)
- [Widgets: Cookbook](#widgets-cookbook)
  - [Buttons](#buttons-controlsbutton--primarybutton)
  - [Command Buttons](#command-buttons-taskrunner)
  - [Confirm + Command](#confirm--command)
  - [Route Navigation](#route-navigation-route_button)
  - [Basic Controls](#basic-controls-toggle--checkbox--textinput--select)
  - [Icon & Link](#icon--linklabel)
  - [Help Popover](#help-popover-hover)
  - [Expand/Collapse Panel](#expandcollapse-panel-expandmore)
  - [Progress Slider](#progress-slider-non-interactive)
  - [Custom Scroll](#custom-scroll)
  - [AsyncTaskButton](#asynctaskbutton-async-tasks)
  - [Toasts](#toasts-simple-action-and-progress)
  - [LoadingOverlay](#loadingoverlay-manual)
  - [Quick Open](#quick-open-programmatic)
- [Visual Customization & Chrome](#visual-customization--chrome)
- [Notification Center (Advanced)](#notification-center-advanced)
- [Themes: Tips & Advanced](#themes-tips--advanced)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)
- [Roadmap](#roadmap)
- [Page Blueprint](#page-blueprint-recommended)
- [Code Quality (Linting & Style)](#code-quality-linting--style)

---

## Installation (PyPI) & Quick Start

Install or upgrade the library:

```
pip install ui-fram-skk
# or
pip install -U ui-fram-skk
```

Bootstrap a new project and run it:

```
# 1) Initialize an app skeleton (creates app/, assets/, pages/, etc.)
ui-cli init

# 2) Run the generated app
python -m app.app

# 3) (Optional) Generate pages via CLI
ui-cli new page "Reports" --route reports --label "Reports" --sidebar --order 10
```

Quick CLI help:

```
ui-cli --help
```

---

## Overview

Highlights
- Frameless window with shadow and rounded corners.
- Page routing with auto-discovery and manifest.
- Dynamic themes via QSS + JSON with smooth transitions.
- Quick Open (Ctrl+K) to jump between routes.
- TopBar with clickable breadcrumbs and unread badge on the bell.
- Right-push Notification Center integrated with toasts.
- Simple, actionable and progress toasts.
- Persisted theme and last route in a JSON cache.
- CLI for scaffolding, examples, cleanup and manifest maintenance.
- Dependency injection (task_runner, theme_service) for pages.

What’s new
- Router v2: hierarchical routes (`home/tools/details`), history (Alt+Left/Alt+Right), `routeChanged` and per-page `on_route(params)` hook.
- Quick Open (Ctrl+K) via `ui/dialogs/quick_open.py`.
- Notification Center with PushSidePanel and `notification_bus()`.
- ThemeService: watches `base.qss` and themes, derived tokens and dump of the applied QSS.
- TitleBar with animated icon (cross-fade) and theme sync.
- TaskRunnerAdapter accepts `async def run_task(...)`.

---

## Architecture

Directory map
```
app/
  app.py
  settings.py
  assets/
    icons/ (app/, client/)
    qss/
    themes/
    cache/
  pages/
    base_page.py
    home_page.py
    notificacoes.py
    registry.py
    settings.py
    subpages/
      guia_rapido_page.py
    theme_editor.py
ui/
  core/
    app.py
    app_controller.py
    command_bus.py
    frameless_window.py
    interface_ports.py
    main.py
    router.py
    settings.py
    theme_service.py
    toast_manager.py
    utils/ (factories.py, guard.py, paths.py)
  dialogs/ (quick_open.py)
  services/ (qss_renderer.py, task_runner_adapter.py, theme_repository_json.py)
  splash/ (splash.py)
  widgets/ (async_button.py, buttons.py, loading_overlay.py,
            overlay_sidebar.py, push_sidebar.py, settings_sidebar.py,
            titlebar.py, toast.py, topbar.py)
requirements.txt
license
README.md
```

---

## Install & Setup

Create and activate a virtual environment, then install dependencies:

```
python -m venv .venv
# Windows
. .venv/Scripts/activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

---

## Run & Shortcuts

Run
```
python -m ui.core.main
# Alternatives
python -m app.app
python ui/core/main.py
```
Settings (`app/settings.py`)
```
APP_TITLE = "My App"
DEFAULT_THEME = "Aku"
FIRST_PAGE = "home"
```
Keyboard shortcuts
- Alt+Left / Alt+Right: Router history (back/forward)
- Ctrl+K: Quick Open
- Ctrl+M: minimize with animation
- Ctrl+Enter: maximize/restore

---

## Pages & Routing

Manifest (`app/assets/pages_manifest.json`)
```
[
  { "route": "home", "label": "Home", "sidebar": true, "order": 0,
    "factory": "app.pages.home_page:build" }
]
```
Auto-discovery (`app/pages`)
Any module exporting `PAGE` and `build(...)` is detected. Example:
```
PAGE = { "route": "reports", "label": "Reports", "sidebar": True, "order": 10 }
def build(task_runner=None, theme_service=None) -> QWidget:
    ...
```
Dependency injection
- `task_runner`: runs business tasks (I/O, network, etc.)
- `theme_service`: reacts to theme changes and provides tokens
Router features
- `router.go(path, params={})` navigates to a route (supports `/`).
- Signal `routeChanged(path, params)` for persistence/breadcrumb/logging.
- History: `go_back()` / `go_forward()` (Alt+Left/Alt+Right).
- Per-page hook: `on_route(self, params: dict)`.

---

## Themes (QSS + JSON)
Structure
- Base QSS: `app/assets/qss/base.qss`
- JSON variables: `app/assets/themes/*.json`
Example
```
{
  "vars": { "bg": "#1a1a1a", "text": "#ffffff", "accent": "#4285f4" }
}
```
ThemeService
- Animates theme switching (with or without animation).
- Watches `base.qss` and the themes folder (hot reload).
- Emits `themeApplied`, `themesChanged`, `themeTokensChanged`.
- Persists the theme in `app/assets/cache/_ui_exec_settings.json`.
Editor & panel
- Panel (gear icon in the TitleBar) to select/create/edit/delete themes.
- Persistence via `JsonThemeRepository` (atomic writes).
- App icon syncs with the active theme.
QSS placeholders (`qss_renderer`)
- `{{token}}`, `{token}`, `${token}` with defaults and useful derived tokens (e.g. `content_bg`).

---

## Toasts & Notifications
APIs
- `show_toast(parent, text, kind="info", timeout_ms=2400, persist=False)`
- `show_action_toast(parent, title, text, kind="info", actions=[...], sticky=False, timeout_ms=3200, persist=False)`
- `ProgressToast.start(parent, text, kind="info", cancellable=True)` (with `update(...)`/`finish(...)`)
- `notification_bus()` integrates with the Center
Notification Center (right push)
- Open/close from the TopBar (bell) and show persisted entries.
- Dismissed toasts can become Center entries (title/text/flags/actions).
- Resizable width via a grip; unread badge in the TopBar.
Example
```
from ui.widgets.toast import (
  show_toast, show_action_toast, ProgressToast, notification_bus
)
show_toast(parent, text="Action completed!", kind="info")
show_action_toast(
  parent,
  title="Export",
  text="File generated successfully.",
  kind="ok",
  actions=[{"label": "Open folder", "command": "open_folder", "payload": {"path": "..."}}],
  persist=True,
)
pt = ProgressToast.start(parent, "Loading data...", kind="info", cancellable=True)
pt.update(5, 10)
pt.finish(True, "Process finished!")
```

---

## CLI
Tools to generate pages, create examples, update the manifest and clean the project. They operate under `app/pages` and keep `app/assets/pages_manifest.json` in sync.

### new page
- What it does: creates a standard page with `PAGE`, `build()`, `on_route()` and a ready-to-use `QScrollArea` for long content.
- Quick usage (bash):
```bash
# 1) Create a "Reports" page with configured route and label
python -m ui.cli new page "Reports" \
  --route reports \
  --label "Reports" \
  --order 10 \
  --sidebar
# 2) (Optional) Overwrite file if it already exists
python -m ui.cli new page "Reports" --route reports --force
```
- Result: file `app/pages/reports_page.py` created and entry added/updated in the manifest.

### new subpage
- What it does: creates a subpage (route `parent/child`, e.g. `home/details`). Useful for internal sections.
- Usage (bash):
```bash
# Create a "Details" subpage under parent route "home"
python -m ui.cli new subpage "Details" \
  --parent home \
  --route details \
  --label "Details" \
  --order 11 \
  --sidebar
```
- Result: file `app/pages/home_details_page.py` (normalized name) and updated manifest.

### examples
- What it does: generates `examples_widgets_page.py` with practical usages (buttons, AsyncTaskButton, toasts) for reference.
- Usage (bash):
```bash
python -m ui.cli examples
```
- Result: adds route `examples` to the manifest for quick navigation.

### manifest-update
- What it does: rewrites `app/assets/pages_manifest.json` based on auto-discovery of `app.pages.*` (reads `PAGE` and `build()`).
- Usage (bash):
```bash
python -m ui.cli manifest-update
```
- Tip: run after moving/renaming modules manually to sync the manifest.

### clean-pages
- What it does: removes sample pages and recreates a minimal Home (route `home`).
- Usage (bash):
```bash
# Cleanup and create the minimal Home
python -m ui.cli clean-pages
# (Optional) Rebuild manifest via auto-discovery right after cleanup
python -m ui.cli clean-pages --rebuild-manifest
```
- Result: lean project to start from; only Home remains.

---

## Widgets: Cookbook

Buttons (Controls.Button / PrimaryButton)
```
from ui.widgets.buttons import Controls
btn = Controls.Button("Primary", size_preset="md")
btn.setProperty("variant", "primary")  # others: "chip", "ghost" (via QSS)
btn.clicked.connect(lambda: print("clicked"))
```
Sizes and variants
- `size_preset`: `sm`, `md`, `lg`, `xl`, `char` (single character)
- `variant` (QSS): `primary`, `chip`, `ghost` (and others defined by your QSS)

Command button (TaskRunner)
```
from ui.widgets.buttons import command_button
btn = command_button(
  text="Sync",
  command_name="sync",
  task_runner=my_runner,
  payload={"force": True},
  disable_while_running=True,
  lock_after_click=False,
  size_preset="md"
)
```

Confirm + command
```
from ui.widgets.buttons import confirm_command_button
btn = confirm_command_button(
  text="Delete",
  confirm_msg="Are you sure?",
  command_name="delete_item",
  task_runner=my_runner,
  payload={"id": 123},
  size_preset="sm"
)
```

Route navigation (`route_button`)
```
from ui.widgets.buttons import route_button
go = lambda: self.window().router.go("home/details")
btn = route_button("Go", go, size_preset="sm")
```

Toggle / CheckBox / TextInput / Select
```
t = Controls.Toggle(); t.setChecked(True)
ck = Controls.CheckBox("I agree")
inp = Controls.TextInput("Type here...")
sel = Controls.InputList(); sel.addItems(["A", "B", "C"]) 
```

Icon / LinkLabel
```
icon = Controls.IconButton("?", tooltip="More")
link = Controls.LinkLabel("Open docs"); link.clicked.connect(lambda: print("open"))
```

Help popover (hover)
```
from ui.widgets.buttons import attach_popover
attach_popover(icon, "Action X", "Executes action X", "Ctrl+X")
```

Expand/collapse panel (ExpandMore)
```
from ui.widgets.buttons import Controls
panel = QFrame(); panel.setLayout(QVBoxLayout()); panel.layout().addWidget(QLabel("Details"))
exp = Controls.ExpandMore(panel, text_collapsed="Show more", text_expanded="Show less")
layout.addWidget(exp)
```

Slider in progress mode (non-interactive)
```
s = Controls.Slider(); s.setRange(0,100); s.setValue(42); s.setMode("progress")
```

Custom scroll
```
scroll = Controls.ScrollArea(); scroll.setWidget(wrap)
```

AsyncTaskButton (async tasks)
```
from ui.widgets.async_button import AsyncTaskButton
ab = AsyncTaskButton(
  "Run",
  task_runner=my_runner,
  command_name="process",
  payload={"limit": 10},
  block_input=True,      # optionally block with overlay
  use_overlay=True,
  overlay_message="Processing...",
  progress_text="Processing.", progress_kind="info", progress_cancellable=False,
)
ab.succeeded.connect(lambda *_: print("ok"))
ab.failed.connect(lambda *_: print("failed"))
layout.addWidget(ab)
```

Toasts (simple, action and progress)
```
from ui.widgets.toast import show_toast, show_action_toast, ProgressToast
show_toast(self, "Saved successfully", kind="ok")
show_action_toast(
  self, "Export", "File ready.", kind="ok",
  actions=[{"label":"Open folder","command":"open_folder","payload":{}}], persist=True
)
pt = ProgressToast.start(self, "Syncing.", kind="info", cancellable=True)
pt.set_indeterminate(True)
pt.update(3, 10)
pt.finish(True, "Done")
```

LoadingOverlay (manual)
```
from ui.widgets.loading_overlay import LoadingOverlay
ov = LoadingOverlay(self, message="Loading...", block_input=True)
ov.show(); ...; ov.hide()
```

Quick Open (programmatic)
```
from ui.dialogs.quick_open import QuickOpenDialog
dlg = QuickOpenDialog(self.window().router._pages.keys(), parent=self)
dlg.exec()
```

---

## Visual Customization & Chrome
- TitleBar: the app icon changes with the theme; icons live in `app/assets/icons/app/`.
- TopBar: breadcrumb and bell are integrated; badge reflects the Notification Center.
- Sidebars: `OverlaySidePanel` (navigation) and `SettingsSidePanel` (settings) stylable via QSS.
- PushSidePanel (right): Notification Center panel with resizable width via grip.

---

## Notification Center (Advanced)
Interact with the bus to create/update/remove entries:
```
from ui.widgets.toast import notification_bus
bus = notification_bus()
bus.addEntry.emit({
  "id": "abc123", "type": "info", "title": "Process started",
  "text": "Please wait.", "persist": True, "expires_on_finish": True
})
bus.updateEntry.emit({"id": "abc123", "text": "50%"})
bus.finishEntry.emit("abc123")
bus.removeEntry.emit("abc123")
```

---

## Themes: Tips & Advanced
- Add variables in `*.json` under the `vars` key and reference them in `base.qss` using `{{token}}`, `{token}` or `${token}`.
- Derived tokens (e.g. `content_bg`) are generated automatically.
- ThemeService watches `base.qss` and themes; changes are applied live.
- Use the Theme Editor (panel) to edit and save safely (atomic writes).

Example of token usage in QSS
```
QPushButton[variant="chip"] {
  background: {{surface}}; color: {{text}}; border: 1px solid {{box_border}};
}
```

---

## Troubleshooting
- Page does not appear
  - Ensure the module lives under `app/pages` and exports `PAGE` and `build()`.
  - Check `pages_manifest.json` or run `python -m ui.cli manifest-update`.
- QSS not applied
  - Check `app/assets/qss/base.qss`. ThemeService emits signals on changes; follow logs.
- Toasts not showing
  - Ensure the app runs with the default AppShell; toasts rely on the frameless shell.

---

## Best Practices
- Centralize styles in `base.qss`; avoid direct `setStyleSheet`.
- Separate UI from business logic (via `task_runner`).
- Standardize routes (kebab-case) and clear labels.
- Use `theme_service` for colors/tokens and reactive visuals.
- Keep the folder structure tidy to aid autoload/discovery.

---

## Roadmap
- Enhanced subpages and navigation history.
- Persistent/filterable Notification Center.
- Integrable event logger.
- Global search and additional shortcuts.
- Lightweight state manager (Qt Signals).
- Packaging (PyInstaller/Briefcase).

---

## Page Blueprint (recommended)
Use this skeleton as a base for new pages to maintain visual and technical consistency.
```python
from __future__ import annotations
from PySide6.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QFrame, QLabel
# Route metadata (sidebar, order and label)
PAGE = {
    "route": "my-page",
    "label": "My Page",
    "sidebar": True,
    "order": 50,
}
class MyPage(QWidget):
    def __init__(self, task_runner=None, theme_service=None):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(12)
        # Scroll area for long content
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        # Real content container
        wrap = QFrame()
        w = QVBoxLayout(wrap)
        w.setContentsMargins(0, 0, 0, 0)
        w.setSpacing(10)
        # Initial content
        w.addWidget(QLabel("Hello, world!"))
        w.addStretch(1)
        scroll.setWidget(wrap)
        root.addWidget(scroll, 1)
    # Lifecycle hook: called when the route is activated
    def on_route(self, params: dict | None = None):
        # Update content/state based on params if needed
        pass
def build(task_runner=None, theme_service=None) -> QWidget:
    return MyPage(task_runner=task_runner, theme_service=theme_service)
```

Best practices for pages
- Use `QScrollArea` as the default container to keep UX consistent.
- Centralize styles in `base.qss`; avoid in-widget `setStyleSheet` where possible.
- Use `on_route(params)` to react to navigation instead of putting logic in `__init__`.
- Prefer kebab-case route names (e.g. `annual-reports`).

---

## Code Quality (Linting & Style)

Suggested tools
- Ruff (lint & fix): `pip install ruff`  ·  `ruff check .`  ·  `ruff check . --fix`
- Black (format): `pip install black`  ·  `black .`
- isort (imports): `pip install isort`  ·  `isort .`
- mypy (optional typing): `pip install mypy`  ·  `mypy ui app`

Style tips
- Typing: annotate public functions and attributes; use `Optional[...]` or `| None` where appropriate.
- Names: routes in kebab-case; modules/files snake_case; classes PascalCase; variables/functions snake_case.
- Signals/slots: prefer descriptive names (`openNotificationsRequested`, `setUnreadCountRequested`).
- Pages: expose `PAGE` + `build(...)`; use `on_route(params)` for lifecycle.
- QSS: declare variants with `setProperty("variant", ...)` and sizes with `setProperty("size", ...)`.
- Imports: group stdlib/third-party/local; keep alphabetical order (use `isort`).

About the file `pyproject.toml`
- What: a single configuration file (at the repo root) centralizing rules for Black, Ruff, isort and mypy.
- Where: `pyproject.toml` at the root of this repository.
- Why: standardizes style and quality for the whole team, reduces noise in PRs and makes commands predictable.
- How: each tool reads its options directly from `pyproject.toml`, so you don’t need long flags.

Day-to-day commands (read from pyproject.toml):
```
# Lint (check only)
ruff check .
# Lint with autofixes
ruff check . --fix
# Format code (opinionated)
black .
# Organize imports
isort .
# Type-check (optional, gradual)
mypy ui app
```

Suggested flow
- Getting started: run `ruff check . --fix` and then `black .`; if imports need ordering, run `isort .`.
- Power users: configure a pre-commit with `ruff`, `black` and `isort` or add these steps to your CI.
