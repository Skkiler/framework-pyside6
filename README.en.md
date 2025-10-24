<p align="center">
  <img src="app/assets/icons/app/app.ico" width="96" alt="App Icon" />
</p>

<p align="center">
  <a href="README.md">Ler em Português</a>
</p>

# UI Exec Framework (PySide6)

Modern base for desktop apps with Python + PySide6. Includes a frameless window, hierarchical routing, themed QSS + JSON with smooth transitions, toasts and a Notification Center, plus a productivity‑focused CLI.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Install & Setup](#install--setup)
- [Run & Shortcuts](#run--shortcuts)
- [Pages & Routing](#pages--routing)
  - [Manifest](#manifest-appassetspages_manifestjson)
  - [Auto‑discovery](#auto-discovery-apppages)
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
- [Widgets Cookbook](#widgets-cookbook)
  - [Buttons](#buttons)
  - [Command Buttons](#command-buttons)
  - [Confirm + Command](#confirm--command)
  - [Route Navigation](#route-navigation)
  - [Basic Controls](#basic-controls)
  - [Icon & LinkLabel](#icon--linklabel)
  - [Help Popover](#help-popover)
  - [Expand/Collapse Panel](#expandcollapse-panel)
  - [Progress Slider](#progress-slider)
  - [Custom Scroll](#custom-scroll)
  - [AsyncTaskButton](#asynctaskbutton)
  - [Toasts](#toasts)
  - [LoadingOverlay](#loadingoverlay)
  - [Quick Open](#quick-open)
- [Visual Customization](#visual-customization)
- [Notification Center (Advanced)](#notification-center-advanced)
- [Themes: Tips & Advanced](#themes-tips--advanced)
- [Troubleshooting](#troubleshooting)
- [Code Quality (Linting & Style)](#code-quality-linting--style)
- [Page Blueprint](#page-blueprint)
- [Roadmap](#roadmap)

---

## Overview

Highlights

- Frameless window with drop shadow and rounded corners.
- Pages with routing via auto‑discovery and/or manifest.
- Dynamic Themes via QSS + JSON with smooth transitions.
- Quick Open (Ctrl+K) to navigate routes fast.
- TopBar with clickable breadcrumb and notifications badge.
- Right push Notification Center integrated with toasts.
- Simple, actionable and progress toasts.
- Persisted theme and last route in JSON cache.
- CLI for scaffolding, examples, cleanup and manifest updates.
- DI for `task_runner` and `theme_service` in pages.

---

## Architecture

```
app/
  app.py, settings.py
  assets/ (icons/, qss/, themes/, cache/)
  pages/ (base_page.py, home_page.py, notificacoes.py, registry.py, settings.py,
          subpages/guia_rapido_page.py, theme_editor.py)

ui/
  core/ (app.py, app_controller.py, command_bus.py, frameless_window.py,
         interface_ports.py, main.py, router.py, settings.py, theme_service.py,
         toast_manager.py, utils/)
  dialogs/ (quick_open.py)
  services/ (qss_renderer.py, task_runner_adapter.py, theme_repository_json.py)
  splash/ (splash.py)
  widgets/ (async_button.py, buttons.py, loading_overlay.py, overlay_sidebar.py,
            push_sidebar.py, settings_sidebar.py, titlebar.py, toast.py, topbar.py)
```

---

## Install & Setup

```
python -m venv .venv
. .venv/Scripts/activate   # Windows
# or
source .venv/bin/activate  # macOS/Linux

pip install -r requirements.txt
```

---

## Run & Shortcuts

```
python -m ui.core.main
```

Shortcuts

- Alt+Left / Alt+Right: router back/forward
- Ctrl+K: Quick Open
- Ctrl+M: minimize with animation
- Ctrl+Enter: maximize/restore

---

## Pages & Routing

Manifest (app/assets/pages_manifest.json)

```
[
  { "route": "home", "label": "Home", "sidebar": true, "order": 0,
    "factory": "app.pages.home_page:build" }
]
```

Auto‑discovery (app/pages)

Modules exposing `PAGE` and `build(...)` are auto‑detected.

Dependency Injection

- `task_runner`: run business actions
- `theme_service`: theme tokens and reactive behavior

Router Features

- `router.go(path, params={})`, `go_back()`, `go_forward()`
- `routeChanged(path, params)` signal
- page hook: `on_route(self, params)`

---

## Themes (QSS + JSON)

Structure & Example

```
{
  "vars": { "bg": "#1a1a1a", "text": "#ffffff", "accent": "#4285f4" }
}
```

ThemeService

- Smooth transitions, watches `base.qss` and `themes/` folder, emits `themeApplied`, `themesChanged`, `themeTokensChanged`.

Editor & Panel

- Use the gear icon (TitleBar) to select/create/edit/delete themes. Atomic JSON writes.

QSS Placeholders (qss_renderer)

- `{{token}}`, `{token}`, `${token}` with defaults and derived tokens (e.g. `content_bg`).

---

## Toasts & Notifications

APIs

- `show_toast(parent, text, kind="info", timeout_ms=2400, persist=False)`
- `show_action_toast(parent, title, text, kind="info", actions=[...], sticky=False, timeout_ms=3200, persist=False)`
- `ProgressToast.start(parent, text, kind="info", cancellable=True)`

Notification Center (right push panel)

- Opens from TopBar, shows persisted entries, integrates with toasts via `notification_bus()`.

Example

```python
from ui.widgets.toast import show_toast, show_action_toast, ProgressToast

show_toast(self, "Saved successfully", kind="ok")

show_action_toast(
  self, "Export", "File ready.", kind="ok",
  actions=[{"label":"Open folder","command":"open_folder","payload":{}}],
  persist=True
)

pt = ProgressToast.start(self, "Syncing…", kind="info", cancellable=True)
pt.set_indeterminate(True)
pt.update(3, 10)
pt.finish(True, "Done")
```

---

## CLI

All commands operate on `app/pages` and keep `app/assets/pages_manifest.json` in sync.

### new page

```bash
python -m ui.cli new page "Reports" \
  --route reports \
  --label "Reports" \
  --order 10 \
  --sidebar
```

Creates `app/pages/reports_page.py` with PAGE, build(), on_route(), QScrollArea and upserts the manifest entry.

### new subpage

```bash
python -m ui.cli new subpage "Details" --parent home --route details --label "Details" --order 11 --sidebar
```

Creates `app/pages/home_details_page.py` and updates the manifest.

### examples

```bash
python -m ui.cli examples
```

Generates `examples_widgets_page.py` demonstrating buttons, AsyncTaskButton and toasts; adds route `examples`.

### manifest-update

```bash
python -m ui.cli manifest-update
```

Rewrites the manifest based on auto‑discovery of `app.pages.*`.

### clean-pages

```bash
python -m ui.cli clean-pages [--rebuild-manifest]
```

Removes demo pages and creates a minimal home; optionally rebuilds the manifest from discovery.

---

## Widgets Cookbook

```python
from ui.widgets.buttons import Controls

# primary button with QSS variant
btn = Controls.Button("Primary", size_preset="md")
btn.setProperty("variant", "primary")
btn.clicked.connect(lambda: print("clicked"))
```

See the Portuguese README for an extensive, commented cookbook covering command buttons, toggles, inputs, icon/link labels, popovers, expanders, progress slider, custom scroll, AsyncTaskButton, toasts, LoadingOverlay and Quick Open.

---

## Visual Customization

- TitleBar icon syncs with the active theme (icons in `app/assets/icons/app/`).
- TopBar includes breadcrumb and notifications bell.
- OverlaySidePanel / SettingsSidePanel are styled via QSS.
- Right PushSidePanel hosts the Notification Center and is resizable.

---

## Code Quality (Linting & Style)

- Ruff: `ruff check .` / `ruff check . --fix`
- Black: `black .`
- isort: `isort .`
- mypy: `mypy ui app`

Guidelines

- Type annotations for public APIs; prefer Optional/Union (or `| None`).
- Routing in kebab‑case; modules snake_case; classes PascalCase; functions snake_case.
- Expose `PAGE` + `build(...)` and implement `on_route(params)` in pages.
- Use QSS properties for variants/sizes: `setProperty("variant", …)`, `setProperty("size", …)`.

---

## Page Blueprint

```python
from PySide6.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QFrame, QLabel

PAGE = {"route":"my-page","label":"My Page","sidebar":True,"order":50}

class MyPage(QWidget):
    def __init__(self, task_runner=None, theme_service=None):
        super().__init__()
        root = QVBoxLayout(self); root.setContentsMargins(14,14,14,14); root.setSpacing(12)
        scroll = QScrollArea(self); scroll.setWidgetResizable(True)
        wrap = QFrame(); w = QVBoxLayout(wrap); w.setContentsMargins(0,0,0,0); w.setSpacing(10)
        w.addWidget(QLabel("Hello!")); w.addStretch(1)
        scroll.setWidget(wrap); root.addWidget(scroll, 1)

    def on_route(self, params: dict | None = None):
        pass

def build(task_runner=None, theme_service=None) -> QWidget:
    return MyPage(task_runner=task_runner, theme_service=theme_service)
```

---

## Troubleshooting

- Page doesn’t show
  - Ensure it lives under `app/pages` and exports `PAGE` + `build()`; run `manifest-update` if using a manifest.
- QSS not applied
  - Check `app/assets/qss/base.qss`; ThemeService emits signals upon changes.
- Toasts invisible
  - Make sure the app uses the default AppShell (toasts rely on the frameless window).

---

## Roadmap

- Enhanced subpages and navigation history
- Persistent/filterable notification center
- Integratable event logger
- Global search and shortcuts
- Lightweight state manager (Qt Signals)
- Packaging (PyInstaller/Briefcase)

