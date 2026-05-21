# Telas Disponíveis para Debug

Use o argumento do script para abrir em qualquer tela:

```bash
./pokecable.sh <nome_da_tela>
```

## Telas Disponíveis

### Fluxo Principal
- `menu` - Menu principal (padrão)
- `load_save` - Selecionar save file
- `select_pokemon` - Seleção de Pokémon (com dados carregados do primeiro save, e opção Y para alternar Party/PC)
- `enter_lan_endpoint` - Teclado para endereço LAN

### Trading
- `connecting` - Conectando ao servidor
- `waiting_partner` - Aguardando parceiro
- `trading` - Animação de troca em progresso
- `trade_confirm` - Confirmação da troca
- `trade_result` - Resultado da troca

### PC Management
- `deposit_confirm` - Confirmação para guardar Pokémon no PC
- `withdraw_confirm` - Confirmação para retirar Pokémon do PC

### Self Trade (Troca Local)
- `self_select_save_a` - Selecionar primeiro save
- `self_select_save_b` - Selecionar segundo save
- `self_select_pokemon_a` - Selecionar Pokémon do primeiro save
- `self_select_pokemon_b` - Selecionar Pokémon do segundo save
- `self_trade_confirm` - Confirmação da troca local

### Confirmações e Modais
- `cancel_waiting_confirm` - Confirmar cancelamento
- `leave_room_confirm` - Confirmar saída da sala
- `info_modal` - Modal de informação
- `resolve_moves` - Resolver movimentos incompatíveis
- `evolution_cancel_prompt` - Prompt de cancelamento de evolução
- `evolution_cancel_confirm` - Confirmação de cancelamento de evolução

### Config
- `config` - Tela de configuração

## Exemplos

```bash
# Abrir na tela de seleção de Pokémon (com dados carregados)
./pokecable.sh select_pokemon

# Abrir na tela aguardando parceiro
./pokecable.sh waiting_partner

# Abrir no menu padrão
./pokecable.sh
# ou
./pokecable.sh menu
```

## Notas

- Algumas telas precisam de dados carregados (saves, Pokémon, etc)
- A tela `select_pokemon` carrega automaticamente o primeiro save disponível
- Use as setas do teclado/controle para navegar
- Pressione ESC ou Back para retornar
