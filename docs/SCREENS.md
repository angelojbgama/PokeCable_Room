# Telas Disponíveis para Debug

Use o argumento do script para abrir em qualquer tela:

```bash
./pokecable.sh <nome_da_tela>
```

O nome da tela corresponde ao `screen_id` registrado em `frontend/screens/`.
Qualquer `screen_id` registrado pode ser passado como argumento inicial.

## Telas Disponíveis

### Menu Principal
- `menu` - Menu principal (padrão). Itens: Acessar sala, Troca local, Config, Infos, Verificar atualização, Extras, Sair
- `config` - Tela de configuração
- `update_check` - Verificação de atualização da ferramenta

### Infos
- `infos_topics` - Lista de tópicos de ajuda/informação
- `infos_reader` - Leitor do tópico selecionado (com scroll)

### Fluxo Principal (Sala / Troca Online)
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

### Extras (aplicar eventos/utilitários a um save)
- `extras_select_save` - Selecionar save para aplicar extras (pré-analisa os saves em background)
- `extras_category` - Selecionar categoria (eventos, utilitários, e-reader)
- `extras_events` - Lista de eventos oficiais (tickets) aplicáveis ao save
- `extras_utilities` - Utilitários aplicáveis ao save
- `extras_ereader` - Batalhas/cards e-reader
- `extras_item_category` - Selecionar categoria de item consumível (Pokébolas, Cura, Status, PP, Vitaminas, Batalha, Repelente, Flautas, Berries)
- `extras_item_select` - Selecionar item consumível e quantidade (L/R ajusta a quantidade) para adicionar à mochila
- `extras_result` - Resultado da operação de extras

### Confirmações e Modais
- `cancel_waiting_confirm` - Confirmar cancelamento
- `leave_room_confirm` - Confirmar saída da sala
- `info_modal` - Modal de informação
- `resolve_moves` - Resolver movimentos incompatíveis
- `resolve_item_relocation` - Resolver realocação de itens segurados na troca
- `evolution_cancel_prompt` - Prompt de cancelamento de evolução
- `evolution_cancel_confirm` - Confirmação de cancelamento de evolução

## Exemplos

```bash
# Abrir na tela de seleção de Pokémon (com dados carregados)
./pokecable.sh select_pokemon

# Abrir na tela aguardando parceiro
./pokecable.sh waiting_partner

# Abrir na seleção de save dos Extras
./pokecable.sh extras_select_save

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
