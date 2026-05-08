# Battle Visual Checklist

Este documento e o backlog operacional para fechar o frontend de batalha com fidelidade ao jogo original.

Regras de trabalho:

- Cada gen deve manter visual, assets e animacao proprios.
- A logica visual deve vir das referencias originais em assembly sempre que possivel.
- CSS deve servir para layout, recorte e fallback minimo.
- Arte de batalha deve vir de assets exportados do jogo original.
- Animacoes devem ser frame-based em JavaScript, nao CSS genérico.
- Sprites de Pokemon em frames devem ser usados quando o asset existir.
- Nada de compartilhamento de logica visual entre Gens 1, 2 e 3.

Referencias locais:

- Gen 1: `reference/pret/pokered`
- Gen 2: `reference/pret/pokecrystal`
- Gen 3: `reference/pret/pokeemerald`
- Assets exportados: `frontend/generated/battle-assets/`
- Renderer: `frontend/battle-scene.js`
- Estilo base: `frontend/styles.css`
- Progresso Gen 2: `docs/battle-visual-gen2-progress.md`

## 1. Diretrizes Gerais

- [ ] Garantir que o renderer de batalha opere com pipelines separados por geracao.
- [ ] Garantir que a camada visual nao reutilize assets errados entre Gens 1/2/3.
- [ ] Manter o layout com escala pixelada e alinhamento em grid quando possivel.
- [x] Usar fontes sprite originais para texto de batalha, menus e labels.
- [ ] Usar logs da engine como fonte de verdade para estados e eventos.
- [ ] Manter fallback visual simples apenas quando o asset original nao existir.
- [ ] Registrar no guia visual quando um elemento nao tiver equivalente exportado.

## 2. Fontes de Verdade por Jogo

- [ ] Mapear os scripts de batalha do jogo original para cada gen.
- [ ] Usar a ordem de comandos original para reproduzir o ritmo da batalha.
- [ ] Traduzir comandos originais para eventos de frontend sem mudar a semantica.
- [ ] Revalidar cada mudanca com saves reais.
- [ ] Manter textos e mensagens alinhados com a charmap original.
- [ ] Evitar misturar heuristica moderna com comportamento original.

## 3. Sprites de Pokemon em Frames

- [x] Usar `front`, `back` e `anim_front` quando existirem nos assets exportados.
- [x] Detectar sprites com multiplos frames via metadata do manifest.
- [x] Renderizar animacoes de Pokemon com frame plan baseado em sprite sheet.
- [x] Usar animacoes de entrada por species quando o jogo original tiver frames.
- [x] Usar sequencias e duracoes reais da Gen 3 extraidas de `front_pic_anims.h`.
- [x] Completar mapeamento JS dos movimentos `ANIM_*` usados pelos front sprites da Gen 3.
- [ ] Suportar variantes de genero, shiny e formas separadas quando existirem.
- [x] Evitar fallback para sprites externos quando o asset local existir.
- [x] Documentar por species quais animacoes estao completas e quais faltam.

Status:

- Gen 3 `anim_front` usa playback finito com sequencia e duracao reais de `reference/pret/pokeemerald/src/data/pokemon_graphics/front_pic_anims.h`.
- Efeitos de golpe continuam em loop quando o asset de efeito pede repeticao; sprites de Pokemon nao ficam mais alternando frames indefinidamente.
- Cobertura registrada em `docs/battle-visual-pokemon-frame-coverage.md`.
- `frontend/generated/battle-assets/gen3/pokemon-front-anim-sequences.json` e gerado de `pokeemerald` e fornece sequencia, duracao e motion por species.
- O renderer ja usa essas duracoes reais quando o JSON esta carregado; o fallback generico fica apenas para assets sem entrada mapeada.
- Front sprite Gen 3 tem cobertura `62/62` motions; o teste do renderer falha se novo motion extraido ficar sem perfil JS.
- Gen 2 agora tambem carrega `frontend/generated/battle-assets/gen2/pokemon-front-anim-sequences.json`, extraido de `reference/pret/pokecrystal/gfx/pokemon/*/anim.asm` e `anim_idle.asm`.
- Front sprite Gen 2 usa ordem e duracao reais do ASM; fallback vertical simples fica apenas para species sem entrada gerada.
- O JSON da Gen 2 separa entrada em `species` e idle em `idle_species`.

