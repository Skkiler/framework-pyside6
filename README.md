# UI Exec Framework (PySide6)

> Framework modular para criação de interfaces desktop em **Python + PySide6**, com arquitetura extensível, roteamento dinâmico, temas configuráveis (QSS + JSON), injeção de dependências e CLI para scaffolding de páginas.

---

## Sumário
- [1. Visão Geral](#1-visão-geral)
- [2. Arquitetura e Estrutura](#2-arquitetura-e-estrutura)
  - [2.1. Mapa de Diretórios](#21-mapa-de-diretórios)
  - [2.2. Fluxo de Inicialização](#22-fluxo-de-inicialização)
  - [2.3. Componentes Principais](#23-componentes-principais)
- [3. Dependências e Instalação](#3-dependências-e-instalação)
- [4. Execução do Aplicativo](#4-execução-do-aplicativo)
- [5. Criação e Registro de Páginas](#5-criação-e-registro-de-páginas)
  - [5.1. Manifesto (JSON)](#51-manifesto-json)
  - [5.2. Autodescoberta (`app/pages`)](#52-autodescoberta-apppages)
  - [5.3. Injeção de Dependências](#53-injeção-de-dependências)
- [6. Sistema de Temas (QSS + JSON)](#6-sistema-de-temas-qss--json)
  - [6.1. Tokens e Estrutura](#61-tokens-e-estrutura)
  - [6.2. Criando e Editando Temas](#62-criando-e-editando-temas)
- [7. Execução de Tarefas e Toasts](#7-execução-de-tarefas-e-toasts)
- [8. CLI e Automação](#8-cli-e-automação)
- [9. Widgets Incluídos](#9-widgets-incluídos)
- [10. Tutoriais e Exemplos Práticos](#10-tutoriais-e-exemplos-práticos)
  - [10.1. Criando uma Nova Página](#101-criando-uma-nova-página)
  - [10.2. Criando um Novo Tema](#102-criando-um-novo-tema)
  - [10.3. Integrando um Runner Personalizado](#103-integrando-um-runner-personalizado)
- [11. Boas Práticas](#11-boas-práticas)
- [12. Roadmap e Extensões Futuras](#12-roadmap-e-extensões-futuras)

---

## 1. Visão Geral

O **UI Exec Framework** fornece uma base sólida e reutilizável para desenvolvimento de aplicações desktop modernas com **PySide6**, priorizando modularidade, produtividade e escalabilidade.  

Principais recursos:

- **Janela Frameless** com sombra e cantos arredondados.  
- **Roteamento de páginas** com `Router` e suporte a autodescoberta.  
- **Sistema de temas** dinâmico via **QSS + JSON** com tokens reutilizáveis.  
- **Splash Screen** opcional e personalizável.  
- **Toasts de notificação e progresso** integrados.  
- **CLI para scaffolding** de páginas e componentes.  
- **Injeção de dependências** em fábricas de páginas.  
- **Hot-reload de temas e QSS** em tempo real.  

---

## 2. Arquitetura e Estrutura

### 2.1. Mapa de Diretórios

```
app/
  app.py
  settings.py
  assets/
    icons/
    qss/
    themes/
    cache/
  pages/
    home_page.py
    settings.py
    theme_editor.py
    base_page.py
    registry.py

ui/
  core/
    main.py
    app.py
    app_controller.py
    router.py
    theme_service.py
    frameless_window.py
    settings.py
    utils/
      factories.py
      paths.py
      theme_icon_watcher.py
  services/
    qss_renderer.py
    theme_repository_json.py
    task_runner_adapter.py
  widgets/
    toast.py
    async_button.py
    buttons.py
    titlebar.py
    overlay_sidebar.py
    loading_overlay.py
  splash/
    splash.py

requirements.txt
README.md
```

### 2.2. Fluxo de Inicialização

1. `ui/core/main.py` inicia o aplicativo via `app.app.main()`.  
2. `app/app.py` cria a instância `QApplication`, inicializa `AppController` e exibe o **Splash** (opcional).  
3. `AppController` configura o `AppShell`, carrega páginas e aplica o tema padrão.  
4. `AppShell` constrói a janela principal com **TopBar**, **Sidebar** e **Router**.  

### 2.3. Componentes Principais

| Componente | Função |
|-------------|--------|
| **AppController** | Inicializa e gerencia rotas, temas e instâncias. |
| **AppShell** | Estrutura visual principal (TopBar, Sidebar, Router). |
| **Router** | Gerencia a navegação entre páginas. |
| **ThemeService** | Aplica temas e monitora alterações de QSS/JSON. |
| **TaskRunnerAdapter** | Interface para execução de tarefas externas. |
| **Toast / ProgressToast** | Exibe notificações e progresso visual. |
| **CLI** | Gera páginas e estruturas padrão automaticamente. |

---

## 3. Dependências e Instalação

Requisitos:
- Python **3.10+**
- PySide6

Instalação:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

---

## 4. Execução do Aplicativo

```bash
# Execução recomendada
python -m ui.core.main

# Alternativas
python -m app.app
python ui/core/main.py
```

Configurações principais em `app/settings.py`:

```python
APP_TITLE = "Meu App"
DEFAULT_THEME = "Aku"
FIRST_PAGE = "home"
```

---

## 5. Criação e Registro de Páginas

### 5.1. Manifesto (JSON)

Defina suas páginas em `app/assets/pages_manifest.json`:

```json
[
  {
    "route": "home",
    "label": "Início",
    "sidebar": true,
    "order": 0,
    "factory": "app.pages.home_page:build"
  }
]
```

### 5.2. Autodescoberta (`app/pages`)

O framework reconhece automaticamente páginas com `PAGE` e `build(...)`:

```python
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

PAGE = {
    "route": "relatorios",
    "label": "Relatórios",
    "sidebar": True,
    "order": 10
}

def build(task_runner=None, theme_service=None) -> QWidget:
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.addWidget(QLabel("Página de Relatórios"))
    return w
```

### 5.3. Injeção de Dependências

O `AppShell` injeta dependências automaticamente conforme parâmetros aceitos pela função `build(...)`:

- `task_runner` — executa tarefas (I/O, rede, etc.)  
- `theme_service` — reage a trocas de tema e fornece tokens visuais  

Exemplo:

```python
def build(task_runner=None, theme_service=None):
    task_runner.run_task("atualizar_dados", {})
```

---

## 6. Sistema de Temas (QSS + JSON)

### 6.1. Tokens e Estrutura

Cada tema é composto por:
- **QSS base:** `app/assets/qss/base.qss`  
- **JSON de variáveis:** `app/assets/themes/*.json`

Exemplo de tema:

```json
{
  "vars": {
    "bg": "#1a1a1a",
    "text": "#ffffff",
    "accent": "#4285f4"
  }
}
```

### 6.2. Criando e Editando Temas

Você pode criar um novo tema:
1. Duplicando um arquivo `.json` existente em `app/assets/themes`.  
2. Editando as cores e variáveis desejadas.  
3. Salvando com um novo nome (ex: `Ocean.json`).  

O **ThemeService** aplica automaticamente e permite **hot-reload**: alterações no `.json` ou `.qss` são aplicadas em tempo real.

---

## 7. Execução de Tarefas e Toasts

Para integração com lógica de negócio, implemente um runner customizado:

```python
class MyRunner:
    def run_task(self, name, payload):
        if name == "enviar_email":
            return {"ok": True, "data": "Enviado com sucesso"}
        return {"ok": False, "error": "Comando desconhecido"}
```

### Toasts e Progresso

```python
from ui.widgets.toast import Toast, ProgressToast

Toast.show(parent, text="Ação concluída!", kind="info")

pt = ProgressToast.start(parent, "Carregando dados...", kind="info", cancellable=True)
pt.update(5, 10)
pt.finish(True, "Processo finalizado!")
```

---

## 8. CLI e Automação

O **CLI** integrado (`ui/cli.py`) permite gerar páginas rapidamente:

```bash
python -m ui.cli new-page "Relatorios" --route relatorios
```

Isso cria um arquivo em `app/pages/relatorios_page.py` já com `PAGE` e `build()` preenchidos.

---

## 9. Widgets Incluídos

| Widget | Função |
|---------|--------|
| **TitleBar** | Barra de título customizada (min/max/close). |
| **TopBar** | Exibe o título atual e botão de menu lateral. |
| **OverlaySidePanel** | Sidebar flutuante com scrim. |
| **SettingsSidePanel** | Painel lateral direito. |
| **LoadingOverlay** | Overlay de carregamento (GIF). |
| **Toast / ProgressToast** | Notificações flutuantes. |
| **AsyncButton** | Executa tarefas assíncronas com feedback visual. |

---

## 10. Tutoriais e Exemplos Práticos

### 10.1. Criando uma Nova Página

```bash
python -m ui.cli new-page "Financeiro" --route financeiro
```

Isso gera automaticamente:

```python
PAGE = {"route": "financeiro", "label": "Financeiro", "sidebar": True, "order": 2}

def build(task_runner=None, theme_service=None):
    ...
```

### 10.2. Criando um Novo Tema

1. Duplique um tema existente (`Dark.json`).  
2. Renomeie para `MyTheme.json`.  
3. Altere as cores desejadas.  
4. Selecione o tema em **Configurações > Tema**.  

### 10.3. Integrando um Runner Personalizado

No arquivo `app/app.py`:

```python
from ui.services.task_runner_adapter import TaskRunnerAdapter

class MyRunner:
    def run_task(self, name, payload):
        if name == "calcular_relatorio":
            return {"ok": True, "data": "Relatório gerado"}
        return {"ok": False, "error": "Ação inválida"}

controller = AppController(task_runner=TaskRunnerAdapter(MyRunner()))
```

---

## 11. Boas Práticas

1. **Centralize estilos** no `base.qss`.  
2. **Evite** `setStyleSheet` direto em widgets.  
3. **Separe** lógica de UI e lógica de negócio (via `task_runner`).  
4. **Padronize** nomes de rotas (`kebab-case`).  
5. **Utilize** `theme_service` para cores e reatividade visual.  
6. **Organize** pastas e mantenha estrutura limpa para facilitar o autoload.  

---

## 12. Roadmap e Extensões Futuras

- Suporte a **subpáginas e histórico de navegação**.  
- **Centro de notificações persistente**.  
- **Logger de eventos** integrável.  
- **Sistema de pesquisa e atalhos globais**.  
- **Gerenciador de estado leve** com Qt Signals.  
- **Empacotamento** com PyInstaller/Briefcase.  

---

© 2025 – UI Exec Framework | Documentação Técnica
