# Guia visual das batalhas por geração

Este documento define como o frontend do PokeCable deve reproduzir a aparência de batalha das Gens 1, 2 e 3. O objetivo é orientar a implementação do renderer no navegador para parecer nativo de cada jogo, mantendo as engines Python isoladas por geração.

Para a ordem de execucao e controle de pendencias, use tambem:

- `docs/battle-visual-checklist.md`
- `docs/battle-visual-pokemon-frame-coverage.md`

Referências locais principais:

- Gen 1: `reference/pret/pokered`
- Gen 2: `reference/pret/pokecrystal`
- Gen 3: `reference/pret/pokeemerald`
- Assets exportados: `PokeCable/frontend/generated/battle-assets/`
- Renderer atual: `PokeCable/frontend/battle-scene.js`

Essas referências foram clonadas localmente dentro de `PokeCable/reference/pret/` para consulta offline durante a implementação do frontend.

O renderer da batalha deve ser orientado por assets:

- CSS fica responsável por layout, recorte e posicionamento.
- Elementos visuais de batalha devem vir dos assets exportados do jogo original sempre que existirem.
- Imagens com `frame.count > 1` são animadas no browser por JavaScript com base no metadata do manifest.
- Os scripts de batalha originais servem como referência para a ordem e o tipo das animações, não para recriar a arte em CSS.
- Textos de batalha e rótulos devem preferir fontes sprite exportadas do jogo original:
  - Gens 1/2 usam `font.png` do pacote exportado.
  - Gen 3 usa `latin_short.png` exportado do `pokeemerald`.
- CSS deve ficar restrito a:
  - layout
  - recorte
  - posicionamento
  - estado visual mínimo de fallback
- Quando houver asset original de background para um efeito de batalha:
  - usar a imagem exportada do jogo como camada visual principal
  - manter o fundo-base do renderer apenas como fallback
  - não inventar backdrop persistente quando o jogo original não exportou esse campo

## Regras gerais para todas as gerações

- A cena de batalha deve ser renderizada em proporção fixa equivalente à tela do jogo:
  - Gen 1/2: base mental de Game Boy, 160x144 px, tile grid 20x18, tiles de 8x8.
  - Gen 3: base mental de Game Boy Advance, 240x160 px, tiles de 8x8, sprites 4bpp.
- O frontend pode escalar a cena, mas o conteúdo interno deve usar `image-rendering: pixelated`.
- Textos, barras, sprites e menus devem alinhar em grid de 8 px sempre que possível.
- Não misturar estilos entre gerações:
  - Gen 1 não usa paleta colorida rica nem mochila por bolsos.
  - Gen 2 não usa healthboxes arredondadas de GBA.
  - Gen 3 não usa caixa monocromática simples de Game Boy.
- O renderer deve consumir logs da engine:
  - `|switch|` atualiza sprite, nome, nível e HP.
  - `|move|` toca animação de golpe.
  - `|damage|` / `|-damage|` atualiza barra de HP e anima impacto.
  - `|heal|` / `|-heal|` atualiza HP e anima cura.
  - `|-status|` / `|status|` atualiza badge/status.
  - `|faint|` executa animação de queda/desaparecimento.
  - `|win|` congela cena com mensagem final.
- A janela de texto deve ser a superfície principal de narrativa. Botões HTML do site podem existir, mas a primeira camada visual deve imitar o menu do jogo.

## Gen 1: Red, Blue, Yellow

### Identidade visual

- Aparência monocromática ou quase monocromática.
- A experiência deve lembrar Game Boy clássico:
  - Fundo limpo.
  - Alto contraste.
  - Pouca ornamentação.
  - Textos grandes em fonte bitmap.
  - Animações curtas e rígidas.
- Em Super Game Boy ou paletas customizadas poderia haver cor, mas o padrão visual do renderer deve ser preto/branco/cinza para Gen 1.
- O visual deve parecer mais “tilemap” do que “interface moderna”.

### Área de batalha

- Tela baseada em 20 colunas x 18 linhas de tiles.
- O inimigo fica no quadrante superior direito.
- O Pokémon do jogador fica no quadrante inferior esquerdo.
- O fundo do campo é quase vazio:
  - Sem cenário detalhado.
  - Sem chão colorido.
  - Plataformas simples ou ausentes dependendo do estado.
- A introdução original usa silhuetas/deslizamento:
  - O jogador e o inimigo entram com scroll lateral.
  - No site, a entrada mínima aceitável é sprite deslizando ou aparecendo em steps.
  - Referência: `reference/pret/pokered/engine/battle/core.asm`.

### Sprites de Pokémon