## 4. Animacoes de Golpes

- [ ] Converter os scripts originais de animacao em familias JS.
- [ ] Reproduzir timing, espera, flashes e shakes com steps.
- [ ] Usar assets originais de efeito por frame.
- [ ] Reproduzir backgrounds de efeito quando o jogo original fornecer esse asset.
- [ ] Reproduzir objetos temporarios sobre o alvo com duracao correta.
- [ ] Tratar golpes multi-hit como sequencia de frames e nao como um unico flash.
- [ ] Tratar golpes de carga, recoil, drain e prioridade visual com estados proprios.

Status Gen 2:

- [x] `gen2_anim_gfx` usa recorte de tile/frame de 8x8 e nao renderiza a sheet inteira.
- [x] OAM composites da Gen 2 usam tiles recortados de `battle_anims/`.
- [x] Duracao de frame dos composites respeita `duration_frames` extraido dos framesets do `pokecrystal`.
- [x] Thunderbolt Gen 2 e validado contra `animation-map.json` real com `BATTLE_ANIM_GFX_LIGHTNING`.
- [x] `anim_obj` Gen 2 renderiza instancias reais com `args`, `callback`, `frameset`, `gfx`, `object` e OAM composite.
- [x] Callbacks Gen 2 nao nulos presentes no `animation-map.json` possuem perfil JS de movimento: `483/483`.
- [x] Fundo base Gen 2 ajustado para superficie limpa/tilemap, sem gradiente moderno de cenario.
- [x] Healthboxes Gen 2 usam `enemy_hp_bar_border.png` e `hp_exp_bar_border.png` como asset visual principal.
- [x] Layout visual Gen 2 tem tabela central `GEN2_BATTLE_LAYOUT` com coordenadas do ASM.
- [x] Sprites, HUDs, textbox, command menu, move menu e move info box da Gen 2 usam coordenadas derivadas de `hlcoord`/`menu_coords`.
- [x] Textboxes e menus Gen 2 usam `gfx/frames/1.png` exportado como `gen2/ui/frames/1.png`.
- [x] Perfil/layout/assets Gen 2 ficam em `frontend/battle-scene-gen2.js`.
- [x] Barra de HP Gen 2 usa 48 pixels e thresholds originais de `GetHPPal`.
- [x] Party balls Gen 2 usam `ldpixel 9,4` e `ldpixel 12,12` de `trainer_huds.asm`.
- [x] HUD, textbox, command menu, fight menu e run confirm da Gen 2 sao renderizados por `battle-scene-gen2.js`.
- [x] Timeline de animacao Gen 2 preserva ordem e waits dos comandos de `data/moves/animations.asm`.
- [x] Objetos `anim_obj` Gen 2 recebem delay visual baseado no frame original da timeline ASM.
- [x] Primeiro `anim_bgeffect` Gen 2 recebe delay visual baseado no frame original da timeline ASM.
- [x] `anim_clearobjs` Gen 2 encerra objetos ativos no frame original da timeline ASM.
- [x] `anim_incobj` e `anim_setobj` Gen 2 normalizam ID ASM para indice JS e alimentam `stateEvents` nos objetos visuais.
- [x] `anim_incbgeffect` Gen 2 delimita a duracao do background visual principal quando corresponde ao efeito ativo.
- [x] Objetos de efeito Gen 2 usam coordenadas X/Y de `anim_obj` em vez de posicoes genericas por `nth-child`.
- [ ] Falta refinar callbacks contra ASM linha a linha, converter semantica completa de multiplos BG effects, paletas e comandos de lifecycle restantes para JS.

## 5. Backgrounds e Camadas de Campo

