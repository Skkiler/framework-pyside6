<h1 align="center">UI Exec Framework (PySide6)</h1>

> Base modular para apps desktop com **janela frameless**, **roteamento de páginas**, **temas dinâmicos (QSS + JSON)**, **splash opcional**, **sidebar overlay**, **topbar responsiva** e **injeção de dependências** simples para suas páginas.

---

## Sumário
- [Visão Geral](#visão-geral)
- [Arquitetura e Estrutura](#arquitetura-e-estrutura)
  - [Mapa de diretórios](#mapa-de-diretórios)
  - [Fluxo de inicialização](#fluxo-de-inicialização)
  - [Componentes principais](#componentes-principais)
- [Dependências](#dependências)
- [Como Executar](#como-executar)
- [Como Criar/Registrar Páginas](#como-criarregistrar-páginas)
  - [Opção A — Manifesto (JSON)](#opção-a--manifesto-json)
  - [Opção B — Autodescoberta (convenção em `ui/pages`)](#opção-b--autodescoberta-convenção-em-uipages)
  - [Assinatura de `build(...)` e Injeção de Dependências](#assinatura-de-build-e-injeção-de-dependências)
- [Sistema de Temas (QSS + JSON)](#sistema-de-temas-qss--json)
  - [Tokens suportados](#tokens-suportados)
  - [Como criar/editar temas](#como-criareditar-temas)
- [Execução de Tarefas e Comandos](#execução-de-tarefas-e-comandos)
  - [`TaskRunnerAdapter` e `run_task(...)`](#taskrunneradapter-e-run_task)
  - [Botões de comando e ações assíncronas](#botões-de-comando-e-ações-assíncronas)
- [Widgets incluídos](#widgets-incluídos)
- [Dicas de Aplicação ao seu Projeto](#dicas-de-aplicação-ao-seu-projeto)
- [Roadmap / Extensões sugeridas](#roadmap--extensões-sugeridas)

---

## Visão Geral
Este repositório entrega um **framework leve** para acelerar a criação de UIs desktop em **Python + PySide6**. A ideia é que você foque na **lógica do seu projeto** — páginas, fluxos e tarefas — enquanto a base resolve:

- **Janela custom (frameless)** com sombra e cantos arredondados.
- **TopBar + Sidebar overlay** (hambúrguer) com **roteador de páginas**.
- **Temas dinâmicos** via **QSS parametrizado** (tokens) alimentado por **temas JSON**.
- **Splash screen** opcional (GIF/PNG).
- **Páginas plugáveis** via manifesto JSON **ou** autodescoberta em `ui/pages`.
- **Injeção de dependências** opcional para suas páginas (`task_runner`, `theme_service`).
- **Toasts/overlays** para feedback, loading e progresso.

---

## Arquitetura e Estrutura

### Mapa de diretórios
```text
app/
  app.py                 # ponto de entrada do app (cria QApplication + AppController)
  settings.py            # metadados e caminhos (APP_TITLE, DEFAULT_THEME, etc.)

ui/
  core/
    main.py              # entrypoint alternativo: `python -m ui.core.main`
    app.py               # AppShell (constrói janela, topbar, sidebar, router, theme service)
    app_controller.py    # orquestra inicialização, registra páginas e exibe a UI
    router.py            # navegação (QStackedWidget + `go(route, params)`)
    frameless_window.py  # janela sem moldura + sombra/cantos
    settings.py          # persistência simples de configurações (JSON)
    theme_service.py     # aplica temas (QSS render) e sinais de troca de tema
    command_bus.py       # barramento simples de comandos
    interface_ports.py   # protocolos/ports (ITaskRunner, IThemeRepository, ICommandBus)
    utils/
      factories.py       # chama fábricas com DI por kwargs aceitos (DIP)
      guard.py, paths.py # utilitários de suporte

  services/
    qss_renderer.py          # renderer que substitui tokens no `base.qss`
    theme_repository_json.py # repositório de temas (JSON em disco)
    task_runner_adapter.py   # adaptador para um objeto `run_task(name, payload)`

  pages/
    base_page.py         # Protocolo base; metadados `PAGE` de exemplo
    home_page.py         # Exemplo de página (botões, toasts, etc.)
    settings.py          # Página de ajustes/temas
    theme_editor.py      # Editor de temas (CRUD)
    registry.py          # carrega do manifesto e/ou descobre automaticamente

  widgets/
    titlebar.py          # barra de título custom (ícone, mover, minimizar, maximizar, fechar)
    topbar.py            # barra superior (título dinâmico) + botão hambúrguer
    overlay_sidebar.py   # sidebar esquerda em overlay (lista de páginas, com scrim)
    settings_sidebar.py  # painel lateral direito (configurações)
    async_button.py      # botão com execução de tarefa + overlay/toasts
    loading_overlay.py   # overlay de carregamento com GIF
    toast.py             # toasts (notificações) e `ProgressToast`
    buttons.py           # `Controls` (PrimaryButton, ToggleSwitch, etc.)

  assets/
    icons/               # app.ico, splash.gif/png, loading.gif
    qss/base.qss         # QSS com placeholders (tokens) do tema
    themes/*.json        # temas padrão (ex.: Dark.json, Light.json, Dracula.json, etc.)
    pages_manifest.json  # manifesto opcional de páginas

README.md                # (este arquivo, recomendado colocar na raiz do seu projeto)
requirements.txt         # PySide6
```

### Fluxo de inicialização
1. **`ui/core/main.py`** chama `from app.app import main` e executa `main()` (você pode rodar por aqui).
2. **`app/app.py`** cria `QApplication`, instancia `AppController` com base nas configs de `app/settings.py`, e (opcionalmente) exibe o **Splash** antes da janela principal.
3. **`ui/core/app_controller.py` (AppController)**:
   - configura o **AppShell** (janela + serviços),
   - carrega páginas via **manifesto** (`ui/assets/pages_manifest.json`) e/ou **autodescoberta**,
   - registra páginas e inicia tema + rota inicial.
4. **`ui/core/app.py` (AppShell)** monta a UI: **TopBar**, **OverlaySidePanel** (sidebar), **Router** (conteúdo), **SettingsSidePanel** e integra o **ThemeService**.

### Componentes principais
- **AppController** — Orquestrador da aplicação (config, páginas, exibição).
- **AppShell** — Contêiner visual (TopBar, Sidebar, Router, Settings).
- **Router** — Troca de páginas via `register(name, widget)` e `go(name, params)`. Suporta `on_route(params)` na página.
- **ThemeService** — Carrega/aplica temas JSON, renderiza QSS a partir de `base.qss` e publica sinais para reatividade.
- **Settings** — Persistência simples (JSON) em `ui/assets/cache`.
- **CommandBus** — Barramento de comandos (opcional).
- **TaskRunnerAdapter** — Ponte para seu executor de tarefas (vide seção tarefa).

---

## Dependências
- **Python 3.10+** (recomendado)
- **PySide6** (listado em `requirements.txt`)

Instalação rápida:
```bash
python -m venv .venv
# Windows
.venv\Scripts\pip install -r requirements.txt
# Linux/macOS
source .venv/bin/activate && pip install -r requirements.txt
```

---

## Como Executar
A partir da raiz do projeto:

```bash
# forma 1 (recomendada)
python -m ui.core.main

# forma 2
python -m app.app

# ou diretamente (dependendo do seu ambiente)
python ui/core/main.py
```

A configuração básica vem de **`app/settings.py`**:
```python
APP_TITLE = "Meu App"
DEFAULT_THEME = "Aku"
FIRST_PAGE = "home"
PAGES_MANIFEST_FILENAME = "pages_manifest.json"
```
Os caminhos internos (`UI_DIR`, `ASSETS_DIR`, `THEMES_DIR`, `QSS_DIR`, `CACHE_DIR`) já estão resolvidos e o app copia assets quando necessário.

---

## Como Criar/Registrar Páginas

### Opção A — Manifesto (JSON)
Arquivo: **`ui/assets/pages_manifest.json`**

Exemplo:
```json
[
  {
    "route": "Home",
    "label": "Ínicio",
    "sidebar": true,
    "order": 0,
    "factory": "ui.pages.home_page:build"
  }
]
```
**Campos**:
- `route` — nome único da rota (ex.: `"relatorios"`). Preferencialmente **kebab-case**.
- `label` — rótulo exibido na Sidebar/TopBar.
- `sidebar` — se `true`, aparece na sidebar.
- `order` — ordenação na sidebar (inteiro, menor vem primeiro).
- `factory` — `"<modulo>:<função>"` que deve **retornar um `QWidget`** da página.

> **Prioridade**: se você usar **manifesto** e **autodescoberta**, o **manifesto sobrepõe** (pelo `route`).

### Opção B — Autodescoberta (convenção em `ui/pages`)
Crie um arquivo em `ui/pages`, por exemplo **`ui/pages/relatorios_page.py`**, contendo:

```python
# ui/pages/relatorios_page.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

PAGE = {
    "route": "relatorios",    # nome da rota
    "label": "Relatórios",    # rótulo na sidebar/topbar
    "sidebar": True,          # aparece na sidebar
    "order": 10               # posição
}

def build(task_runner=None, theme_service=None) -> QWidget:
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.addWidget(QLabel("Relatórios"))
    # Você pode usar task_runner e theme_service se quiser (são injetados, se aceitar nos args)
    return w
```
**Convenções** usadas pela autodescoberta:
- Procura módulos em `ui/pages` e **usa `PAGE` + `build(...)`**.
- Se `PAGE["route"]` não for fornecido, a rota pode ser inferida do nome do módulo (ex.: `relatorios_page.py` → `"relatorios"`).
- Se `build` não existir, o módulo é ignorado e é impresso um aviso (modo dev).

### Assinatura de `build(...)` e Injeção de Dependências
O `AppShell.register_pages(...)` chama as fábricas com **injeção por kwargs conhecidos** (ver `ui/core/utils/factories.py`):
- Você **pode** declarar na sua `build(...)` os argumentos que quer usar:
  - `task_runner` — adaptador para execução de tarefas (vide abaixo).
  - `theme_service` — serviço de tema (útil para reagir a mudanças de tema).
- A fábrica **só receberá** os kwargs que declarar — nada de acoplamento forte.

Exemplo:
```python
def build(task_runner=None, theme_service=None) -> QWidget:
    ...
```

---

## Sistema de Temas (QSS + JSON)
- O QSS base está em **`ui/assets/qss/base.qss`** e usa **tokens** (`{{token}}` ou `{token}`) para cores/estilos.
- Cada tema é um **JSON** em **`ui/assets/themes/*.json`**, normalmente no formato:
  ```json
  {
    "vars": {
      "bg_start": "#000000",
      "bg_end":   "#141414",
      "text":     "#e5e5e5",
      "...":      "..."
    }
  }
  ```
- O `ThemeService` renderiza o QSS **mesclando tokens** do tema com **defaults** e **derivados** (ver `ui/services/qss_renderer.py`).

### Tokens suportados
Os **principais tokens** usados no `base.qss` (podem variar conforme sua versão do arquivo):
`bg_start`, `bg_end`, `bg`, `surface`, `text`, `muted`, `input_bg`, `btn`, `btn_hover`, `btn_text`, `checkbox`, `slider`, `cond_selected`, `box_border`, `hover`, `text_hover`, `window_bg`, `accent`, além de **derivados** gerados pelo renderer (ex.: `content_bg`, `panel_bg`).

### Como criar/editar temas
- Use a página **Settings** / **Theme Editor** para **duplicar/editar** temas.
- Ou crie um novo arquivo JSON em `ui/assets/themes`, seguindo o schema acima.
- O repositório de temas é abstraído por `IThemeRepository` com implementação em `ui/services/theme_repository_json.py`.

---

## Execução de Tarefas e Comandos

### `TaskRunnerAdapter` e `run_task(...)`
Para acoplar sua lógica (I/O, rede, automações, etc.), forneça um **runner** com **método**:
```python
def run_task(self, name: str, payload: dict) -> dict:
    # deve retornar {"ok": bool, "data": ..., "error": str?}
```
O framework usa `TaskRunnerAdapter` para padronizar o contrato e permitir **uso opcional com corrotinas** (se a função retornar `awaitable`, o adaptador resolve).

**Exemplo minimalista:**
```python
class MyRunner:
    def run_task(self, name, payload):
        if name == "enviar_email":
            # ... faça o trabalho ...
            return {"ok": True, "data": "ok"}
        return {"ok": False, "error": "comando desconhecido"}
```

Na inicialização (dentro do `main()`), passe o runner ao `AppController` (o entrypoint do repositório já faz isso por você; se precisar customizar, adapte `app/app.py`).

### Botões de comando e ações assíncronas
- **`ui/widgets/buttons.py`** expõe `command_button(text, command_name, task_runner, payload=None)` que cria um botão já conectado ao seu runner.
- **`ui/widgets/async_button.py`** facilita rodar tarefas em _background_ com overlay/toasts de progresso.
- **Toasts** (`ui/widgets/toast.py`) têm variantes de notificação e **progresso**.

---

## Widgets incluídos
- **TitleBar** — barra de título custom com ícone e botões nativos.
- **TopBar** — título dinâmico + hambúrguer (abre a sidebar esquerda).
- **OverlaySidePanel** — sidebar esquerda (lista de páginas) com **scrim** e animações.
- **SettingsSidePanel** — painel lateral direito para configurações.
- **LoadingOverlay** — overlay com GIF de loading.
- **Toast / ProgressToast** — notificações e barra de progresso.
- **Controls** — fábrica simples de widgets:
  - `Controls.Button` (PrimaryButton)
  - `Controls.Toggle` (ToggleSwitch)
  - `Controls.IconButton`
  - `Controls.TextInput`, `Controls.CheckBox`, `Controls.InputList`

---

## Dicas de Aplicação ao seu Projeto
1. **Modelagem das páginas**: trate cada área do seu app como uma **página** independente em `ui/pages`.
2. **Contrato de tarefas**: centralize I/O e integrações no seu **runner** (`run_task`) e use `command_button`/`AsyncTaskButton` para acionar.
3. **Temas**: padronize paleta/visual com 1–2 temas base (ex.: claro/escuro) e derive variações.
4. **Navegação**: use `router.go("minha-pagina")` (ou o botão de atalho) e, se necessário, implemente `on_route(params)` na página para reagir a parâmetros.
5. **Splash**: deixe opcional via Settings; útil em inicializações pesadas.
6. **Persistência leve**: use `ui/core/settings.py` quando precisar gravar pequenas preferências do usuário.
7. **Padronização visual**: centralize estilos no `base.qss` e use tokens — evite `setStyleSheet` ad-hoc.
8. **Escalabilidade**: separe **comandos** (CommandBus) da camada de UI para facilitar testes e evolução.

---

## Roadmap / Extensões sugeridas
- **CLI de scaffolding** (há um rascunho em `ui/cli.py`): gerar páginas automaticamente (`new-page`) com `PAGE` + `build(...)` pré-preenchidos.
- **Mecanismo de plugins**: carregar páginas/temas a partir de diretórios externos.
- **Gerenciador de estados**: camada leve de _store_ reativa (Qt signals) compartilhada entre páginas.
- **Empacotamento**: _bundlers_ como PyInstaller/Briefcase para distribuição (.exe, .app, .AppImage).

---

> **Suporte/Debug**: Em desenvolvimento, o framework imprime avisos caso um módulo de página não exponha `build(...)` ou esteja mal referenciado no manifesto. Aproveite para validar sua estrutura antes de empacotar.
