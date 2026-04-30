# Compatibilidade de Itens Entre Gerações

Este documento descreve o que o projeto **modela hoje** para itens no fluxo de troca.

Escopo atual:

- foco em **held items**
- foco em **evolução por item via troca**
- foco em **compatibilidade entre Gen 1, Gen 2 e Gen 3**

Este documento **não** lista todos os itens existentes dos jogos. Ele lista os itens que o código já conhece e trata com segurança no fluxo atual.

Arquivos de referência no código:

- [PokeCable/backend/pokecable_room/data/items.py](/srv/PokeCable/backend/pokecable_room/data/items.py)
- [PokeCable/backend/pokecable_room/converters/gen2_to_gen1.py](/srv/PokeCable/backend/pokecable_room/converters/gen2_to_gen1.py)
- [PokeCable/backend/pokecable_room/converters/gen2_to_gen3.py](/srv/PokeCable/backend/pokecable_room/converters/gen2_to_gen3.py)
- [PokeCable/backend/pokecable_room/converters/gen3_to_gen1.py](/srv/PokeCable/backend/pokecable_room/converters/gen3_to_gen1.py)
- [PokeCable/backend/pokecable_room/converters/gen3_to_gen2.py](/srv/PokeCable/backend/pokecable_room/converters/gen3_to_gen2.py)

## Regra principal

- **Gen 1 não suporta held item.**
- Um Pokémon pode ser convertido e recebido por Gen 1, mas o item segurado é removido.
- Entre **Gen 2** e **Gen 3**, o item só é preservado quando existe mapeamento explícito por equivalência.

## Catálogo atualmente modelado

### Gen 1

Nenhum held item é modelado porque Gen 1 não possui esse conceito no save.

| Geração | Itens modelados |
|---|---|
| Gen 1 | nenhum |

### Gen 2

| ID Gen 2 | Nome | Observação |
|---|---:|---|
| `0x52` | King's Rock | usado em compatibilidade e evolução por item |
| `0x8F` | Metal Coat | usado em compatibilidade e evolução por item |
| `0x97` | Dragon Scale | usado em compatibilidade e evolução por item |
| `0xAC` | Up-Grade | usado em compatibilidade e evolução por item |

### Gen 3

| ID Gen 3 | Nome | Observação |
|---|---:|---|
| `187` | King's Rock | usado em compatibilidade e evolução por item |
| `192` | Deep Sea Tooth | usado em evolução por item de Clamperl |
| `193` | Deep Sea Scale | usado em evolução por item de Clamperl |
| `199` | Metal Coat | usado em compatibilidade e evolução por item |
| `201` | Dragon Scale | usado em compatibilidade e evolução por item |
| `218` | Up-Grade | usado em compatibilidade e evolução por item |

## Matriz de equivalência atual

O código atual usa equivalência **por nome** entre gerações.

### Equivalentes entre Gen 2 e Gen 3

| Nome | ID Gen 2 | ID Gen 3 | Preserva em Gen 2 -> Gen 3 | Preserva em Gen 3 -> Gen 2 |
|---|---:|---:|---|---|
| King's Rock | `0x52` | `187` | sim | sim |
| Metal Coat | `0x8F` | `199` | sim | sim |
| Dragon Scale | `0x97` | `201` | sim | sim |
| Up-Grade | `0xAC` | `218` | sim | sim |

### Sem equivalente atual em Gen 2

| Nome | ID Gen 3 | Resultado em Gen 3 -> Gen 2 |
|---|---:|---|
| Deep Sea Tooth | `192` | removido |
| Deep Sea Scale | `193` | removido |

## Regras por direção

### Gen 2 -> Gen 1

Regra atual:

- o Pokémon pode ser convertido se a species existir
- o held item é sempre removido

Consequência:

- King's Rock -> removido
- Metal Coat -> removido
- Dragon Scale -> removido
- Up-Grade -> removido

### Gen 3 -> Gen 1

Regra atual:

- o Pokémon pode ser convertido se a species existir
- o held item é sempre removido

Consequência:

- King's Rock -> removido
- Metal Coat -> removido
- Dragon Scale -> removido
- Up-Grade -> removido
- Deep Sea Tooth -> removido
- Deep Sea Scale -> removido

### Gen 2 -> Gen 3

Regra atual:

- o item é preservado **somente** se existir equivalente conhecido em Gen 3
- se não houver equivalente, o item é removido

Itens que preservam:

- King's Rock
- Metal Coat
- Dragon Scale
- Up-Grade

### Gen 3 -> Gen 2

Regra atual:

- ability e nature são removidas por limitação de geração
- o item é preservado **somente** se existir equivalente conhecido em Gen 2
- se não houver equivalente, o item é removido

Itens que preservam:

- King's Rock
- Metal Coat
- Dragon Scale
- Up-Grade

Itens que não preservam:

- Deep Sea Tooth
- Deep Sea Scale

## Resposta objetiva para a dúvida principal

> Um item que não existe na Gen 1 pode ser passado pelo Gen 3 através de um Pokémon?

No modelo atual do projeto:

- **o Pokémon pode passar**
- **o item não passa para Gen 1**

Exemplo:

- Mew Gen 3 com Metal Coat -> Gen 1
  - Mew pode ser recebido
  - Metal Coat é removido

- Scyther Gen 3 com Metal Coat -> Gen 1
  - Scyther pode ser recebido se a species existir no destino
  - Metal Coat é removido

- Onix Gen 3 com Metal Coat -> Gen 1
  - Onix pode ser recebido
  - Metal Coat é removido

## Relação com evolução por item

Itens de evolução por troca atualmente suportados:

### Gen 2

- King's Rock
- Metal Coat
- Dragon Scale
- Up-Grade

Casos:

- Poliwhirl + King's Rock -> Politoed
- Slowpoke + King's Rock -> Slowking
- Onix + Metal Coat -> Steelix
- Scyther + Metal Coat -> Scizor
- Seadra + Dragon Scale -> Kingdra
- Porygon + Up-Grade -> Porygon2

### Gen 3

- King's Rock
- Metal Coat
- Dragon Scale
- Up-Grade
- Deep Sea Tooth
- Deep Sea Scale

Casos adicionais:

- Clamperl + Deep Sea Tooth -> Huntail
- Clamperl + Deep Sea Scale -> Gorebyss

## Limitações atuais

Hoje o projeto **não** possui:

- catálogo completo de todos os itens de Gen 1
- catálogo completo de todos os itens de Gen 2
- catálogo completo de todos os itens de Gen 3
- classificação completa por tipo de item
- política completa para berries, mail, key items, TMs/HMs e battle items em cross-generation

O que existe hoje é o subconjunto necessário para:

- held items relevantes
- equivalência Gen 2 <-> Gen 3
- remoção segura ao entrar em Gen 1
- evolução por item

## Próximos passos recomendados

Para fechar compatibilidade de itens de forma séria, o caminho correto é:

1. expandir o catálogo para todos os itens por geração
2. classificar cada item por categoria:
   - hold item
   - consumível
   - berry
   - key item
   - TM/HM
   - mail
   - evolução
3. definir regra por direção:
   - preserva
   - remove
   - bloqueia
   - mapeia por equivalente
4. adicionar testes por item ou por classe de item

## Resumo curto

Estado atual do projeto:

- Gen 1: não suporta held items
- Gen 2: 4 itens modelados
- Gen 3: 6 itens modelados
- Gen 2 <-> Gen 3: 4 equivalências preservadas
- Gen 3 -> Gen 2: Deep Sea Tooth e Deep Sea Scale são removidos
- Gen 2/3 -> Gen 1: todo held item é removido