- Front sprites e back sprites separados:
  - Front: `reference/pret/pokered/gfx/pokemon/front/`
  - Back: `reference/pret/pokered/gfx/pokemon/back/`
- Back sprites têm sufixo `b` no nome original.
- Sprites devem ser desenhados pixelados, sem antialias.
- Não aplicar sombras suaves.
- Escala deve preservar blocos grandes de pixel.
- O Pokémon do jogador pode parecer mais “ampliado”/recortado por causa do estilo de back sprite da Gen 1.

### HUD de HP

- O HUD é formado por tiles e cantos simples.
- Referência de tiles:
  - `reference/pret/pokered/gfx/battle/battle_hud_1.png`
  - `reference/pret/pokered/gfx/battle/battle_hud_2.png`
  - `reference/pret/pokered/gfx/battle/battle_hud_3.png`
  - `reference/pret/pokered/engine/battle/draw_hud_pokeball_gfx.asm`
- Inimigo:
  - HUD na parte superior esquerda ou próximo ao topo.
  - Nome em caixa alta.
  - Barra de HP visível.
  - HP numérico do inimigo não deve ser exibido em batalha normal.
- Jogador:
  - HUD na metade inferior direita.
  - Nome, nível, barra de HP e HP numérico.
  - HP deve aparecer como `current/max`.
- Indicadores de party:
  - Pokébolas pequenas representam time.
  - Bola normal: Pokémon vivo sem status.
  - Bola marcada/escura: status ou faint conforme tiles originais.
  - Referência: `DrawAllPokeballs`, `SetupOwnPartyPokeballs`, `SetupEnemyPartyPokeballs`.

### Caixa de texto

- Caixa na parte inferior da tela.
- Bordas simples.
- Fundo claro, texto escuro.
- Fonte bitmap, maiúsculas quando o jogo original usa maiúsculas.
- Mensagens aparecem linha por linha.
- Deve haver pausa visual entre mensagens importantes:
  - Pokémon entrou.
  - Pokémon usou golpe.
  - É super efetivo.
  - Não é muito efetivo.
  - Pokémon caiu.
- Referências:
  - `reference/pret/pokered/home/textbox.asm`
  - `reference/pret/pokered/engine/battle/used_move_text.asm`
  - `reference/pret/pokered/engine/battle/common_text.asm`

### Menu principal de batalha

- Menu 2x2 na área inferior direita ou sobre a caixa inferior.
- Opções:
  - `FIGHT`
  - `PKMN`
  - `ITEM`
  - `RUN`
- Em link battle, `RUN` pode ser substituído ou tratado como desistência conforme regra do projeto, mas visualmente deve ocupar o slot inferior direito.
- Cursor deve ser uma seta/triângulo simples à esquerda da opção.
- Navegação visual:
  - Cima/baixo/esquerda/direita.
  - Sem hover moderno.
  - Seleção com cursor piscando ou estático.
- Botões HTML devem mapear para esse layout visual, não para uma lista moderna.

### Menu de golpes

- Quatro golpes listados em área de menu.
- Deve mostrar:
  - Nome do golpe.
  - PP atual e PP máximo.
  - Tipo do golpe pode aparecer no painel de detalhe conforme layout usado.
- Estilo monocromático.
- Golpes desabilitados:
  - Devem ficar visualmente apagados.
  - Cursor não deve parar neles.
- Se não há PP:
  - Mostrar ou selecionar `STRUGGLE` conforme engine.

### Mochila e itens em batalha

- Gen 1 não tem bolsos separados no estilo Gen 2/3.
- A mochila é uma lista simples de itens.
- Visual esperado:
  - Janela retangular simples.
  - Lista vertical.
  - Quantidade à direita quando aplicável.
  - Cursor à esquerda.
  - Opção de cancelar no final.
- Tipos de item em batalha:
  - Poké Balls em wild battle.
  - Potions/healing.
  - Status heal.
  - X items.
  - Poké Flute.
  - Itens inválidos devem exibir mensagem de falha.
- Em batalha online/link do PokeCable:
  - Captura pode ser bloqueada se não fizer sentido.
  - O menu visual ainda deve parecer Gen 1.
- Referências:
  - `reference/pret/pokered/engine/items/inventory.asm`
  - `reference/pret/pokered/engine/items/item_effects.asm`
  - `reference/pret/pokered/data/items/names.asm`

### Party menu

- Lista dos Pokémon do jogador.
- Estilo monocromático.
- Cada entrada deve mostrar:
  - Ícone pequeno ou marcador.
  - Nome.
  - HP/status.
  - Nível.
