# 🧭 UI Framework (PySide6)

Uma base **modular, extensível e elegante** para aplicações desktop com **roteamento dinâmico**, **temas personalizáveis**, **execução de tarefas assíncronas**, **sidebar animada**, **topbar responsiva** e **autodescoberta de páginas**.  
Ideal para construir dashboards, ferramentas internas e apps de automação com **rapidez e escalabilidade**.

---

## 🚀 Índice

- [⚙️ Instalação](#️-instalação)
- [🗂 Estrutura do Projeto](#-estrutura-do-projeto)
- [🧩 Componentes Principais](#-componentes-principais)
- [🎨 Sistema de Temas](#-sistema-de-temas)
- [⚙️ Task Runner e Comandos](#️-task-runner-e-comandos)
- [🧪 Criando Novas Páginas](#-criando-novas-páginas)
- [🔧 Botões e Funções](#-botões-e-funções)
- [🎨 Personalizando a UI](#-personalizando-a-ui)
- [✅ Checklist de Novas Telas](#-checklist-de-novas-telas)
- [📦 Manifesto e Páginas](#-manifesto-e-páginas)
- [📜 Licença](#-licença)

---

## ⚙️ Instalação

```bash
# Instalar dependências
pip install PySide6

# Executar aplicação
python -m ui.core.main
```

---

## 🗂 Estrutura do Projeto

```
ui/
  core/              # Núcleo do framework
  pages/             # Telas do app
  widgets/           # Componentes reutilizáveis
  assets/            # Temas, QSS e ícones
```

**Pontos-chave:**

- `app_controller.py`: inicializa aplicação e páginas.
- `app.py`: cria janela base (`AppShell`) com roteamento, topbar e sidebar.
- `theme_service.py`: aplica e anima temas.
- `registry.py`: descobre páginas automaticamente ou via manifesto.
- `widgets/`: componentes prontos (botões, toasts, inputs, sidebar, etc).

---

## 🧩 Componentes Principais

### 🧠 AppController
- Responsável por inicializar o app, aplicar temas, registrar páginas e exibir a UI.

### 🏛️ AppShell
- Estrutura principal da interface.
- Inclui **TopBar**, **Sidebar** e o **Router** de páginas.
- Responsável por navegar entre telas e carregar componentes dinâmicos.

### 🧭 Router
- Gerencia o conteúdo ativo da janela.
- Permite alternar entre páginas com `.go("rota")`.

### 🎨 ThemeService
- Aplica temas dinâmicos com tokens (`{accent}`, `{bg_start}` etc).
- Suporta transição animada entre temas e persistência em cache.

### 🧰 Widgets
- Conjunto de componentes prontos para uso: botões, switches, inputs, toasts, etc.
- Inclui helpers para **ações síncronas**, **assíncronas** e **navegação**.

---

## 🎨 Sistema de Temas

- Temas são definidos em JSON dentro de `assets/themes/`.
- Cada tema contém um dicionário `"vars"` com cores e tokens.
- `base.qss` utiliza esses tokens dinamicamente.

Exemplo (`assets/themes/Dark.json`):

```json
{
  "vars": {
    "bg_start": "#2f2f2f",
    "text": "#e5e5e5",
    "accent": "#347de9",
    "btn": "#3f7ad1"
  }
}
```

Aplicar tema em runtime:

```python
controller.theme_service.apply("Dark", animate=True)
```

---

## ⚙️ Task Runner e Comandos

O `task_runner` executa operações do backend de forma síncrona ou assíncrona.

```python
class MyRunner:
    def run_task(self, name, payload):
        if name == "salvar":
            return {"ok": True, "data": "Salvo com sucesso"}
        return {"ok": False, "error": "Comando desconhecido"}
```

Integrando em botões:

```python
from ui.widgets.buttons import command_button
btn = command_button("Salvar", "salvar", task_runner)
```

Assíncrono:

```python
from ui.widgets.async_button import AsyncTaskButton
btn = AsyncTaskButton("Rodar", task_runner, "processar", {"heavy": True})
```

---

## 🧪 Criando Novas Páginas

Crie um novo módulo em `ui/pages/`:

```python
# ui/pages/reports_page.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from ..widgets.buttons import command_button

PAGE = {"route": "reports", "label": "Relatórios", "sidebar": True, "order": 10}

class ReportsPage(QWidget):
    def __init__(self, task_runner=None, theme_service=None):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Página de Relatórios"))
        lay.addWidget(command_button("Gerar", "gerar_relatorio", task_runner))

def build(task_runner=None, theme_service=None):
    return ReportsPage(task_runner, theme_service)
```

✅ **Importante:**  
- Inclua o dicionário `PAGE`.  
- Exporte a função `build()` (injeção automática de dependências).

---

## 🔧 Botões e Funções

| Tipo                     | Exemplo                                                         |
|-------------------------|------------------------------------------------------------------|
| Botão simples          | `command_button("Rodar", "proc_A", task_runner)`               |
| Botão com confirmação  | `confirm_command_button("Excluir", "Confirma?", "delete", runner)` |
| Botão assíncrono       | `AsyncTaskButton("Rodar", runner, "proc_B", {"heavy": True})`  |
| Toast rápido           | `show_toast(self.window(), "Sucesso!", "success")`            |

---

## 🎨 Personalizando a UI

- **TopBar:** altere título com `self.topbar.title.setText("Novo Título")`.
- **Sidebar:** configure fechamento automático (`close_on_select=True`).
- **Tema:** edite arquivos JSON em `assets/themes/` ou crie novos pelo editor de tema integrado.

---

## ✅ Checklist de Novas Telas

- [x] Criar módulo em `ui/pages/`
- [x] Adicionar `PAGE` e `build()`
- [x] Integrar botões e funções
- [x] Registrar automaticamente ou via `pages_manifest.json`
- [x] Testar navegação e tema

---

## 📦 Manifesto e Páginas

`pages_manifest.json` define a ordem e seleção manual de páginas:

```json
[
  {"module": "ui.pages.home_page", "route": "home", "label": "Início", "order": 1},
  {"module": "ui.pages.reports_page", "route": "reports", "label": "Relatórios", "order": 10}
]
```

Se não existir, o sistema faz **autodescoberta automática**.

---

## 📜 Licença

MIT © 2025 - Seu Projeto / Framework UI

---

💡 **Dica:** Combine este framework com APIs REST, scripts de automação ou bases de dados para criar ferramentas poderosas e totalmente customizadas.
