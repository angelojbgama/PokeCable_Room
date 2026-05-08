# Battle Visual Gen 2 Progress

Atualizado em 2026-05-08.

Objetivo: reproduzir a batalha da Gen 2 usando a referencia original do `pokecrystal`, sem misturar asset ou comportamento visual de outras geracoes.

## Fontes Originais

- [x] `reference/pret/pokecrystal/data/moves/animations.asm` como fonte dos scripts de golpe.
- [x] `reference/pret/pokecrystal/data/battle_anims/object_gfx.asm` como fonte dos tile sheets carregados por `BATTLE_ANIM_GFX_*`.
- [x] `reference/pret/pokecrystal/data/battle_anims/objects.asm` como fonte de `BATTLE_ANIM_OBJ_*`, frameset, funcao, paleta e gfx.
- [x] `reference/pret/pokecrystal/data/battle_anims/framesets.asm` como fonte da sequencia e duracao dos frames.
- [x] `reference/pret/pokecrystal/data/battle_anims/oam.asm` como fonte dos OAM composites.
- [x] `reference/pret/pokecrystal/gfx/pokemon/*/anim.asm` como fonte da ordem original dos front sprites de entrada.
- [x] `reference/pret/pokecrystal/gfx/pokemon/*/anim_idle.asm` como fonte da ordem original dos front sprites em idle.
- [x] `reference/pret/pokecrystal/engine/battle/core.asm` como fonte das coordenadas dos HUDs de HP.
- [x] `reference/pret/pokecrystal/engine/battle/menu.asm` como fonte das coordenadas do menu de comando.
- [x] `reference/pret/pokecrystal/gfx/battle/enemy_hp_bar_border.png` e `hp_exp_bar_border.png` como fonte visual dos healthboxes.
- [x] `reference/pret/pokecrystal/gfx/frames/1.png` como frame visual original para textbox/menu.
- [ ] `reference/pret/pokecrystal/engine/battle_anims/` ainda precisa ser convertido para movimentos de objeto, BG effects, shakes e callbacks.

## Implementado Neste Bloco