- Pokémon fainted deve ficar visualmente indisponível.
- Ao tentar trocar:
  - Active Pokémon deve ser marcado.
  - Pokémon fainted não pode ser escolhido.
  - Se está preso por mecânica da engine, mostrar mensagem na caixa de texto.
- Referência:
  - `reference/pret/pokered/engine/menus/party_menu.asm`
  - `reference/pret/pokered/data/pokemon/menu_icons.asm`

### Animações de golpes

- Animações simples, curtas e baseadas em subanimações.
- Muitas são combinação de:
  - Impact star.
  - Flash de tela.
  - Shake de HUD/sprite.
  - Pequenos objetos de fogo/água/elétrico.
- Referência:
  - `reference/pret/pokered/data/moves/animations.asm`
  - `reference/pret/pokered/engine/battle/animations.asm`
- No renderer:
  - Cada golpe deve consultar `animation-map.json`.
  - A família visual inferida deve ser refinada com comandos reais.
  - O tempo deve ser step-based, não smooth CSS contínuo.

## Gen 2: Gold, Silver, Crystal

### Identidade visual

- Aparência Game Boy Color.
- Mais cor e mais organização que Gen 1.
- Ainda usa tile grid e caixas simples.
- Crystal tem animações e refinamentos mais ricos que Gold/Silver.
- A UI continua rígida, com textos e menus tile-based.

### Área de batalha

- Base visual 160x144.
- Inimigo no superior direito.
- Jogador no inferior esquerdo.
- Coordenadas visuais devem ser derivadas de `GEN2_BATTLE_LAYOUT`, que espelha `hlcoord` e `menu_coords` do ASM.
- Posições principais:
  - Inimigo front sprite: `hlcoord 12, 0`.
  - Jogador back sprite: `hlcoord 2, 6`.
  - Textbox: `hlcoord 0, 12`.
  - Command menu: `menu_coords 8, 12, 19, 17`.
  - Move menu: `hlcoord 4, 12`.
  - Move info box: `hlcoord 0, 8`.
- Campo ainda é relativamente limpo, com paletas mais ricas que Gen 1.
- A batalha normal não deve parecer um cenário moderno com céu e grama em gradiente.
- O fundo base deve parecer uma superfície/tilemap limpo de GBC.
- Plataformas devem ser discretas e tile-like, não elipses suaves modernas.
- Backgrounds detalhados devem aparecer principalmente quando um efeito de golpe pedir `battle_anims/*`.
- Referências:
  - `reference/pret/pokecrystal/engine/battle/start_battle.asm`
  - `reference/pret/pokecrystal/engine/battle/sliding_intro.asm`
  - `reference/pret/pokecrystal/gfx/battle/`
- Efeitos de background da batalha:
  - `reference/pret/pokecrystal/gfx/battle_anims/`
  - em especial `sand.png`, `water.png`, `shine.png`, `lightning.png`, `psychic.png`
- Progresso operacional:
  - `docs/battle-visual-gen2-progress.md`

### Sprites de Pokémon

- Estrutura por pasta:
  - `reference/pret/pokecrystal/gfx/pokemon/<species>/front.png`
  - `reference/pret/pokecrystal/gfx/pokemon/<species>/back.png`
- Sprites são coloridos.
- Crystal tem animações de entrada/frontpic.
- O frontend deve manter:
  - Sprite front do oponente.
  - Sprite back do jogador.
  - Pixelated.
  - Sem filtros modernos.
- Regra de front sprite exportado:
  - Alguns `gen2/pokemon/*/front.png` sao sheets verticais com varios frames.
  - Quando a altura for multipla da largura e o manifest marcar como `static`, o renderer deve inferir `pokemon_front`.
  - A ordem e a duracao devem vir de `frontend/generated/battle-assets/gen2/pokemon-front-anim-sequences.json`.
  - Esse JSON e extraido de `reference/pret/pokecrystal/gfx/pokemon/*/anim.asm` e `anim_idle.asm`, com `frame`, `setrepeat`, `dorepeat` e `endanim`.
  - `species` representa a animacao de entrada de `anim.asm`.
  - `idle_species` representa a animacao idle de `anim_idle.asm`.
  - O playback deve retornar ao frame base apos `endanim`, como `PokeAnim_Play` faz no ASM.
  - Idle deve rodar em loop quando o contexto visual pedir `animationKind: "idle"`.
  - O fallback de tocar os frames de cima para baixo uma vez so deve ser usado quando a especie nao tiver entrada extraida.
- Shiny:
  - Gen 2 suporta shiny.
  - Renderer deve reservar variação de paleta/sprite quando o save indicar shiny.
  - Se asset shiny não existir exportado, usar tint/paleta controlada, nunca sprite Gen 3.

