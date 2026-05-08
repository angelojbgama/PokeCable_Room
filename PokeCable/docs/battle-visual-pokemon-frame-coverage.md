# Battle Visual Pokemon Frame Coverage

Este arquivo registra a cobertura atual de sprites de Pokemon usados pelo frontend de batalha.

Fonte:

- `frontend/generated/battle-assets/manifest.json`
- Gen 3 front animations: `reference/pret/pokeemerald/src/data/pokemon_graphics/front_pic_anims.h`
- Gen 3 animation runtime: `reference/pret/pokeemerald/src/pokemon_animation.c`
- Extrator: `scripts/extract_pokeemerald_front_anim_sequences.py`
- JSON gerado: `frontend/generated/battle-assets/gen3/pokemon-front-anim-sequences.json`

## Estado Atual

| Gen | Species records | Front | Back | Anim front | Frameados ativos |
| --- | ---: | ---: | ---: | ---: | ---: |
| Gen 1 | 153 | 153 | 151 | 0 | 0 |
| Gen 2 | 277 | 277 | 276 | 0 | 0 |
| Gen 3 | 385 | 385 | 384 | 385 | 385 |

## Politica do Renderer

- Gen 1 usa `front` para o oponente e `back` para o jogador.
- Gen 2 usa `front` para o oponente e `back` para o jogador.
- Gen 3 usa `anim_front` para o oponente quando existir.
- Gen 3 usa `back` para o jogador quando existir.
- Se um sprite local existir, o renderer nao deve usar sprite externo.
- Fallback externo so e aceitavel quando nenhum asset local foi exportado para aquela species.

## Animacao de Frames

- Sprites com `frame.count > 1` sao renderizados como sprite sheet.
- Sprites de Pokemon com layout `pokemon_front` usam playback finito.
- O playback de Gen 3 `anim_front` usa sequencia e duracao extraidas de `front_pic_anims.h`.
- Exemplo: Pikachu usa `0 -> 1 -> 0 -> 1 -> 0`, com duracoes `250, 333, 250, 333, 250ms`.
- O renderer tambem carrega o `motion` por species a partir de `sMonFrontAnimIdsTable` em `pokemon.c`.
- Assets de efeito de golpe continuam podendo usar loop quando o efeito visual pede repeticao.

## Exemplos Gen 3 com `anim_front`

- `abra`
- `absol`
- `aerodactyl`
- `aggron`
- `aipom`
- `alakazam`
- `altaria`
- `ampharos`
- `anorith`
- `arbok`
- `arcanine`
- `ariados`

## Pendencias

- [x] Extrair sequencias exatas por species de `front_pic_anims.h`.
- [x] Aplicar duracoes exatas dos `ANIMCMD_FRAME` por species.
- [x] Completar mapeamento dos `ANIM_*` usados pelos front sprites da Gen 3.
- [ ] Completar mapeamento dos `BACK_ANIM_*` usados pelos back sprites da Gen 3.
- [ ] Mapear back animations da Gen 3 por species.
- [ ] Mapear shiny/gender/forms quando o save indicar variante e o asset existir.

## Progresso de Movimento JS

Cobertura atual:

- Front sprite Gen 3: `62/62` motions extraidos do `sMonFrontAnimIdsTable`.
- O teste `covers every front pokemon motion extracted from pokeemerald` falha se um motion usado por species ficar sem perfil JS.

- [x] `ANIM_V_JUMPS_H_JUMPS`
- [x] `ANIM_V_SQUISH_AND_BOUNCE`
- [x] `ANIM_H_VIBRATE`
- [x] `ANIM_H_SHAKE`
- [x] `ANIM_V_SHAKE`
- [x] `ANIM_H_SLIDE`
- [x] `ANIM_V_SLIDE`
- [x] `ANIM_ROTATE_*`
- [x] `ANIM_PIVOT_*`
- [x] `ANIM_GROW_*`
- [x] `ANIM_FLASH_*`
- [x] `ANIM_GLOW_*`
- [x] `ANIM_SWING_*`
- [x] `ANIM_CONCAVE_*`
- [x] `ANIM_CONVEX_*`
- [x] `ANIM_TRIANGLE_*`
- [x] `ANIM_TWIST*`
- [x] `ANIM_SPIN*`
- [x] `ANIM_FLIP*`
- [x] `ANIM_FIGURE_8`
- [x] `ANIM_CIRCLE_*`
- [x] `ANIM_SPRING*`
- [x] `ANIM_ZIGZAG_*`
- [x] `ANIM_WOBBLE*`
- [x] `ANIM_STRETCH*`
- [x] `ANIM_SHRINK_GROW*`
- [x] `ANIM_LUNGE*`
- [x] `ANIM_TIP*`
- [x] `ANIM_FLICKER*`
- [x] `ANIM_H_HOPS`
