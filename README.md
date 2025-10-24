<p align="center">
  <img src="app/assets/icons/app/app.ico" width="96" alt="App Icon" />
</p>

<p align="center">
  <a href="README.en.md">Read this in English</a>
</p>

# UI Exec Framework (PySide6)

Base moderna para aplicativos desktop com Python + PySide6. Inclui janela frameless, roteamento hierárquico, sistema de temas (QSS + JSON) com animação, toasts e Centro de Notificações, além de um CLI para produtividade.

---

## Sumário

- [Visão Geral](#visão-geral)
- [Arquitetura](#arquitetura)
- [Instalação e Setup](#instalação-e-setup)
- [Execução e Atalhos](#execução-e-atalhos)
- [Páginas e Roteamento](#páginas-e-roteamento)
  - [Manifesto](#manifesto-appassetspages_manifestjson)
  - [Auto‑descoberta](#auto‑descoberta-apppages)
  - [Injeção de dependências](#injeção-de-dependências)
  - [Recursos do Router](#recursos-do-router)
- [Temas (QSS + JSON)](#temas-qss--json)
  - [Estrutura e Exemplo](#estrutura-e-exemplo)
  - [ThemeService](#themeservice)
  - [Editor e Painel](#editor-e-painel)
  - [QSS Placeholders](#qss-placeholders-qss_renderer)
- [Toasts e Notificações](#toasts-e-notificações)
  - [APIs](#apis)
  - [Centro de Notificações](#centro-de-notificações-push-à-direita)
  - [Exemplo](#exemplo)
- [CLI](#cli)
  - [new page](#new-page)
  - [new subpage](#new-subpage)
  - [examples](#examples)
  - [manifest-update](#manifest-update)
  - [clean-pages](#clean-pages)
- [Criação Manual de Páginas](#criando-páginas-manualmente-sem-cli)
- [Criação Manual de Subpáginas](#subpáginas-manualmente-sem-cli)
- [Widgets: Guia Prático](#widgets-guia-prático-cookbook)
  - [Buttons](#buttons-controlssbutton--primarybutton)
  - [Command Buttons](#botão-de-comando-taskrunner)
  - [Confirmação + Comando](#confirmação--comando)
  - [Navegação por Rota](#navegar-por-rota-route_button)
  - [Controles Básicos](#toggle--checkbox--textinput--select)
  - [Ícone e Link](#ícone--linklabel)
  - [Popover de Ajuda](#popover-de-ajuda-hover)
  - [ExpandirPainel](#expandircolapsar-painel-expandmore)
  - [Slider Progresso](#slider-em-modo-progresso-não-interativo)
  - [Scroll Customizado](#scroll-customizado)
  - [AsyncTaskButton](#asynctaskbutton-tarefas-assíncronas)
  - [Toasts](#toasts-simples-ação-e-progresso)
  - [LoadingOverlay](#loadingoverlay-manual)
  - [Quick Open](#quick-open-programático)
- [Personalização Visual](#personalização-visual--chrome)
- [Centro de Notificações (Avançado)](#centro-de-notificações-avançado)
- [Temas: Dicas Avançadas](#temas-dicas--avançado)
- [Troubleshooting](#troubleshooting)
- [Boas Práticas](#boas-práticas)
- [Roadmap](#roadmap)

---

## Visão Geral

Principais recursos

- Janela frameless com sombra e cantos arredondados.
- Roteamento de páginas com auto‑descoberta e manifesto.
- Temas dinâmicos via QSS + JSON, com animação suave entre temas.
- Quick Open (Ctrl+K) para navegar por rotas rapidamente.
- TopBar com breadcrumb clicável e sino com badge de não lidas.
- Centro de Notificações (push à direita) integrado aos toasts.
- Toasts simples, com ações e com progresso.
- Persistência de tema e última rota em cache JSON.
- CLI para scaffolding, exemplos, limpeza e manifesto.
- Injeção de dependências (task_runner, theme_service) em páginas.

Novidades

- Router v2: rotas hierárquicas (`home/ferramentas/detalhes`), histórico (Alt+Left/Alt+Right), `routeChanged` e hook `on_route(params)` por página.
- Quick Open (Ctrl+K) via `ui/dialogs/quick_open.py`.
- Centro de Notificações com PushSidePanel e `notification_bus()`.
- ThemeService: watcher de `base.qss` e temas, tokens derivados e dump do QSS aplicado.
- TitleBar com ícone animado (cross‑fade) e sincronização com o tema.
- TaskRunnerAdapter aceita `async def run_task(...)`.

---

## Arquitetura

Mapa de diretórios

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

Componentes de destaque

- Router: rotas hierárquicas, histórico, `routeChanged`, hook `on_route(params)`.
- ThemeService: anima temas, observa `base.qss` e temas, emite `themeApplied`, `themesChanged`, `themeTokensChanged`.
- AppShell: TitleBar (ícone animado + engrenagem), TopBar (breadcrumb + sino), Sidebar, Centro de Notificações (push) e Router.
- Toasts: simples/ações/progresso; integração com o Centro via `notification_bus()`.
- Settings: cache JSON em `app/assets/cache/_ui_exec_settings.json` (tema, última rota, etc.).

---

## Execução e Atalhos

Executar

```
python -m ui.core.main
# Alternativas
python -m app.app
python ui/core/main.py
```

Configurações (app/settings.py)

```
APP_TITLE = "Meu App"
DEFAULT_THEME = "Aku"
FIRST_PAGE = "home"
```

Atalhos de teclado

- Alt+Left / Alt+Right: histórico do Router (voltar/avançar).
- Ctrl+K: Quick Open (busca/abre rotas).
- Ctrl+M: minimizar com animação.
- Ctrl+Enter: maximizar/restaurar.

---

## Páginas e Roteamento

Manifesto (app/assets/pages_manifest.json)

```
[
  { "route": "home", "label": "Início", "sidebar": true, "order": 0,
    "factory": "app.pages.home_page:build" }
]
```

Auto‑descoberta (app/pages)

Qualquer módulo com `PAGE` e `build(...)` é detectado. Exemplo:

```
PAGE = { "route": "relatorios", "label": "Relatórios", "sidebar": True, "order": 10 }

def build(task_runner=None, theme_service=None) -> QWidget:
    ...
```

Injeção de dependências

- `task_runner`: executa tarefas de negócio (I/O, rede, etc.).
- `theme_service`: reage a trocas de tema e fornece tokens.

Recursos do Router

- `router.go(path, params={})` navega para uma rota (com `/`).
- Sinal `routeChanged(path, params)` para persistência/breadcrumb/log.
- Histórico: `go_back()` / `go_forward()` (Alt+Left/Alt+Right).
- Hook por página: `on_route(self, params: dict)`.

---

## Temas (QSS + JSON)

Estrutura

- QSS base: `app/assets/qss/base.qss`
- JSON de variáveis: `app/assets/themes/*.json`

Exemplo

```
{
  "vars": { "bg": "#1a1a1a", "text": "#ffffff", "accent": "#4285f4" }
}
```

ThemeService

- Anima troca de tema (com ou sem animação).
- Observa `base.qss` e a pasta de temas (hot‑reload).
- Emite `themeApplied`, `themesChanged`, `themeTokensChanged`.
- Persiste tema em `app/assets/cache/_ui_exec_settings.json`.

Editor e painel

- Painel (engrenagem na TitleBar) para selecionar/criar/editar/excluir temas.
- Persistência via `JsonThemeRepository` (gravação atômica).
- Ícone do app é sincronizado com o tema ativo.

QSS placeholders (qss_renderer)

- `{{token}}`, `{token}`, `${token}` com defaults e derivados úteis (ex.: `content_bg`).

---

## Toasts e Notificações

APIs

- `show_toast(parent, text, kind="info", timeout_ms=2400, persist=False)`
- `show_action_toast(parent, title, text, kind="info", actions=[...], sticky=False, timeout_ms=3200, persist=False)`
- `ProgressToast.start(parent, text, kind="info", cancellable=True)` (com `update(...)`/`finish(...)`)
- `notification_bus()` para integração com o Centro.

Centro de Notificações (push à direita)

- Abre/fecha pela TopBar (sino) e exibe entradas persistidas.
- Toasts dispensados podem virar entradas do Centro (título/texto/flags/ações).
- Largura redimensionável por “grip”, badge de não lidas na TopBar.

Exemplo

```
from ui.widgets.toast import (
  show_toast, show_action_toast, ProgressToast, notification_bus
)

show_toast(parent, text="Ação concluída!", kind="info")

show_action_toast(
  parent,
  title="Exportação",
  text="Arquivo gerado com sucesso.",
  kind="ok",
  actions=[{"label": "Abrir pasta", "command": "abrir_pasta", "payload": {"path": "..."}}],
  persist=True,
)

pt = ProgressToast.start(parent, "Carregando dados...", kind="info", cancellable=True)
pt.update(5, 10)
pt.finish(True, "Processo finalizado!")
```

---

## CLI

Ferramentas para gerar páginas, criar exemplos, atualizar o manifesto e limpar o projeto. Operam em `app/pages` e mantêm `app/assets/pages_manifest.json` alinhado.

### new page

- O que faz: cria uma página padrão com `PAGE`, `build()`, hook `on_route()` e estrutura com `QScrollArea` pronta para conteúdos longos.

- Uso rápido (bash):

```bash
# 1) Cria página "Relatórios" com rota e label configurados
python -m ui.cli new page "Relatorios" \
  --route relatorios \
  --label "Relatórios" \
  --order 10 \
  --sidebar

# 2) (Opcional) Sobrescrever arquivo se já existir
python -m ui.cli new page "Relatorios" --route relatorios --force
```

- Resultado: arquivo `app/pages/relatorios_page.py` criado e entrada adicionada/atualizada no manifesto.

### new subpage

- O que faz: cria uma subpágina (rota `pai/filho`, ex.: `home/detalhes`). Útil para seções internas.

- Uso (bash):

```bash
# Cria uma subpágina "Detalhes" sob a rota pai "home"
python -m ui.cli new subpage "Detalhes" \
  --parent home \
  --route detalhes \
  --label "Detalhes" \
  --order 11 \
  --sidebar
```

- Resultado: arquivo `app/pages/home_detalhes_page.py` (nome normalizado) e manifesto atualizado.

### examples

- O que faz: gera `examples_widgets_page.py` com usos práticos (botões, AsyncTaskButton, toasts) para consulta.

- Uso (bash):

```bash
python -m ui.cli examples
```

- Resultado: rota `examples` adicionada ao manifesto para navegação rápida.

### manifest-update

- O que faz: reescreve `app/assets/pages_manifest.json` com base na auto‑descoberta de `app.pages.*` (lendo `PAGE` e `build()`).

- Uso (bash):

```bash
python -m ui.cli manifest-update
```

- Dica: use após mover/renomear módulos manualmente para sincronizar o manifesto.

### clean-pages

- O que faz: remove páginas de exemplo e recria uma Home mínima (rota `home`).

- Uso (bash):

```bash
# Limpeza e criação da Home mínima
python -m ui.cli clean-pages

# (Opcional) Reconstruir manifesto via auto‑descoberta logo após a limpeza
python -m ui.cli clean-pages --rebuild-manifest
```

- Resultado: projeto enxuto para começar; somente a Home permanece.

---

## Widgets Inclusos

- TitleBar: barra de título com ícone animado, botões min/max/close e engrenagem.
- TopBar: breadcrumb clicável, sino com badge e menu.
- OverlaySidePanel: menu lateral (overlay) com scrim.
- SettingsSidePanel: painel de configurações (direita).
- PushSidePanel: painel lateral (Centro de Notificações), redimensionável.
- LoadingOverlay: overlay de carregamento sensível ao tema (GIF).
- Toast / ActionToast / ProgressToast: notificações flutuantes integradas ao Centro.
- AsyncButton: execução assíncrona com feedback visual.
- QuickOpenDialog: busca/abre rotas (Ctrl+K).

---

## Tutoriais Rápidos

Criar página

```
python -m ui.cli new page "Financeiro" --route financeiro --sidebar
```

Gerada com `PAGE`, `build()` e `QScrollArea`; `build(task_runner=None, theme_service=None)` recebe dependências injetadas.

Criar tema

1. Duplique `app/assets/themes/Dark.json`.
2. Renomeie (ex.: `MyTheme.json`) e ajuste cores.
3. Selecione pelo painel de configurações (engrenagem na TitleBar).

Integrar TaskRunner

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

---

## Instalação e Setup

- Requisitos
  - Python 3.10+
  - Pip recente e ambiente virtual recomendado
  - Windows/macOS/Linux com Qt (PySide6)

- Passo a passo
  - Crie e ative um ambiente virtual
    - Windows: `python -m venv .venv && .venv\Scripts\activate`
    - macOS/Linux: `python -m venv .venv && source .venv/bin/activate`
  - Instale dependências: `pip install -r requirements.txt`
  - Rode o app: `python -m ui.core.main`

---

## CLI Detalhado (guia completo)

O CLI acelera tarefas comuns. Abaixo, as opções e impactos de cada comando.

- new page
  - Cria um arquivo em `app/pages/<rota>_page.py` com:
    - `PAGE = { route, label, sidebar, order }`
    - `build(task_runner=None, theme_service=None)`
    - Estrutura com `QScrollArea` pronta para conteúdo extenso
  - Exemplo:
    - `python -m ui.cli new page "Relatorios" --route relatorios --label Relatórios --order 10 --sidebar`
  - Manifesto: faz “upsert” de uma entrada coerente em `app/assets/pages_manifest.json`.

- new subpage
  - Gera uma subpágina com rota `pai/filho` (ex.: `home/detalhes`).
  - Exemplo:
    - `python -m ui.cli new subpage "Detalhes" --parent home --route detalhes --label Detalhes --order 11 --sidebar`
  - Arquivo: `app/pages/home_detalhes_page.py` (rota normalizada).
  - Manifesto: atualiza com a nova rota.

- examples
  - Cria `examples_widgets_page.py` com usos práticos de botões, AsyncTaskButton e toasts.
  - Exemplo: `python -m ui.cli examples`
  - Manifesto: adiciona rota `examples`.

- manifest-update
  - Reescreve completamente `app/assets/pages_manifest.json` com base na auto‑descoberta de `app.pages.*`.
  - Útil após mover/renomear páginas manualmente.
  - Exemplo: `python -m ui.cli manifest-update`

- clean-pages
  - Remove páginas pré‑programadas de exemplo e cria uma Home mínima.
  - Exemplo: `python -m ui.cli clean-pages` (ou `--rebuild-manifest` para reconstruir o manifesto via descoberta)

Observações importantes

- O nome do arquivo gerado é a rota com barras substituídas por sublinhados + `_page.py`.
- A descoberta padrão importa `app.pages.*`; mantenha páginas dentro de `app/pages`.

---

## Criando Páginas Manualmente (sem CLI)

1) Crie um arquivo em `app/pages/minha_pagina_page.py` com:

```
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea, QFrame

PAGE = { "route": "minha-pagina", "label": "Minha Página", "sidebar": True, "order": 50 }

class MinhaPaginaPage(QWidget):
    def __init__(self, task_runner=None, theme_service=None):
        super().__init__()
        root = QVBoxLayout(self); root.setContentsMargins(14,14,14,14); root.setSpacing(12)
        scroll = QScrollArea(self); scroll.setWidgetResizable(True)
        wrap = QFrame(); wrap_l = QVBoxLayout(wrap); wrap_l.setContentsMargins(0,0,0,0); wrap_l.setSpacing(10)
        wrap_l.addWidget(QLabel("Conteúdo da Minha Página")); wrap_l.addStretch(1)
        scroll.setWidget(wrap); root.addWidget(scroll, 1)

    def on_route(self, params: dict | None = None):
        # Atualize conteúdo com base em params quando a rota for ativada
        pass

def build(task_runner=None, theme_service=None) -> QWidget:
    return MinhaPaginaPage(task_runner=task_runner, theme_service=theme_service)
```

2) Registre no manifesto (opcional caso confie na auto‑descoberta)

```
// app/assets/pages_manifest.json
[
  { "route": "home", "label": "Início", "sidebar": true, "order": 0,
    "factory": "app.pages.home_page:build" },
  { "route": "minha-pagina", "label": "Minha Página", "sidebar": true, "order": 50,
    "factory": "app.pages.minha_pagina_page:build" }
]
```

3) Execute e navegue: a página aparecerá na sidebar e breadcrumbs.

---

## Subpáginas Manualmente (sem CLI)

1) Rota e arquivo

- Para uma subpágina de `home`, crie `app/pages/home_detalhes_page.py` com `PAGE = { "route": "home/detalhes", ... }`.
- O breadcrumb mostrará `Home / Detalhes` automaticamente.

2) SideBar e order

- `sidebar: true` para aparecer no menu; `false` para rotas internas.
- Ajuste `order` para ordenar a exibição na sidebar.

3) Navegação programática

```
def _go(self, path: str):
    win = self.window(); r = getattr(win, "router", None)
    if r: r.go(path)
```

---

## Widgets: Guia Prático (Cookbook)

Botões (Controls.Button / PrimaryButton)

```
from ui.widgets.buttons import Controls

btn = Controls.Button("Primário", size_preset="md")
btn.setProperty("variant", "primary")  # outras: "chip", "ghost" (via QSS)
btn.clicked.connect(lambda: print("clicado"))
```

Tamanhos e variantes

- `size_preset`: `sm`, `md`, `lg`, `xl`, `char` (um caractere)
- `variant` (QSS): `primary`, `chip`, `ghost` (e outras que seu QSS definir)

Botão de comando (TaskRunner)

```
from ui.widgets.buttons import command_button
btn = command_button(
  text="Sincronizar",
  command_name="sync",
  task_runner=my_runner,
  payload={"force": True},
  disable_while_running=True,
  lock_after_click=False,
  size_preset="md"
)
```

Confirmação + comando

```
from ui.widgets.buttons import confirm_command_button
btn = confirm_command_button(
  text="Excluir",
  confirm_msg="Tem certeza?",
  command_name="delete_item",
  task_runner=my_runner,
  payload={"id": 123},
  size_preset="sm"
)
```

Navegar por rota (route_button)

```
from ui.widgets.buttons import route_button
go = lambda: self.window().router.go("home/detalhes")
btn = route_button("Ir", go, size_preset="sm")
```

Toggle / CheckBox / TextInput / Select

```
t = Controls.Toggle(); t.setChecked(True)
ck = Controls.CheckBox("Aceito termos")
inp = Controls.TextInput("Digite aqui...")
sel = Controls.InputList(); sel.addItems(["A", "B", "C"]) 
```

Ícone / LinkLabel

```
icon = Controls.IconButton("⋯", tooltip="Mais")
link = Controls.LinkLabel("Abrir documentação"); link.clicked.connect(lambda: print("abrir"))
```

Popover de ajuda (hover)

```
from ui.widgets.buttons import attach_popover
attach_popover(icon, "Ação X", "Executa a ação X", "Ctrl+X")
```

Expandir/colapsar painel (ExpandMore)

```
from ui.widgets.buttons import Controls
panel = QFrame(); panel.setLayout(QVBoxLayout()); panel.layout().addWidget(QLabel("Detalhes"))
exp = Controls.ExpandMore(panel, text_collapsed="Ver mais", text_expanded="Ver menos")
layout.addWidget(exp)
```

Slider em modo progresso (não interativo)

```
s = Controls.Slider(); s.setRange(0,100); s.setValue(42); s.setMode("progress")
```

Scroll customizado

```
scroll = Controls.ScrollArea(); scroll.setWidget(wrap)
```

AsyncTaskButton (tarefas assíncronas)

```
from ui.widgets.async_button import AsyncTaskButton

ab = AsyncTaskButton(
  "Executar",
  task_runner=my_runner,
  command_name="processar",
  payload={"limit": 10},
  block_input=True,      # opcional: bloqueia com overlay
  use_overlay=True,
  overlay_message="Processando...",
  progress_text="Processando…", progress_kind="info", progress_cancellable=False,
)
ab.succeeded.connect(lambda *_: print("ok"))
ab.failed.connect(lambda *_: print("falha"))
layout.addWidget(ab)
```

Toasts (simples, ação e progresso)

```
from ui.widgets.toast import show_toast, show_action_toast, ProgressToast
show_toast(self, "Salvo com sucesso", kind="ok")

show_action_toast(
  self, "Exportação", "Arquivo pronto.", kind="ok",
  actions=[{"label":"Abrir pasta","command":"abrir_pasta","payload":{}}], persist=True
)

pt = ProgressToast.start(self, "Sincronizando…", kind="info", cancellable=True)
pt.set_indeterminate(True)
pt.update(3, 10)
pt.finish(True, "Concluído")
```

LoadingOverlay manual

```
from ui.widgets.loading_overlay import LoadingOverlay
ov = LoadingOverlay(self, message="Carregando…", block_input=True)
ov.show(); ...; ov.hide()
```

Quick Open programático

```
from ui.dialogs.quick_open import QuickOpenDialog
dlg = QuickOpenDialog(self.window().router._pages.keys(), parent=self)
dlg.exec()
```

---

## Personalização Visual & Chrome

- TitleBar: o ícone do app troca conforme o tema; ícones em `app/assets/icons/app/`.
- TopBar: breadcrumb e sino já integrados; badge reflete o Centro de Notificações.
- Sidebars: `OverlaySidePanel` (navegação) e `SettingsSidePanel` (configurações) estilizáveis via QSS.
- PushSidePanel (direita): painel do Centro de Notificações com redimensionamento por “grip”.

---

## Centro de Notificações (avançado)

Interaja com o barramento para criar/atualizar/remover entradas:

```
from ui.widgets.toast import notification_bus
bus = notification_bus()

bus.addEntry.emit({
  "id": "abc123", "type": "info", "title": "Processo iniciado",
  "text": "Aguarde…", "persist": True, "expires_on_finish": True
})

bus.updateEntry.emit({"id": "abc123", "text": "50%"})
bus.finishEntry.emit("abc123")
bus.removeEntry.emit("abc123")
```

---

## Temas: Dicas & Avançado

- Adicione variáveis em `*.json` na chave `vars` e faça referência no `base.qss` usando `{{token}}`, `{token}` ou `${token}`.
- Tokens derivados (ex.: `content_bg`) são gerados automaticamente.
- O ThemeService observa `base.qss` e temas; alterações são aplicadas em tempo real.
- Use o Editor de Temas (painel) para editar e salvar de forma segura (gravação atômica).

Exemplo de uso de token no QSS

```
QPushButton[variant="chip"] {
  background: {{surface}}; color: {{text}}; border: 1px solid {{box_border}};
}
```

---

## Troubleshooting

- Página não aparece
  - Verifique se o módulo está em `app/pages` e exporta `PAGE` e `build()`.
  - Cheque `pages_manifest.json` ou rode `python -m ui.cli manifest-update`.
- QSS não aplica
  - Verifique `app/assets/qss/base.qss`. O ThemeService emite sinais nas trocas; acompanhe logs.
- Toasts não aparecem
  - Confirme se o app está rodando com `AppShell` padrão; toasts dependem do shell frameless.

---

## Blueprint de Página (modelo recomendado)

Use este esqueleto como base para novas páginas, mantendo consistência visual e técnica.

```python
from __future__ import annotations
from PySide6.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QFrame, QLabel

# Metadados de rota (sidebar, ordem e rótulo)
PAGE = {
    "route": "minha-pagina",
    "label": "Minha Página",
    "sidebar": True,
    "order": 50,
}

class MinhaPaginaPage(QWidget):
    def __init__(self, task_runner=None, theme_service=None):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(12)

        # Área rolável para conteúdos longos
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)

        # Container real do conteúdo
        wrap = QFrame()
        wrap_l = QVBoxLayout(wrap)
        wrap_l.setContentsMargins(0, 0, 0, 0)
        wrap_l.setSpacing(10)

        # Conteúdo inicial
        wrap_l.addWidget(QLabel("Olá, mundo!"))
        wrap_l.addStretch(1)

        scroll.setWidget(wrap)
        root.addWidget(scroll, 1)

    # Hook de ciclo de vida: chamado quando a rota é ativada
    def on_route(self, params: dict | None = None):
        # Atualize conteúdo/estado a partir de params, se necessário
        pass

def build(task_runner=None, theme_service=None) -> QWidget:
    return MinhaPaginaPage(task_runner=task_runner, theme_service=theme_service)
```

Boas práticas para páginas

- Use `QScrollArea` como container padrão para manter UX consistente.
- Centralize estilos no `base.qss`; evite `setStyleSheet` diretamente em widgets.
- Utilize `on_route(params)` para reagir a navegação em vez de lógicas no `__init__`.
- Prefira nomes de rota em kebab-case (ex.: `relatorios-anuais`).

---

## Qualidade de Código (Linting & Style)

Ferramentas sugeridas

- Ruff (lint & fix): `pip install ruff`  •  `ruff check .`  •  `ruff check . --fix`
- Black (format): `pip install black`  •  `black .`
- isort (imports): `pip install isort`  •  `isort .`
- mypy (tipagem opcional): `pip install mypy`  •  `mypy ui app`

Dicas de estilo

- Tipagem: anote funções e atributos públicos; use `Optional[...]` e `| None` onde apropriado.
- Nomes: rotas em kebab-case; módulos/arquivos em snake_case; classes em PascalCase; variáveis/funções em snake_case.
- Sinais/slots: prefira nomes descritivos (`openNotificationsRequested`, `setUnreadCountRequested`).
- Páginas: exponha `PAGE` + `build(...)`; use `on_route(params)` para ciclo de vida.
- QSS: declare variantes com `setProperty("variant", ...)` e tamanhos com `setProperty("size", ...)`.
- Imports: agrupe padrão→terceiros→locais; mantenha ordem alfabética (use `isort`).
- Formatação: 88 colunas (black), quebras legíveis, evite linhas muito longas.

Sobre o arquivo pyproject.toml

- O que é: um arquivo único de configuração (na raiz do projeto) que centraliza as regras de ferramentas como Black, Ruff, isort e mypy.
- Onde fica: `pyproject.toml` na raiz deste repositório.
- Por que usar: padroniza estilo e qualidade para todo o time, reduzindo ruído em PRs e tornando os comandos previsíveis.
- Como funciona: cada ferramenta lê suas opções diretamente do `pyproject.toml`, então você não precisa passar flags nos comandos.

Comandos do dia a dia (usam o pyproject.toml):

```
# Lint (apenas checar)
ruff check .

# Lint com correções automáticas
ruff check . --fix

# Formatar código (opiniado)
black .

# Organizar imports
isort .

# Checar tipos (opcional, gradual)
mypy ui app
```

Sugestões de fluxo

- Para iniciantes: rode `ruff check . --fix` e depois `black .`; se houver import bagunçado, rode `isort .`.
- Para quem já domina: configure um pre-commit com `ruff`, `black` e `isort` ou adicione esses passos no seu CI.