### HUD de HP

- HUD mais refinado que Gen 1.
- Coordenadas originais de referencia:
  - Inimigo: `hlcoord 1, 0`, HP em `hlcoord 2, 2`.
  - Jogador: `hlcoord 9, 7`, HP em `hlcoord 10, 9`.
  - Party balls inimigo: `ldpixel wPlaceBallsX, 9, 4`, direcao `-TILE_WIDTH`.
  - Party balls jogador: `ldpixel wPlaceBallsX, 12, 12`, direcao `TILE_WIDTH`.
- Assets:
  - `reference/pret/pokecrystal/gfx/battle/enemy_hp_bar_border.png`
  - `reference/pret/pokecrystal/gfx/battle/hp_exp_bar_border.png`
  - `reference/pret/pokecrystal/gfx/battle/hp_bar.pal`
  - `reference/pret/pokecrystal/gfx/battle/exp_bar.pal`
- Inimigo:
  - Nome e nível no topo.
  - Barra de HP.
  - Sem HP numérico para o inimigo.
- Jogador:
  - Nome, nível, barra de HP, HP numérico.
  - EXP bar pode aparecer em batalha local, mas em batalha online pode ser omitida se não houver ganho de EXP.
- Barra de HP:
  - Verde em HP alto.
  - Amarela em HP médio.
  - Vermelha em HP baixo.
  - Transição deve ser em passos, não linear suave.
- A largura visual da barra deve seguir `ComputeHPBarPixels`:
  - `HP_BAR_LENGTH = 6` tiles.
  - `HP_BAR_LENGTH_PX = 48` pixels.
  - HP maior que zero sempre mostra pelo menos 1 pixel.
- A cor deve seguir `GetHPPal`:
  - Verde quando `e >= 24`.
  - Amarela quando `e >= 10`.
  - Vermelha quando `e < 10`.
- O renderer Gen 2 deve tratar nivel e status como campos separados:
  - Se houver status, o jogo substitui a area de nivel pelo status.
  - Se não houver status, o nivel aparece na coordenada original.

### Caixa de texto

- Caixa inferior com borda tile-based.
- A borda deve vir de `reference/pret/pokecrystal/gfx/frames/1.png` por padrao.
- No frontend, o asset correspondente e `frontend/generated/battle-assets/gen2/ui/frames/1.png`.
- Texto em fonte GBC.
- Cor de texto escura, fundo claro.
- Mensagens de batalha seguem a cadência:
  - Mensagem entra.
  - Pausa curta.
  - Animação.
  - Próxima mensagem.
- Referências:
  - `reference/pret/pokecrystal/data/text/battle.asm`
  - `reference/pret/pokecrystal/engine/battle/used_move_text.asm`
  - `reference/pret/pokecrystal/docs/text_commands.md`

### Menu principal de batalha

- Menu 2x2 no canto inferior direito.
- Referência direta:
  - `reference/pret/pokecrystal/engine/battle/menu.asm`
- Opções padrão:
  - `FIGHT`
  - `<PKMN>`
  - `PACK`
  - `RUN`
- Coordenadas originais usam menu na região inferior, com `menu_coords 8, 12, SCREEN_WIDTH - 1, SCREEN_HEIGHT - 1`.
- O cursor deve usar a lógica de `_2DMenu`.
- Em Bug-Catching/Contest/Safari há variações:
  - `PARKBALL×`
  - Safari ball count.
  - Throw bait/rock.
- Para PokeCable online:
  - O menu padrão deve ser link-battle style.
  - `RUN` pode acionar desistência/forfeit no projeto.

### Menu de golpes

- Lista de quatro golpes.
- Deve mostrar:
  - Nome.
  - PP.
  - Tipo.
- A área de tipo/PP é mais clara que Gen 1.
- Golpes podem ser desabilitados por:
  - Disable.
  - Encore.
  - Torment não existe em Gen 2.
  - PP zero.
  - Sleep Talk/Snore constraints.
- O renderer deve mostrar desabilitado com cor/cursor bloqueado.

### Mochila / Pack em batalha

- Gen 2 usa `PACK`, não `BAG`.
- Possui bolsos.
- Assets:
  - `reference/pret/pokecrystal/gfx/pack/pack_menu.png`
  - `reference/pret/pokecrystal/gfx/pack/pack_menu.tilemap`
- Referências de código:
  - `reference/pret/pokecrystal/engine/items/pack.asm`
  - `reference/pret/pokecrystal/engine/items/pack_kris.asm`
  - `reference/pret/pokecrystal/data/items/pocket_names.asm`
  - `reference/pret/pokecrystal/data/items/attributes.asm`