- [ ] Manter fallback de campo para Gen 1 quando nao houver arte exportada de fundo.
- [ ] Usar backgrounds originais de efeito da Gen 2 quando a animacao pedir.
- [ ] Usar backgrounds originais de efeito da Gen 3 quando a animacao pedir.
- [ ] Evitar inventar fundo persistente se o jogo original nao exportou esse campo.
- [ ] Registrar em doc quais backgrounds sao persistentes e quais sao de efeito.
- [ ] Revalidar camadas com testes de renderer.

## 6. Gen 1

- [ ] Conferir HUD monocromatico com tiles originais.
- [ ] Conferir caixa de texto no estilo Game Boy classico.
- [ ] Conferir menu 2x2 com cursor simples.
- [ ] Conferir menu de golpes com PP e estado desabilitado.
- [ ] Conferir party menu simples e status de faint.
- [ ] Conferir mochila simples em lista.
- [ ] Conferir sprites de front/back no estilo da Gen 1.
- [ ] Conferir animacoes por golpes usando a logica original do jogo.
- [ ] Conferir batalha com saves reais ate exaustao.

## 7. Gen 2

- [x] Conferir HUD colorido de GBC com bordas originais.
- [x] Aplicar assets originais nos boxes de nome/HP da Gen 2.
- [x] Remover aparencia moderna de ceu/grama do fundo base da batalha Gen 2.
- [x] Conferir caixa de texto Gen 2 na posicao original `hlcoord 0,12`.
- [x] Conferir menu principal Gen 2 na posicao original `menu_coords 8,12,19,17`.
- [x] Conferir menu de golpes Gen 2 em `hlcoord 4,12` com info box em `hlcoord 0,8`.
- [x] Conferir bordas de textbox/menu Gen 2 com frame original de `gfx/frames`.
- [ ] Conferir pack/pocket visual da Gen 2.
- [ ] Conferir party menu com icones, HP bar e status.
- [x] Conferir sprites coloridos por especie com front sheets verticais animados.
- [x] Conferir ordem original dos front sprites Gen 2 extraida de `gfx/pokemon/*/anim.asm`.
- [x] Conferir ordem idle dos front sprites Gen 2 extraida de `gfx/pokemon/*/anim_idle.asm`.
- [ ] Conferir efeitos de batalha com assets de `battle_anims/`.
- [ ] Conferir batalha com saves reais ate exaustao.

Plano atual Gen 2:

- [x] Mapear `object_gfx.asm`, `objects.asm`, `framesets.asm` e `oam.asm`.
- [x] Renderizar frames de sheets grandes como tiles recortados.
- [x] Testar recorte de tile sheet, OAM tile style e duracao por frameset.
- [x] Testar metadata real de OAM composite da Gen 2 em golpe do `pokecrystal`.
- [x] Criar primeira camada JS para objetos `anim_obj` da Gen 2.
- [x] Implementar movimentos por objeto a partir de `BATTLE_ANIM_FUNC_*` cobertos pelo mapa atual.
- [x] Corrigir `front.png` Gen 2 exportado como sheet vertical para tocar como sprite em frames.
- [x] Extrair e consumir sequencias reais de front sprite Gen 2 do ASM original.
- [x] Extrair e consumir sequencias reais de idle front sprite Gen 2 do ASM original.
- [x] Ajustar background e healthboxes Gen 2 contra `core.asm` e `gfx/battle/`.
- [x] Refatorar layout Gen 2 para coordenadas ASM centralizadas e testadas.
- [x] Exportar e usar frames originais da Gen 2 para textboxes/menus.
- [x] Separar perfil/layout/assets Gen 2 em modulo proprio.
- [x] Implementar calculo visual de HP Gen 2 como `ComputeHPBarPixels`/`GetHPPal`.
- [x] Corrigir party balls Gen 2 contra `BattleStart_TrainerHuds`.
- [x] Mover renderizacao de HUD/textbox/menu Gen 2 para modulo isolado.
- [x] Criar timeline Gen 2 baseada em comandos ASM.
- [x] Aplicar timing da timeline ASM aos objetos `anim_obj` da Gen 2.
- [x] Aplicar timing da timeline ASM ao primeiro `anim_bgeffect` da Gen 2.
- [x] Aplicar `anim_clearobjs` da timeline ASM como fim da duracao visual dos objetos ativos.
- [x] Normalizar e anexar `anim_incobj`/`anim_setobj` aos objetos visuais como eventos de estado.
- [x] Usar `anim_incbgeffect` para finalizar/delimitar o primeiro BG effect visual.
- [x] Trocar posicionamento de objetos Gen 2 para coordenadas reais dos argumentos de `anim_obj`.
- [ ] Expandir consumo da timeline Gen 2 para multiplos BG effects simultaneos, som/cry e interpretacao callback-specific dos eventos inc/set object.
- [ ] Comparar efeitos de golpes com saves reais e baseline txt.

