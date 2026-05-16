# PokeCable - R36S Trading Tool

Ferramenta visual para trading de Pokémon no R36S.

**Padrão:** Simplificado (baseado em Task_Manager)

## Dependências

```bash
sudo apt install python3-pygame
```

## Arquivos

- **pokecable.sh** - Launcher
- **r36s_pokecable_ui.py** - Interface gráfica
- **r36s_pokecable_core.py** - Lógica de estado
- **button_mapper.py** - Ferramenta de mapeamento
- **find_saves.py** - Busca de saves
- **logs/** - Logs

## Como Usar

```bash
./pokecable.sh
```

## Controles

| Botão | Ação |
|-------|------|
| **Analógico UP/DOWN** | Navegar |
| **Button 10** | Selecionar |
| **Button 1** | Voltar |

## Mapeamento de Botões

Direto no código (`r36s_pokecable_ui.py`):

```python
BUTTON_A = 10        # Select
BUTTON_B = 1         # Back
AXIS_Y = 1           # Navegação
AXIS_THRESHOLD = 0.7
```

## Backend

```
wss://9kernel.vps-kinghost.net/ws
```

Config em: `~/.pokecable/server.conf`

## Logs

```bash
tail -f logs/pokecable_*.log
```

## Debug Mode

Para ativar debug mode com logs mais verbosos:

```bash
POKECABLE_DEBUG=1 ./pokecable.sh
```

Veja `debug_tools/README.md` para mais informações.