- Visual esperado:
  - Tela própria do Pack.
  - Coluna/lista de itens.
  - Nome do bolso/pocket.
  - Descrição do item.
  - Ícone/decoração da mochila.
  - Setas de navegação para bolsos.
- Bolsos relevantes:
  - Item pocket.
  - Ball pocket.
  - Key item pocket.
  - TM/HM pocket.
- Em batalha:
  - Apenas itens válidos devem permitir `USE`.
  - Itens-chave inválidos mostram mensagem.
  - Bolas podem ser bloqueadas em trainer/link battle conforme engine.
- O site deve manter o visual de Pack mesmo se internamente estiver usando lista HTML.

### Party menu

- Party colorida com ícones.
- Deve mostrar:
  - Nome do Pokémon.
  - Nível.
  - HP bar.
  - HP numérico.
  - Status.
  - Ícone pequeno.
- Assets/paletas:
  - `reference/pret/pokecrystal/gfx/stats/party_menu_bg.pal`
  - `reference/pret/pokecrystal/gfx/stats/party_menu_ob.pal`
  - `reference/pret/pokecrystal/data/pokemon/menu_icons.asm`
- Seleção para troca:
  - Active marcado.
  - Fainted indisponível.
  - Egg não entra em batalha.
  - Mensagens de erro devem voltar à caixa de texto.

### Animações de golpes

- Gen 2 tem scripts bem estruturados.
- Referências:
  - `reference/pret/pokecrystal/data/moves/animations.asm`
  - `reference/pret/pokecrystal/data/battle_anims/`
  - `reference/pret/pokecrystal/engine/battle_anims/`
  - `reference/pret/pokecrystal/docs/battle_anim_commands.md`
- Comandos importantes:
  - `anim_1gfx`, `anim_2gfx`
  - `anim_sound`
  - `anim_obj`
  - `anim_wait`
  - `anim_bgeffect`
  - `anim_loop`
  - `anim_ret`
- Esta é a melhor geração para começar o interpretador real no navegador.
- O renderer deve representar:
  - Objetos temporários sobre o alvo.
  - Efeitos de background.
  - Flash de paleta.
  - Shake.
  - Delays em frames.
- Regra de sheets:
  - `BATTLE_ANIM_GFX_*` da Gen 2 representa tiles de 8x8 carregados em VRAM.
  - O frontend deve recortar o tile/frame correto da sheet exportada.
  - A sheet completa nunca deve aparecer como objeto visual de golpe.
  - Quando houver OAM composite em `animation-map.json`, ele prevalece sobre qualquer fallback generico.
  - Quando nao houver composite, o fallback deve mostrar um tile/frame recortado e registrar a pendencia de timeline real.
- Regra de objeto:
  - `anim_obj` da Gen 2 deve virar uma instancia visual propria, nao um composite generico compartilhado por GFX.
  - Cada instancia deve preservar `args`, `callback`, `frameset`, `gfx`, `object` e OAM composite.
  - Cada instancia deve preservar tambem `startFrame` e `startMs`, calculados pela ordem real do script ASM.
  - O renderer deve aplicar `--battle-effect-delay` com base nesse tempo para que o objeto apareca no frame correto.
  - As coordenadas X/Y dos argumentos de `anim_obj` devem ser a fonte primaria de `--battle-effect-left/top`.
  - Posicionamento generico por ordem do elemento deve ser apenas fallback quando o objeto nao tiver coordenada ASM.
  - `BATTLE_ANIM_FUNC_*` deve ser aplicado como movimento frame-based em JavaScript.
  - O primeiro criterio de cobertura e ter perfil JS para todo callback nao nulo presente em `animation-map.json`.
  - O criterio final e comparar cada perfil com a rotina correspondente em `engine/battle_anims/functions.asm`.
- Regra de timeline:
  - `battle-scene-gen2.js` deve montar a timeline a partir de `data/moves/animations.asm`, sem reordenar comandos.
  - `anim_wait` acumula frames e converte tempo usando 60fps.
  - `anim_obj` registra o frame exato de spawn do objeto.
  - `anim_incobj` e `anim_setobj` usam IDs ASM 1-based; o renderer deve normalizar para indices JS 0-based e anexar o evento ao objeto alvo.
  - `anim_setobj` deve preservar o estado solicitado pelo script.
  - `anim_bgeffect` registra o frame exato em que o efeito de background deve iniciar.
  - O primeiro `anim_bgeffect` deve preencher `backgroundStartFrame`/`backgroundStartMs` e virar `--battle-bg-effect-delay` no renderer.
  - `anim_incbgeffect` deve ser associado pelo nome do efeito e usado para delimitar a duracao do efeito ativo quando aplicavel.
  - `anim_clearobjs` deve encerrar os objetos ativos no frame exato da limpeza de OAM.
  - `anim_ret` encerra a timeline no frame acumulado.
  - O estado atual ja aplica timing da timeline nos objetos `anim_obj`, no primeiro background de efeito, no encerramento por `anim_clearobjs` e na delimitacao por `anim_incbgeffect`.
  - O estado atual tambem anexa `stateEvents` de `anim_incobj`/`anim_setobj` aos objetos, mas a interpretacao visual final ainda precisa seguir cada rotina de `engine/battle_anims/functions.asm`.
  - A pendencia e fazer o renderer consumir a semantica completa de multiplos `anim_bgeffect`, `anim_sound` e `anim_cry`.

