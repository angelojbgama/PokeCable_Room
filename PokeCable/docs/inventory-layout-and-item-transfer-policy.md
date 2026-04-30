# Layout de Inventário e Política de Destino do Item

Este documento fecha o bloco de mapeamento do inventário real dos saves e define a política-base de destino do item entre Gen 1, Gen 2 e Gen 3.

Ele ainda **não** aplica escrita na mochila/PC dentro da troca. O objetivo desta etapa é deixar:

- os layouts reais do save mapeados;
- a política de destino do item explicitada;
- a base pronta para o próximo bloco de implementação.

## Escopo

Este documento cobre:

- offsets e capacidades dos bolsos de inventário;
- diferenças entre famílias de jogo;
- codificação dos itens no save;
- regra-base para decidir se o item:
  - continua segurado;
  - vai para a mochila;
  - vai para o PC;
  - ou é removido.

Não cobre ainda:

- UI de mochila no frontend;
- escrita real do item em mochila/PC;
- lógica de overflow já integrada à troca;
- consumo persistente de itens em batalha.

## Fonte de verdade no código

- [inventory_layouts.py](/srv/PokeCable/backend/pokecable_room/data/inventory_layouts.py)
- [item_transfer_policy.py](/srv/PokeCable/backend/pokecable_room/data/item_transfer_policy.py)
- [items.py](/srv/PokeCable/backend/pokecable_room/data/items.py)
- [item-catalog.md](/srv/PokeCable/docs/item-catalog.md)

## Gen 1

Família:

- `pokemon_red`
- `pokemon_blue`
- `pokemon_yellow`

### Estrutura

| Pocket | Offset | Tamanho | Capacidade | Formato |
|---|---:|---:|---:|---|
| `bag_items` | `0x25C9` | `0x2A` | `20` | `count + pares (item, qtd) + terminador` |
| `pc_items` | `0x27E6` | `0x68` | `50` | `count + pares (item, qtd) + terminador` |

### Regras relevantes

- Gen 1 **não suporta held item**.
- Se o item existir no catálogo da Gen 1:
  - o item pode ser preservado fora do Pokémon;
  - destino preferido: mochila;
  - fallback: PC.
- Se o item **não existir** na Gen 1:
  - o item deve ser removido.

## Gen 2

Famílias:

- `pokemon_gold`
- `pokemon_silver`
- `pokemon_crystal`

### Gold / Silver

| Pocket | Offset | Tamanho | Capacidade | Formato |
|---|---:|---:|---:|---|
| `tm_hm` | `0x23E6` | `57` | `57` | vetor fixo de quantidades (`TM01..TM50`, `HM01..HM07`) |
| `items` | `0x241F` | `42` | `20` | `count + pares (item, qtd) + terminador` |
| `key_items` | `0x2449` | `27` | `26` | `count + ids + terminador` |
| `balls` | `0x2464` | `26` | `12` | `count + pares (item, qtd) + terminador` |
| `pc_items` | `0x247E` | `102` | `50` | `count + pares (item, qtd) + terminador` |

### Crystal

| Pocket | Offset | Tamanho | Capacidade | Formato |
|---|---:|---:|---:|---|
| `tm_hm` | `0x23E7` | `57` | `57` | vetor fixo de quantidades (`TM01..TM50`, `HM01..HM07`) |
| `items` | `0x2420` | `42` | `20` | `count + pares (item, qtd) + terminador` |
| `key_items` | `0x244A` | `27` | `26` | `count + ids + terminador` |
| `balls` | `0x2465` | `26` | `12` | `count + pares (item, qtd) + terminador` |
| `pc_items` | `0x247F` | `102` | `50` | `count + pares (item, qtd) + terminador` |

### Regras relevantes

- Gen 2 suporta held item.
- Se o item existe na Gen 2, o comportamento preferido é:
  - continuar segurado, se a categoria puder ser segurada;
  - senão, mochila;
  - se a mochila estiver cheia, PC.
- Itens sem equivalente/sem existência em Gen 2:
  - removidos.

## Gen 3

Famílias:

- `pokemon_ruby`
- `pokemon_sapphire`
- `pokemon_emerald`
- `pokemon_firered`
- `pokemon_leafgreen`

### Ruby / Sapphire

| Pocket | Offset | Tamanho | Capacidade | Formato |
|---|---:|---:|---:|---|
| `pc_items` | `0x0498` | `200` | `50` | slots `(u16 item_id, u16 quantity)` |
| `items` | `0x0560` | `80` | `20` | slots `(u16 item_id, u16 quantity_xor)` |
| `key_items` | `0x05B0` | `80` | `20` | slots `(u16 item_id, u16 quantity_xor)` |
| `balls` | `0x0600` | `64` | `16` | slots `(u16 item_id, u16 quantity_xor)` |
| `tm_hm` | `0x0640` | `256` | `64` | slots `(u16 item_id, u16 quantity_xor)` |
| `berries` | `0x0740` | `184` | `46` | slots `(u16 item_id, u16 quantity_xor)` |