- [x] Gen 2 `gen2_anim_gfx` agora e tratado como tile sheet de batalha, nao como imagem completa.
- [x] O fallback de asset Gen 2 sem composite renderiza um tile/frame recortado da sheet.
- [x] O renderer continua usando OAM composites quando `animation-map.json` fornece frames vindos de `framesets.asm` e `oam.asm`.
- [x] O playback dos OAM composites passou a respeitar `duration_frames` por frame.
- [x] O CSS foi ajustado para permitir tile/frame recortado sem limite de `max-width`/`max-height`.
- [x] Testes cobrem recorte de tile sheet Gen 2, posicao de tile/OAM e duracao original de frameset.
- [x] Teste usa `animation-map.json` real para validar Thunderbolt com `BATTLE_ANIM_GFX_LIGHTNING`, OAM composite e duracoes do `pokecrystal`.
- [x] `effectVisualProfile` renderiza instancias reais de `anim_obj` da Gen 2 em vez de usar composites genericos por GFX.
- [x] Instancias Gen 2 preservam `args`, `callback`, `frameset`, `gfx`, `object` e OAM composite.
- [x] O renderer aplica movimento step-based nos OAM composites a partir de `BATTLE_ANIM_FUNC_*`.
- [x] Cobertura de callbacks Gen 2 nao nulos no `animation-map.json`: `483/483`.
- [x] Front sprites Gen 2 exportados como sheets verticais agora sao inferidos como `pokemon_front`.
- [x] Sheets `gen2/pokemon/*/front.png` com altura multipla da largura animam uma vez e retornam ao frame inicial.
- [x] Sequencias de front sprite Gen 2 sao extraidas do ASM original para `frontend/generated/battle-assets/gen2/pokemon-front-anim-sequences.json`.
- [x] O JSON contem `species` para `anim.asm` e `idle_species` para `anim_idle.asm`.
- [x] O parser expande `frame`, `setrepeat`, `dorepeat` e `endanim` seguindo a semantica de `engine/gfx/pic_animation.asm`.
- [x] O renderer carrega o JSON da Gen 2 e usa ordem/duracao real por especie antes de cair no fallback vertical.
- [x] Teste valida Ampharos contra `gfx/pokemon/ampharos/anim.asm`, incluindo repeticoes e retorno ao frame base.
- [x] Teste valida Ampharos contra `gfx/pokemon/ampharos/anim_idle.asm`, usando loop para idle.
- [x] Fundo base da Gen 2 foi ajustado para tilemap limpo em vez de gradiente moderno de ceu/grama.
- [x] Healthboxes Gen 2 agora usam os assets originais de borda e posicoes aproximadas das chamadas `hlcoord 1,0` e `hlcoord 9,7`.
- [x] Indicadores de party da Gen 2 passam a usar `gen2/ui/battle/balls.png`.
- [x] `GEN2_BATTLE_LAYOUT` centraliza coordenadas extraidas do ASM para screen, field, textbox, sprites, HUDs, HP, command menu, move menu e move info box.
- [x] CSS da Gen 2 consome variaveis calculadas de `GEN2_BATTLE_LAYOUT`, reduzindo posicionamento manual em porcentagem solta.
- [x] Sprites Gen 2 usam `hlcoord 12,0` para inimigo e `hlcoord 2,6` para jogador.
- [x] Menu de comando Gen 2 usa `menu_coords 8,12,19,17`.
- [x] Menu de golpes Gen 2 usa `hlcoord 4,12` e info box usa `hlcoord 0,8`, conforme `core.asm`.
- [x] HUD Gen 2 renderiza nome, nivel/status e HP como campos separados, permitindo posicionamento por tile.
- [x] `scripts/export_pret_battle_assets.py` agora exporta `gfx/frames` da Gen 2 para `frontend/generated/battle-assets/gen2/ui/frames`.
- [x] Textbox, command menu, move menu, move detail e confirm menu da Gen 2 usam `border-image` com `gen2/ui/frames/1.png`.
- [x] Gen 2 foi separado em `frontend/battle-scene-gen2.js` com perfil, assets, layout ASM e calculos proprios.
- [x] `battle-scene.js` passa a depender de `POKECABLE_BATTLE_SCENE_GEN2`/`require("./battle-scene-gen2.js")` para a Gen 2.
- [x] Barra de HP Gen 2 usa `ComputeHPBarPixels`: 6 tiles, 48 pixels, minimo de 1 pixel se HP atual for maior que zero.
- [x] Cor da barra de HP Gen 2 segue `GetHPPal`: verde em `>=24`, amarelo em `>=10`, vermelho abaixo disso.
- [x] Animacao visual da barra de HP Gen 2 usa `steps(48)` para casar com `HP_BAR_LENGTH_PX`.
- [x] Party balls Gen 2 usam coordenadas de `BattleStart_TrainerHuds`: inimigo em `ldpixel 9,4`, jogador em `ldpixel 12,12`.
- [x] Party balls Gen 2 usam gap de 8px e direcao reversa no inimigo, como `wPlaceBallsDirection = -TILE_WIDTH`.
- [x] Renderizacao de HUD, textbox, command menu, fight menu e run confirm da Gen 2 foi movida para `battle-scene-gen2.js`.
- [x] Textbox Gen 2 deixou de renderizar cabecalho moderno de turno/titulo; agora mostra apenas mensagem e prompt.
- [x] `battle-scene-gen2.js` gera timeline de animacao a partir da ordem real dos comandos ASM.
- [x] Timeline Gen 2 cobre `anim_wait`, `anim_obj`, `anim_bgeffect`, `anim_incobj`, `anim_setobj`, `anim_incbgeffect`, `anim_clearobjs`, `anim_sound`, `anim_cry`, `anim_*gfx`, `anim_oamon`, `anim_oamoff` e `anim_ret`.
- [x] `effectVisualProfile` usa duracao da timeline Gen 2 em vez de estimativa generica quando perfil vem da Gen 2.
- [x] Assets visuais de `anim_obj` Gen 2 recebem `startFrame`/`startMs` calculados pela timeline ASM.
- [x] Renderer aplica `--battle-effect-delay` para atrasar objetos Gen 2 ate o frame original do script.
- [x] `anim_bgeffect` Gen 2 expoe `backgroundStartFrame`/`backgroundStartMs` a partir da timeline ASM.
- [x] Renderer aplica `--battle-bg-effect-delay` para atrasar o background de efeito ate o frame original.
- [x] `anim_clearobjs` Gen 2 define `endFrame`/`endMs`/`durationMs` para encerrar objetos no frame de limpeza do ASM.
- [x] `anim_incobj` e `anim_setobj` normalizam IDs ASM 1-based para indices JS 0-based em `target_object_index`.
- [x] Assets visuais Gen 2 recebem `stateEvents` com frame, tempo, `objectId`, tipo e estado quando o script usa `anim_incobj`/`anim_setobj`.
- [x] `anim_incbgeffect` agora delimita `backgroundEndFrame`/`backgroundEndMs`/`backgroundDurationMs` quando corresponde ao primeiro BG effect ativo.
- [x] Eventos `anim_cry` passam a aparecer como tipo `cry` separado de `sound` na timeline.
- [x] `anim_obj` Gen 2 usa as coordenadas X/Y do ASM como `position` e CSS vars `--battle-effect-left/top`.
- [x] Container de efeito da Gen 2 ocupa o campo inteiro para permitir posicionamento por coordenada ASM.
- [x] Seletores de background effect foram corrigidos para aplicar regras Gen 2 a partir do container pai `.battle-scene-gen2`.