## Gen 3: Ruby, Sapphire, Emerald, FireRed, LeafGreen

### Identidade visual

- Aparência Game Boy Advance.
- Mais resolução, mais cor, mais camadas.
- UI não deve parecer Game Boy Color.
- Elementos típicos:
  - Healthboxes mais detalhadas.
  - Textbox larga inferior.
  - Menus com janelas mais coloridas.
  - Sprites maiores e mais limpos.
  - Animações de golpe com sprites, blending, alpha e background effects.

### Área de batalha

- Base 240x160 px.
- Inimigo no alto direito.
- Jogador no baixo esquerdo.
- Diferente das Gens 1/2, a composição tem mais espaço horizontal.
- Fundo/ambiente varia por battle background:
  - Grama.
  - Água.
  - Caverna.
  - Arena.
  - Link battle.
- Para PokeCable online, usar inicialmente um fundo neutro de link battle até mapear o ambiente.
- Referências:
  - `reference/pret/pokeemerald/src/battle_bg.c`
  - `reference/pret/pokeemerald/src/data/graphics/battle_environment.h`
  - `reference/pret/pokeemerald/graphics/battle_interface/`
  - backgrounds de efeito:
    - `reference/pret/pokeemerald/graphics/battle_anims/backgrounds/`

### Sprites de Pokémon

- Estrutura:
  - `reference/pret/pokeemerald/graphics/pokemon/<species>/front.png`
  - `reference/pret/pokeemerald/graphics/pokemon/<species>/back.png`
  - `reference/pret/pokeemerald/graphics/pokemon/<species>/anim_front.png`
  - `reference/pret/pokeemerald/graphics/pokemon/<species>/icon.png`
- Front animations existem e devem ser consideradas futuramente.
- Sprites devem ser coloridos, com proporções GBA.
- Não usar sprites da PokeAPI quando o pacote exportado existir.
- Shiny:
  - Deve usar paleta shiny quando disponível/extraída.
  - Não aplicar filtro CSS genérico como solução final.

### Healthboxes e HP

- Assets:
  - `reference/pret/pokeemerald/graphics/battle_interface/healthbox_singles_opponent.png`
  - `reference/pret/pokeemerald/graphics/battle_interface/healthbox_singles_player.png`
  - `reference/pret/pokeemerald/graphics/battle_interface/healthbox_doubles_opponent.png`
  - `reference/pret/pokeemerald/graphics/battle_interface/healthbox_doubles_player.png`
  - `reference/pret/pokeemerald/graphics/battle_interface/hpbar.png`
  - `reference/pret/pokeemerald/graphics/battle_interface/status*.png`
  - `reference/pret/pokeemerald/graphics/battle_interface/numbers*.png`
- Singles:
  - Oponente: healthbox no alto esquerdo.
  - Jogador: healthbox no baixo direito.
- Doubles:
  - Dois healthboxes por lado.
  - Layout deve suportar slot 0 e slot 1.
  - O renderer atual precisa evoluir para múltiplos slots.
- HP:
  - Barra colorida em steps.
  - HP numérico do jogador.
  - Inimigo sem HP numérico.
- Status:
  - Usar badges gráficos ou cores equivalentes.
  - `PAR`, `SLP`, `PSN`, `BRN`, `FRZ`, `TOX`.

### Caixa de texto

- Textbox inferior larga.
- Asset:
  - `reference/pret/pokeemerald/graphics/battle_interface/textbox.png`
- Texto usa fonte GBA, menor e mais suave que GB/GBC.
- Mensagens podem ocupar duas linhas.
- Em Gen 3, o ritmo visual usa:
  - Janela de texto.
  - Delay por caracteres/mensagem.
  - Pausas para animações.
  - Retorno ao menu de comando.