### Emerald

| Pocket | Offset | Tamanho | Capacidade | Formato |
|---|---:|---:|---:|---|
| `pc_items` | `0x0498` | `200` | `50` | slots `(u16 item_id, u16 quantity)` |
| `items` | `0x0560` | `120` | `30` | slots `(u16 item_id, u16 quantity_xor)` |
| `key_items` | `0x05D8` | `120` | `30` | slots `(u16 item_id, u16 quantity_xor)` |
| `balls` | `0x0650` | `64` | `16` | slots `(u16 item_id, u16 quantity_xor)` |
| `tm_hm` | `0x0690` | `256` | `64` | slots `(u16 item_id, u16 quantity_xor)` |
| `berries` | `0x0790` | `184` | `46` | slots `(u16 item_id, u16 quantity_xor)` |

### FireRed / LeafGreen

| Pocket | Offset | Tamanho | Capacidade | Formato |
|---|---:|---:|---:|---|
| `pc_items` | `0x0298` | `120` | `30` | slots `(u16 item_id, u16 quantity)` |
| `items` | `0x0310` | `168` | `42` | slots `(u16 item_id, u16 quantity_xor)` |
| `key_items` | `0x03B8` | `120` | `30` | slots `(u16 item_id, u16 quantity_xor)` |
| `balls` | `0x0430` | `52` | `13` | slots `(u16 item_id, u16 quantity_xor)` |
| `tm_hm` | `0x0464` | `232` | `58` | slots `(u16 item_id, u16 quantity_xor)` |
| `berries` | `0x054C` | `172` | `43` | slots `(u16 item_id, u16 quantity_xor)` |

### Regras relevantes

- Mochila usa `security key` para mascarar a quantidade.
- PC **não** usa `security key`.
- Gen 3 suporta held item.
- Se o item existe na geração de destino:
  - continua segurado quando a categoria permite;
  - caso contrário, vai para mochila;
  - se faltar espaço, vai para o PC.

## Política-base de destino do item

Implementada em:

- [item_transfer_policy.py](/srv/PokeCable/backend/pokecable_room/data/item_transfer_policy.py)

### Decisões possíveis

- `keep_held`
- `move_to_bag`
- `move_to_pc`
- `remove`

### Regras

#### 1. Sem item

- `None` ou `0`
- decisão: `remove`
- razão: `no_item`

#### 2. Item existe na geração de destino e pode continuar segurado

- decisão: `keep_held`
- razões:
  - `same_item_available`
  - `equivalent_held_item_available`

#### 3. Item existe na geração de destino, mas o Pokémon/geração não pode mantê-lo segurado

Casos:

- Gen 1 recebendo item preservável;
- item existe, mas a categoria não faz sentido como held item (`tm`, `hm`, `badge`, `system`, `unused`).

Decisão:

- primária: `move_to_bag`
- fallback: `move_to_pc`

Razões:

- `item_exists_but_target_cannot_hold`
- `item_exists_but_category_not_holdable`

#### 4. Item não existe na geração de destino

- decisão: `remove`
- razão: `item_absent_in_target_generation`

## Implicação importante para a troca

Esta etapa **não mudou o fluxo atual da troca**.

Hoje o projeto já sabe:

- listar itens do catálogo;
- decidir se o item existe na geração destino;
- decidir o destino teórico do item.

O próximo bloco é implementar isso no commit local da troca:

1. tentar manter segurado;
2. se não puder, tentar mochila;
3. se mochila cheia, tentar PC;
4. se o item não existir na geração destino, remover;
5. registrar tudo no relatório e metadata de backup.

## Casos práticos

### Gen 3 Potion -> Gen 1

- `Potion` existe na Gen 1
- Gen 1 não tem held item
- decisão:
  - `move_to_bag`
  - fallback `move_to_pc`

### Gen 3 Metal Coat -> Gen 1

- `Metal Coat` não existe na Gen 1
- decisão:
  - `remove`

### Gen 3 Dragon Scale -> Gen 2

- há equivalente em Gen 2
- Gen 2 suporta held item
- decisão:
  - `keep_held`

### Gen 3 TM01 -> Gen 3

- item existe
- categoria `tm`
- não deve continuar segurado
- decisão:
  - `move_to_bag`
  - fallback `move_to_pc`

## Próximo bloco recomendado

1. implementar leitura real do inventário nos parsers Gen 1/2/3;
2. criar API interna única para:
   - `list_inventory()`
   - `can_store_in_bag()`
   - `store_in_bag()`
   - `store_in_pc()`
3. aplicar a política de destino do item no commit da troca;
4. adicionar testes com saves reais cobrindo mochila cheia e fallback para PC.
