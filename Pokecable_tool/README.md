# PokeCable - R36S Trading Tool

Ferramenta visual para trading de Pokémon no R36S.

O app abre localmente no console, analisa o save no próprio aparelho e usa o WebSocket do site apenas para a sala e sincronização da troca.
Sprites dos Pokémon são carregados via API do backend (`/sprites/...`) e cacheados localmente em `~/.pokecable/sprites`.

**Padrão:** Simplificado (baseado em Task_Manager)

## Dependências

```bash
sudo apt install python3-pygame python3-websockets
```

## Arquivos

- **pokecable.sh** - Launcher
- **r36s_pokecable_ui.py** - Interface gráfica
- **r36s_pokecable_core.py** - Lógica de estado e fluxo WebSocket
- **pokecable_save.py** - Parser local e escrita segura do save
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

Para sprites, a UI converte esse endereço para HTTP/HTTPS automaticamente:

- `ws://host/ws` -> `http://host/sprites/...`
- `wss://host/ws` -> `https://host/sprites/...`

Config em: `~/.pokecable/server.conf`

## Fluxo Atual

- Seleção de save local `.sav/.srm`
- Acesso a sala com criação automática quando ela não existe
- Seleção de Pokémon da `Party` ou do `PC`
- Backup automático antes de gravar
- Escrita real da troca no save local

Matriz segura atual:

- `Party -> Party`
- `Party -> PC`
- `PC -> PC`

Limitação atual:

- `PC -> Party` ainda não é aplicado localmente no R36S. Quando o Pokémon remoto vier do `PC`, escolha um slot do `PC` como destino local.

## Logs

```bash
tail -f logs/latest/all.log
```

## Debug Mode

Para ativar debug mode com logs mais verbosos:

```bash
POKECABLE_DEBUG=1 ./pokecable.sh
```

Veja `debug_tools/README.md` para mais informações.
