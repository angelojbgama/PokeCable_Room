# PokeCable R36S - Flow Reordering

## Resumo das Mudanças

O fluxo da ferramenta foi reordenado para seguir o padrão do site web: **selecionar save primeiro, depois inputs de sala/senha**.

### Fluxo Anterior (ERRADO)
```
Menu → Nome Sala → Senha → Load Save → Selecionar Pokémon → Trade
```

### Novo Fluxo (CORRETO)
```
Menu → [Criar/Entrar Sala] → Load Save → Selecionar Pokémon → Nome Sala → Senha → Trade
```

## Mudanças Implementadas

### 1. Novo Estado: `action_menu`
- **Quando**: Após selecionar "Acessar Sala" no menu principal
- **O quê**: Permite escolher entre "Criar Sala" ou "Entrar em Sala"
- **Resultado**: Define `action = "create"` ou `action = "join"`

### 2. Reordenação da Máquina de Estados

#### Menu → Action Menu
```python
if menu_index == 0:  # "Acessar Sala"
    current_screen = "action_menu"
    menu_index = 0
```

#### Action Menu → Load Save
```python
elif current_screen == "action_menu" and action:
    if action == "select":
        action = "create" or "join"  # Based on selection
        current_screen = "load_save"
```

#### Load Save → Select Pokemon
```python
elif action == "select" and state.saves:
    state.selected_save = state.saves[menu_index]
    state.load_pokemon(state.selected_save, "party")
    current_screen = "select_pokemon"
```

#### Select Pokemon → Enter Room Name
```python
elif action == "select" and state.pokemon_list:
    state.selected_pokemon = state.pokemon_list[menu_index]
    current_screen = "enter_room_name"  # CHANGED: was start_trade_thread
```

#### Enter Room Name → Enter Password
Sem mudanças, continua igual.

#### Enter Password → Start Trade
```python
elif keyboard_index == 42:  # OK
    state.room_name = room_name
    state.room_password = room_password
    trade_thread = start_trade_thread(state, action, ui_queue, confirm_queue)  # CHANGED: now uses action
    current_screen = "connecting"
```

### 3. Função Nova: `draw_action_menu()`
Desenha menu com duas opções:
- Criar Sala
- Entrar em Sala

### 4. Navegação "Back"
- `action_menu` → Back → `menu`
- `load_save` → Back → `menu` (foi `enter_password`)
- `enter_room_name` → Back → `select_pokemon` (se vazio) ou deleta char
- `enter_password` → Back → `enter_room_name` (se vazio) ou deleta char

### 5. Reset de Estado
Ao retornar para menu após trade ou cancelamento:
```python
action = None
room_name = ""
room_password = ""
state.selected_save = None
state.selected_pokemon = None
```

## Testes

### Teste 1: Criar Sala
1. Menu → "Acessar Sala"
2. Action Menu → "Criar Sala"
3. Load Save → Selecionar save
4. Select Pokemon → Selecionar pokémon
5. Enter Room Name → Digitar "test-room"
6. Enter Password → Digitar senha
7. Aguardar segundo jogador ✓

### Teste 2: Entrar em Sala
1. Menu → "Acessar Sala"
2. Action Menu → "Entrar em Sala"
3. Load Save → Selecionar save
4. Select Pokemon → Selecionar pokémon
5. Enter Room Name → Digitar "test-room"
6. Enter Password → Digitar senha
7. Conectar à sala existente ✓

### Teste 3: Navegação Back
- Em qualquer tela: Back volta ao anterior corretamente
- Estado limpo ao retornar para menu

## Arquivos Modificados

- `r36s_pokecable_ui.py` - Reordenação completa do fluxo e nova função `draw_action_menu()`
- `r36s_pokecable_core.py` - Sem mudanças necessárias

## Status

✅ Sintaxe verificada
✅ Fluxo reordenado
✅ Navegação "back" implementada
✅ Reset de estado implementado
⏳ Testes em r36s pendentes (depende de hardware)