## Plano de Acao Gen 2

- [x] Tratar sheets grandes como conjuntos de tiles de 8x8.
- [x] Impedir que `gen2_anim_gfx` caia em renderizacao de imagem inteira.
- [x] Respeitar timing original de frameset nos composites.
- [x] Converter `BATTLE_ANIM_FUNC_*` presentes no `animation-map.json` para perfis JS de movimento por objeto.
- [ ] Refinar cada perfil `BATTLE_ANIM_FUNC_*` contra a rotina ASM linha a linha quando houver discrepancia visual.
- [x] Converter comandos principais de animacao em timeline visual por golpe.
- [ ] Aplicar paletas `PAL_BATTLE_OB_*` nos objetos Gen 2.
- [ ] Implementar BG effects da Gen 2 usando assets de `gfx/battle_anims/`.
- [ ] Refinar healthboxes Gen 2 por tile exato quando o renderer passar a trabalhar com matriz 20x18 completa.
- [x] Substituir bordas CSS dos textboxes/menus Gen 2 por tiles de frame originais quando exportados.
- [x] Separar renderer visual Gen 2 em modulo proprio para impedir que ajustes Gen 1/3 afetem o layout ASM.
- [x] Extrair renderizacao completa de HUD/textbox/menu Gen 2 para funcoes proprias no modulo Gen 2.
- [x] Fazer renderer consumir tempo da timeline Gen 2 para atrasar `anim_obj` ate o frame correto.
- [x] Fazer renderer consumir tempo da timeline Gen 2 para atrasar o primeiro `anim_bgeffect` ate o frame correto.
- [x] Fazer renderer consumir `anim_clearobjs` para limitar a duracao visual dos objetos ativos.
- [x] Normalizar `anim_incobj`/`anim_setobj` e anexar eventos de estado aos objetos visuais.
- [x] Usar `anim_incbgeffect` correspondente para definir duracao do background visual principal.
- [x] Posicionar objetos de efeito Gen 2 pelas coordenadas originais de `anim_obj`.
- [ ] Portar a semantica visual especifica de cada `BATTLE_ANIM_FUNC_*` que depende de `stateEvents`.
- [ ] Fazer renderer consumir semantica completa de multiplos BG effects simultaneos, som, cry e comandos de lifecycle restantes da timeline Gen 2.
- [ ] Validar golpes com varios objetos simultaneos, por exemplo Ember, Quick Attack e Thunderbolt.
- [x] Extrair sequencias exatas de animacao de front sprites da Gen 2 quando houver tabela ASM especifica alem da ordem vertical simples.
- [x] Extrair sequencias de idle dos front sprites da Gen 2 a partir de `anim_idle.asm`.
- [ ] Aplicar `animationKind: "idle"` nos contextos visuais corretos fora da entrada de batalha, por exemplo summary/menu quando o mesmo renderer for usado.
- [ ] Validar multi-hit, charge, drain, recoil, status e faint com saves reais.
- [ ] Separar o pipeline visual Gen 2 em arquivo proprio quando o interpretador estiver estavel.