- Referências:
  - `reference/pret/pokeemerald/src/battle_message.c`
  - `reference/pret/pokeemerald/data/battle_scripts_1.s`
  - `reference/pret/pokeemerald/data/battle_scripts_2.s`

### Menu principal de batalha

- Visual GBA com janela de comandos.
- Deve ter quatro comandos básicos:
  - `FIGHT`
  - `BAG`
  - `POKéMON`
  - `RUN`
- Em doubles, seleção de alvo pode aparecer depois do golpe.
- O menu não deve ser uma lista vertical simples.
- Deve ocupar canto inferior direito ou região inferior com caixa própria.
- O cursor/seleção é gráfico, não apenas texto sublinhado.
- Referências:
  - `reference/pret/pokeemerald/src/battle_controller_player.c`
  - `reference/pret/pokeemerald/src/battle_interface.c`

### Menu de golpes

- Quatro golpes em grade 2x2 ou layout equivalente de Gen 3.
- Deve mostrar:
  - Nome do golpe.
  - PP.
  - Tipo.
  - Possível destaque por categoria visual.
- Golpes desabilitados:
  - Devem ficar bloqueados visualmente.
  - Deve mostrar razão no texto se escolhido.
- Targeting:
  - Singles: alvo direto ou self.
  - Doubles: escolher target quando golpe permite múltiplos alvos ou ally/foe.
- Em Gen 3, o menu de golpe precisa considerar:
  - Abilities.
  - Taunt/Torment/Encore/Disable.
  - Choice item.
  - Assault Vest não existe em Gen 3.

### Mochila / Bag em batalha

- Gen 3 usa Bag visual completa.
- Assets:
  - `reference/pret/pokeemerald/graphics/bag/menu.png`
  - `reference/pret/pokeemerald/graphics/bag/bag_male.png`
  - `reference/pret/pokeemerald/graphics/bag/bag_female.png`
  - `reference/pret/pokeemerald/graphics/bag/select_button.png`
  - `reference/pret/pokeemerald/graphics/bag/rotating_ball.png`
  - `reference/pret/pokeemerald/graphics/bag/hm.png`
- Código:
  - `reference/pret/pokeemerald/src/item_menu.c`
- Visual esperado:
  - Tela própria da Bag.
  - Painel/lista de itens.
  - Nome do pocket.
  - Sprite da mochila do jogador.
  - Ícone do item selecionado.
  - Descrição no rodapé.
  - Setas de scroll.
  - Troca de pocket lateral.
- Bolsos:
  - Items.
  - Poké Balls.
  - TMs/HMs.
  - Berries.
  - Key Items.
- Em batalha:
  - Entrada por `BAG`.
  - `Use` em item válido.
  - Mensagem de falha em item inválido.
  - Retorno ao battle screen após uso.
  - Referência de callback: `CB2_BagMenuFromBattle` e `CB2_SetUpReshowBattleScreenAfterMenu2`.
- Para o site:
  - A seleção de item deve parecer Gen 3 mesmo que o inventário venha do parser Python.
  - Não mostrar cards modernos na superfície principal quando o usuário está dentro da Bag de batalha.

### Party menu

- Party menu de GBA deve ser visualmente mais colorido e espaçado.
- Cada Pokémon deve mostrar:
  - Ícone.
  - Nome.
  - Nível.
  - HP bar.
  - HP numérico.
  - Status.
  - Item segurado se aplicável.
- Em batalha:
  - Active marcado.
  - Fainted indisponível.
  - Eggs bloqueados.
  - Em doubles, precisa saber qual slot será substituído.
- Deve suportar callbacks:
  - Troca normal.
  - Forced switch.
  - Uso de item em Pokémon.

### Animações de golpes

- Gen 3 é a mais complexa.
- Referências:
  - `reference/pret/pokeemerald/data/battle_anim_scripts.s`
  - `reference/pret/pokeemerald/src/battle_anim*.c`
  - `reference/pret/pokeemerald/graphics/battle_anims/`
- Scripts usam:
  - `loadspritegfx`
  - `createsprite`
  - `createvisualtask`
  - `delay`
  - `waitforvisualfinish`
  - `monbg`
  - `clearmonbg`
  - `setalpha`
  - `blendoff`
  - `panse`
  - `loopsewithpan`
  - `call`, `goto`, `return`
- Visual effects incluem:
  - Sprites temporários.
  - Backgrounds de golpe.
  - Masks.
  - Alpha blending.
  - Palette blending.
  - Shake de mon.
  - Movimento senoidal.
  - Screen flash.