## 8. Gen 3

- [ ] Conferir healthboxes singles e doubles com assets originais.
- [ ] Conferir textbox GBA com layout correto.
- [ ] Conferir menu 2x2 com visual do Emerald/Ruby/Sapphire.
- [ ] Conferir move menu com PP, tipo e estado de bloqueio.
- [ ] Conferir party menu e bag com visual de GBA.
- [ ] Conferir status badges, numeros e HP bar originais.
- [ ] Conferir backgrounds de efeito de batalha da Gen 3.
- [ ] Conferir animacoes de golpes com scripts e frames originais.
- [ ] Conferir sprites de Pokemon com `front`, `back` e `anim_front`.
- [ ] Conferir doubles e redirecionamento visual.
- [ ] Conferir batalha com saves reais ate exaustao.

## 9. Integracao com Engine

- [ ] Garantir que cada visual responda ao evento certo do log de batalha.
- [ ] Garantir que status, recoil, drain, miss e faint tenham feedback visual.
- [ ] Garantir que switch e forced switch tenham animacao correta.
- [ ] Garantir que victory/defeat congelem a cena corretamente.
- [ ] Garantir que requests de turno atualizem menus e alvo.
- [ ] Garantir que o renderer nao dependa de compartilhamento de estado entre gens.

## 10. Testes e Validacao

- [ ] Manter testes unitarios do renderer por geracao.
- [x] Manter testes de assets e resolucao de sprites/frames.
- [x] Manter teste de cobertura dos callbacks de objeto Gen 2.
- [x] Manter teste de inferencia de front sprite Gen 2 em sheet vertical.
- [x] Manter teste de ordem original de front sprite Gen 2 extraida do ASM.
- [x] Manter teste de ordem idle de front sprite Gen 2 extraida do ASM.
- [ ] Manter testes de efeitos de background por geracao.
- [ ] Manter testes com saves reais para cada gen.
- [ ] Gerar txts de batalha para comparar baseline visual e logico.
- [ ] Revisar regressions sempre que um novo save expuser divergencia.
- [ ] Fechar somente quando a suite de validacao estiver verde.

## 11. Entregas Pendentes de Maior Impacto

- [ ] Converter menus e caixas restantes para molduras e tiles originais sempre que o asset existir.
- [x] Melhorar sprites de Pokemon em frames para efeitos de entrada e animacao.
- [ ] Expandir a interpretacao de animacoes de golpe do assembly para JavaScript.
- [ ] Cobrir mais casos raros de background e status por geracao.
- [ ] Documentar cada bloco concluido no guia visual e nos progress notes.

Status:

- Party e bag renderizam nomes, quantidades, HP numerico e textos vazios com fonte sprite da geracao.
- Chamada `x` grafica foi ajustada para o glyph `×` nas Gens 1, 2 e 3.
- Gen 3 bag art usa `gen3/ui/battle_anims/sprites/item_bag.png` como asset original em vez de desenho CSS.

## 12. Definicao de Completo

- [ ] Gen 1 visual validado com saves reais e baseline limpo.
- [ ] Gen 2 visual validado com saves reais e baseline limpo.
- [ ] Gen 3 visual validado com saves reais e baseline limpo.
- [ ] Cada gen usa apenas seus proprios assets visuais.
- [ ] Sprites em frames estao ativos onde os assets existirem.
- [ ] Animacoes derivadas do assembly estao convertidas para JS.
- [ ] A documentacao reflete o estado real da implementacao.
