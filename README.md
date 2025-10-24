# UI Exec Framework (PySide6)

Framework modular para criação de interfaces desktop em Python + PySide6, com janela frameless, roteamento, temas (QSS + JSON), toasts, centro de notificações, CLI e arquitetura extensível.

---

## Sumário
- [Visão Geral](#visão-geral)
- [Arquitetura](#arquitetura)
- [Execução e Atalhos](#execução-e-atalhos)
- [Páginas e Roteamento](#páginas-e-roteamento)
- [Temas (QSS + JSON)](#temas-qss--json)
- [Toasts e Notificações](#toasts-e-notificações)
- [CLI](#cli)
- [Widgets Inclusos](#widgets-inclusos)
- [Tutoriais Rápidos](#tutoriais-rápidos)
- [Boas Práticas](#boas-práticas)
- [Roadmap](#roadmap)

---

## Visão Geral

Principais recursos:

- Janela frameless com sombra e cantos arredondados.
- Roteamento de páginas com auto‑descoberta e manifesto.
- Sistema de temas dinâmico via QSS + JSON, com animação suave entre temas.
- Quick Open (Ctrl+K) para navegar por rotas rapidamente.
- Breadcrumb clicável na TopBar + badge de notificações.
- Centro de Notificações em painel lateral (push) integrado aos toasts.
- Toasts simples, com ações e com progresso, integrados ao Centro.
- Configurações persistentes (tema e última rota) em cache JSON.
- CLI para scaffolding de páginas.
- Injeção de dependências (task_runner, theme_service) em páginas.

Novidades (resumo):

- Router v2 com rotas hierárquicas (ex.: `home/ferramentas/detalhes`), histórico (Alt+Left/Alt+Right), sinal `routeChanged` e hook `on_route(params)` por página.
- Quick Open (Ctrl+K) via `ui/dialogs/quick_open.py`.
- Centro de Notificações (push à direita) integrado ao `notification_bus()`.
- ThemeService com watcher de `base.qss` e de temas, tokens derivados e dump do QSS aplicado.
- Título/ícone: TitleBar com ícone animado (cross‑fade) e sincronização do ícone do app com o tema.
- TaskRunnerAdapter aceita `async def run_task(...)`.

---

## Arquitetura

Estrutura de diretórios (principal):

```
app/
  app.py
  settings.py
  assets/
    icons/
      app/
      client/
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
    utils/
      factories.py
      guard.py
      paths.py
  dialogs/
    quick_open.py
  services/
    qss_renderer.py
    task_runner_adapter.py
    theme_repository_json.py
  splash/
    splash.py
  widgets/
    async_button.py
    buttons.py
    loading_overlay.py
    overlay_sidebar.py
    push_sidebar.py
    settings_sidebar.py
    titlebar.py
    toast.py
    topbar.py

requirements.txt
license
README.md
```

Componentes de destaque:

- Router: rotas hierárquicas, histórico (back/forward), `routeChanged`, hook `on_route(params)` em cada página.
- ThemeService: anima temas, observa `base.qss`/temas, emite `themeApplied`, `themesChanged`, `themeTokensChanged`.
- AppShell: TitleBar (ícone animado + engrenagem), TopBar (breadcrumb + sino), Sidebar, Centro de Notificações (push) e Router.
- Toasts: simples, com ações e com progresso; integrados ao Centro via `notification_bus()`.
- Settings persistentes: JSON em `app/assets/cache/_ui_exec_settings.json` (tema, última rota, etc.).

---

## Execução e Atalhos

Executar o aplicativo:

```
python -m ui.core.main
# Alternativas:
python -m app.app
python ui/core/main.py
```

Configurações em `app/settings.py`:

```
APP_TITLE = "Meu App"
DEFAULT_THEME = "Aku"
FIRST_PAGE = "home"
```

Atalhos de teclado:

- Alt+Left / Alt+Right: voltar/avançar no histórico do Router.
- Ctrl+K: abrir Quick Open (busca/abre rotas).
- Ctrl+M: minimizar com animação.
- Ctrl+Enter: maximizar/restaurar.

---

## Páginas e Roteamento

Formas de registrar páginas:

1) Manifesto JSON (`app/assets/pages_manifest.json`)

Exemplo:

```
[
  {
    "route": "home",
    "label": "Início",
    "sidebar": true,
    "order": 0,
    "factory": "app.pages.home_page:build"
  },
  {
    "route": "home/guia",
    "label": "Guia Rápido",
    "sidebar": true,
    "order": 5,
    "factory": "app.pages.subpages.guia_rapido_page:build"
  }
]
```

2) Auto‑descoberta (`app/pages`)

Qualquer módulo com `PAGE` e `build(...)` é detectado; exemplos de metadados aceitos:

```
PAGE = {
  "route": "relatorios",
  "label": "Relatórios",
  "sidebar": True,
  "order": 10
}

def build(task_runner=None, theme_service=None) -> QWidget:
    ...
```

Injeção de dependências na `build(...)`:

- `task_runner`: executa tarefas de negócio (I/O, rede, etc.).
- `theme_service`: reage a trocas de tema e fornece tokens.

Recursos do Router:

- `router.go(path, params={})` navega para uma rota (suporta caminhos com `/`).
- Sinal `routeChanged(path, params)` para persistência/breadcrumb/log.
- Histórico: `go_back()` / `go_forward()` (atalhos Alt+Left/Alt+Right).
- Hook por página: defina `on_route(self, params: dict)` no widget da página para reagir a ativações.

---

## Temas (QSS + JSON)

Cada tema é composto por:

- QSS base: `app/assets/qss/base.qss`
- JSON de variáveis: `app/assets/themes/*.json`

Exemplo de tema:

```
{
  "vars": {
    "bg": "#1a1a1a",
    "text": "#ffffff",
    "accent": "#4285f4"
  }
}
```

ThemeService:

- Anima troca de tema (interpolação de cores), com opção de aplicar sem animação.
- Observa `base.qss` e a pasta de temas; altera em tempo real (hot‑reload).
- Emite `themeApplied(name)`, `themesChanged(list)`, `themeTokensChanged(dict)`.
- Persiste tema selecionado em `app/assets/cache/_ui_exec_settings.json`.

Editor de temas e painel de configurações:

- Abra o painel (ícone de engrenagem na TitleBar) para selecionar/editar/criar/excluir temas.
- Persistência via `JsonThemeRepository` (gravação atômica de JSONs).
- O ícone da janela segue o tema ativo e atualiza automaticamente.

Placeholders no QSS base suportados por `qss_renderer`:

- `{{token}}`, `{token}`, `${token}` com defaults e derivados úteis (ex.: `content_bg`).

---

## Toasts e Notificações

APIs principais em `ui/widgets/toast.py`:

- `show_toast(parent, text, kind="info", timeout_ms=2400, persist=False)`
- `show_action_toast(parent, title, text, kind="info", actions=[...], sticky=False, timeout_ms=3200, persist=False)`
- `ProgressToast.start(parent, text, kind="info", cancellable=True)` com `update(...)`/`finish(...)`
- `notification_bus()` para integração com o Centro de Notificações.

Centro de Notificações (painel push à direita):

- Abre/fecha pela TopBar (sino) e exibe entradas persistidas.
- Toasts enviados/ocultados podem virar entradas do Centro (com portabilidade de título/texto/flags/ações).
- Largura redimensionável por “grip”, badge de não lidas na TopBar.

Exemplos:

```
from ui.widgets.toast import (
  show_toast, show_action_toast, ProgressToast, notification_bus
)

# Toast simples
show_toast(parent, text="Ação concluída!", kind="info")

# Toast com ações rápidas (aparece na Central ao dispensar)
t = show_action_toast(
  parent,
  title="Exportação",
  text="Arquivo gerado com sucesso.",
  kind="ok",
  actions=[{"label": "Abrir pasta", "command": "abrir_pasta", "payload": {"path": "..."}}],
  persist=True,
)

# Progresso
pt = ProgressToast.start(parent, "Carregando dados...", kind="info", cancellable=True)
pt.update(5, 10)
pt.finish(True, "Processo finalizado!")
```

---

## CLI

Geração de páginas via `ui/cli.py`:

```
python -m ui.cli new page "Relatorios" --route relatorios
```

- Cria `ui/pages/relatorios_page.py` com `PAGE` e `build()` preenchidos.
- Observação: a auto‑descoberta padrão varre `app.pages`. Se você usa `app/pages`, mova o arquivo gerado ou registre via manifesto (`app/assets/pages_manifest.json`).

---

## Widgets Inclusos

- TitleBar: barra de título com ícone animado, botões min/max/close e engrenagem.
- TopBar: breadcrumb clicável, sino com badge e menu.
- OverlaySidePanel: menu lateral (overlay) com scrim.
- SettingsSidePanel: painel de configurações (direita).
- PushSidePanel: painel lateral direito (Centro de Notificações), redimensionável.
- LoadingOverlay: overlay de carregamento sensível ao tema (GIF).
- Toast / ActionToast / ProgressToast: notificações flutuantes integradas ao Centro.
- AsyncButton: execução assíncrona com feedback visual.
- QuickOpenDialog: busca/abre rotas (Ctrl+K).

---

## Tutoriais Rápidos

Criar página

```
python -m ui.cli new page "Financeiro" --route financeiro
```

A `build(task_runner=None, theme_service=None)` recebe dependências úteis já injetadas.

Criar tema

1. Duplique um tema existente (`app/assets/themes/Dark.json`).
2. Renomeie (ex.: `MyTheme.json`) e ajuste cores.
3. Selecione no painel de configurações (engrenagem na TitleBar).

Integrar TaskRunner personalizado

```
from ui.services.task_runner_adapter import TaskRunnerAdapter

class MyRunner:
  def run_task(self, name, payload):
    if name == "calcular_relatorio":
      return {"ok": True, "data": "Relatório gerado"}
    return {"ok": False, "error": "Ação inválida"}

controller = AppController(task_runner=TaskRunnerAdapter(MyRunner()))
```

---

## Boas Práticas

- Centralize estilos no `base.qss`; evite `setStyleSheet` direto.
- Separe UI de lógica de negócio (via `task_runner`).
- Padronize rotas (kebab‑case) e labels claros.
- Use `theme_service` para cores/tokens e reatividade visual.
- Mantenha a estrutura de pastas limpa para facilitar autoload.

---

## Roadmap

- Subpáginas e histórico de navegação aprimorados.
- Centro de notificações persistente/filtrável.
- Logger de eventos integrável.
- Pesquisa global e atalhos adicionais.
- Gerenciador de estado leve (Qt Signals).
- Empacotamento (PyInstaller/Briefcase).