## Validacao

- [x] `python3 scripts/extract_pokecrystal_front_anim_sequences.py` gerou 278 animacoes de front sprite e 278 animacoes idle da Gen 2.
- [x] `node PokeCable/frontend/tests/test_battle_scene.js` com 40 testes passando.
- [x] Teste valida coordenadas do layout Gen 2 contra `pokecrystal` ASM.
- [x] Teste valida variaveis CSS derivadas das coordenadas ASM da Gen 2.
- [x] Teste valida `ComputeHPBarPixels` e thresholds de `GetHPPal` da Gen 2.
- [x] Teste valida coordenadas ASM dos party balls da Gen 2.
- [x] Teste valida que HUD/textbox Gen 2 sao renderizados pelo modulo isolado.
- [x] Teste valida timeline de Thunderbolt: ordem de comandos, waits `[16,64,64]`, BG effect no frame 16 e `anim_ret` no frame 144.
- [x] Teste valida que assets de `anim_obj` da Gen 2 recebem `startFrame`/`startMs` da timeline ASM.
- [x] Teste valida que Thunderbolt deriva `backgroundStartFrame`/`backgroundStartMs` do `anim_bgeffect` no frame 16.
- [x] Teste valida que Bubblebeam usa `anim_clearobjs` para encerrar objetos no frame 84.
- [x] Teste valida que Ember normaliza `anim_incobj` para objetos 0, 1 e 2 no frame 24.
- [x] Teste valida que Jump Kick normaliza `anim_setobj` para estado 2 nos objetos 0 e 1.
- [x] Teste valida que Acid Armor usa `anim_incbgeffect` para encerrar o BG effect no frame 64.
- [x] Teste valida que Thunderbolt e Bubblebeam usam coordenadas X/Y de `anim_obj` para `position`.
- [x] Manifest contem `gen2/ui/frames/1.png` a `9.png` e `map_entry_sign.png` exportados de `gfx/frames`.
- [x] Teste falha se algum callback Gen 2 nao nulo do `animation-map.json` ficar sem perfil JS.
- [x] Teste falha se front sprite Gen 2 vertical voltar a ser tratado como imagem estatica.
- [x] Teste falha se a ordem extraida do ASM para Ampharos deixar de ser usada pelo renderer.
- [x] Teste falha se a ordem idle extraida do ASM para Ampharos deixar de ser usada pelo renderer.
- [x] Teste valida que o perfil de UI da Gen 2 expoe `balls.png`, `enemy_hp_bar_border.png` e `hp_exp_bar_border.png`.
- [ ] Teste visual automatizado carregando save real Gen 2 e comparando baseline de eventos/txt.
- [ ] Baseline visual de golpes Gen 2 revisado contra comportamento do jogo original.