- No navegador:
  - O interpretador deve ser assíncrono e frame-based.
  - Cada comando deve produzir uma operação visual.
  - Comandos desconhecidos devem ser ignorados com fallback controlado, não quebrar a batalha.
  - O catálogo `animation-map.json` é a ponte inicial, mas não substitui o interpretador real.

## Textos e localização

### Regras de texto

- Textos de batalha devem usar a linguagem visual da geração, não apenas o conteúdo literal.
- Caixa de texto deve suportar:
  - 1 ou 2 linhas.
  - Quebra em boundaries próximos aos jogos.
  - Delay de mensagem.
  - Prompt/continuação quando aplicável.
- Nomes de Pokémon:
  - Gen 1/2 geralmente aparecem em maiúsculas quando vindos do save.
  - Gen 3 pode usar uppercase nos dados originais, mas o renderer pode preservar nickname do save.
- Golpes:
  - Nome exibido deve vir da geração da batalha.
  - Se o save usa nome canônico com hífen, converter para estilo da geração quando possível.

### Mensagens mínimas obrigatórias

- Início:
  - Jogador/oponente entrou.
  - Pokémon inicial enviado.
- Turno:
  - `X used Y!`
  - Miss.
  - Critical hit.
  - Effectiveness.
  - Status.
  - HP drain/recoil.
  - Faint.
  - Forced switch.
  - Win.
- Itens:
  - Item usado.
  - Item não pode ser usado.
  - Pokémon curado.
  - Status removido.
  - PP restaurado.
  - Item consumido.

## Opções de batalha no site

### Camada visual

- O usuário deve ver primeiro a UI da geração.
- Botões HTML podem continuar existindo como fallback/acessibilidade, mas a camada principal deve parecer o jogo.
- Ações devem mapear:
  - `FIGHT` -> mostra golpes.
  - `PKMN`/`POKéMON` -> party.
  - `ITEM`/`PACK`/`BAG` -> inventário.
  - `RUN` -> desistir/sair conforme regra de sala.
- Em link battle:
  - `RUN` deve pedir confirmação antes de enviar forfeit.
  - Captura deve ser desabilitada.
  - Itens podem ser restringidos por formato, se o projeto definir regras competitivas.

### Estado online

- Quando aguardando o outro jogador:
  - Gen 1/2: caixa de texto com mensagem curta.
  - Gen 3: textbox inferior com estado.
- Quando ação foi enviada:
  - Cursor/menu deve travar.
  - Texto deve indicar espera.
- Quando chega request nova:
  - Menu volta ao estado navegável.

## Inventário por geração

### Gen 1

- Lista única.
- Sem abas/pockets.
- Quantidade simples.
- Janela monocromática.
- Opção cancel no fim.
- Não usar ícones de item modernos.

### Gen 2

- Pack com pockets.
- Visual colorido GBC.
- Descrição de item.
- Ícone/decor da mochila.
- Setas de pocket e scrolling list.
- `PACK`, não `BAG`.

### Gen 3

- Bag completa com sprite do personagem/mochila.
- Pockets laterais/indicadores.
- Ícone do item selecionado.
- Descrição inferior.
- Context menu com `Use`, `Give`, `Toss`, `Cancel` conforme localização.
- Em batalha, contexto deve mostrar `Use` para itens válidos.

## Requisitos de implementação para fidelidade

- Criar renderer por geração:
  - `BattleSceneGen1`
  - `BattleSceneGen2`
  - `BattleSceneGen3`
- Separar layout de batalha, menus e animações.
- Consumir manifestos:
  - `manifest.json` para sprites/HUD.
  - `animation-map.json` para golpe -> animação.
- Implementar interpretador de animação em fases:
  1. Família visual por golpe.
  2. Sprites reais por comando.
  3. Delays e loops reais.
  4. BG effects.
  5. Palette/blend effects.
  6. Target selection e doubles.
- Gen 2 deve ser a primeira a receber interpretador real porque os comandos são mais legíveis e documentados em `docs/battle_anim_commands.md`.
- Gen 3 deve vir depois, pois usa scripts + funções C para visual tasks.
- Gen 1 deve ser tratado como subanimações e special effects, com parser próprio para `battle_anim`.

## Checklist de qualidade visual

- A cena escala sem blur.
- Nenhum texto vaza da caixa.
- HP muda em steps.
- Sprites da geração correta são usados.
- Oponentes usam front sprite.
- Jogador usa back sprite.
- Menu principal usa nomes corretos da geração.
- Inventário usa estrutura correta da geração.
- Party menu mostra status/fainted corretamente.
- Golpes têm pelo menos família visual correta.
- Logs desconhecidos não quebram renderer.
- Gen 1, Gen 2 e Gen 3 nunca compartilham CSS/asset que mude a identidade visual.
