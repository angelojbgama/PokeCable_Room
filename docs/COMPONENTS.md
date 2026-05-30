# Componentes e Responsabilidades

Este documento descreve os componentes atuais do PokeCable Room como tool local-first para R36S/Linux, com troca local e troca direta em rede.

## Diagrama PUML

```plantuml
@startuml
title PokeCable Room - Componentes e responsabilidades

skinparam componentStyle rectangle
skinparam shadowing false
skinparam wrapWidth 180
skinparam maxMessageSize 180

actor "Usuário R36S" as User
node "R36S / Linux" as R36S {
  component "pokecable.sh\nLauncher" as Launcher

  package "UI Pygame\nPokecable_tool/frontend" as UI {
    component "app.py\nLoop principal" as App
    component "session.py\nEstado de navegação e trade" as Session
    component "input.py\nControles do R36S" as Input
    component "input_mapping.py\nPerfis e calibração de botões" as InputMapping
    component "display_scaling.py\nEscala lógica 640x480" as DisplayScaling
    component "screens/*\nTelas e fluxo visual" as Screens
    component "components/*\nPrimitivos visuais" as Components
    component "sprites.py / item_sprites.py\nCarregamento de sprites" as Sprites
    component "i18n.py / theme.py / fonts.py\nIdioma, tema e fontes" as Presentation
    component "trade_flow.py\nFluxo de troca local" as TradeFlow
  }

  package "Tool Core\nPokecable_tool" as Tool {
    component "r36s_pokecable_ui.py\nEntrada compatível da UI" as UiEntrypoint
    component "r36s_pokecable_core.py\nServiços de app e estado global" as Core
    component "pokecable_save.py\nLeitura, escrita, backup e checksum" as Save
    component "pokecable_lan.py\nTroca direta em rede local" as Lan
    component "save_curation.py\nFiltro/curadoria de saves" as Curation
    component "pokecable_logging.py\nLogs locais" as Logging
    component "version.py\nVersão da tool" as Version
  }

  package "Runtime Pokémon\nPokecable_tool/pokecable_runtime" as Runtime {
    component "runtime_services.py\nPreflight, enrich e serviços de trade" as RuntimeServices
    component "canonical/*\nModelo canônico Pokémon" as Canonical
    component "parsers/*\nParsers Gen 1/2/3/4" as Parsers
    component "converters/*\nConversores entre gerações" as Converters
    component "compatibility/*\nRegras e matriz de compatibilidade" as Compatibility
    component "evolutions/*\nEvoluções por troca" as Evolutions
    component "events/*\nEventos extras de save" as Events
    component "data/*\nEspécies, moves, itens, learnsets e layouts" as Data
    component "display.py\nDados preparados para exibição" as Display
  }

  package "Recursos locais" as Resources {
    database "Saves .sav" as Saves
    folder "config/*\nPerfis de dispositivo e input calibrado" as Config
    folder "assets/*\nSprites, badges, fontes" as Assets
    folder "logs/*" as Logs
    folder "dependence/python/*\nDependências vendorizadas" as Deps
  }
}

node "Outro R36S / PC na mesma rede" as Peer {
  component "PokeCable Room\nInstância remota" as PeerApp
}

package "Qualidade e suporte" as Quality {
  component "tests/*\nTestes de save, conversão, LAN e UI" as Tests
  component "tools/*\nGeração/atualização de dados e assets" as Tools
  folder "roms/*\nROMs/fixtures locais quando usados" as Roms
  folder "docs/*\nDocumentação" as Docs
}

User --> Launcher
Launcher --> UiEntrypoint
UiEntrypoint --> App

App --> Session
App --> Input
App --> DisplayScaling
App --> Screens
Screens --> Components
Screens --> Sprites
Screens --> Presentation
Screens --> TradeFlow
Input --> InputMapping

TradeFlow --> Core
TradeFlow --> RuntimeServices
Core --> Save
Core --> Curation
Core --> Logging
Core --> Version

Lan --> Save
Lan --> RuntimeServices
Lan <--> PeerApp : TCP JSON Lines\nLAN discovery

Save --> Parsers
Save --> Data
Save --> Saves : leitura/escrita\nbackup/checksum
InputMapping --> Config

RuntimeServices --> Canonical
RuntimeServices --> Parsers
RuntimeServices --> Converters
RuntimeServices --> Compatibility
RuntimeServices --> Evolutions
RuntimeServices --> Data
RuntimeServices --> Display
RuntimeServices --> Events

Converters --> Canonical
Converters --> Data
Compatibility --> Canonical
Compatibility --> Data
Evolutions --> Canonical
Evolutions --> Data
Parsers --> Canonical
Parsers --> Data

Sprites --> Assets
Presentation --> Assets
Logging --> Logs
App --> Deps

Tests ..> Tool
Tests ..> Runtime
Tools ..> Data
Tools ..> Assets
Docs ..> Tool
Roms ..> Tests

@enduml
```

## Responsabilidades

| Componente | Responsabilidade |
|---|---|
| `Pokecable_tool/pokecable.sh` | Iniciar a tool no ambiente Linux do R36S. |
| `Pokecable_tool/r36s_pokecable_ui.py` | Manter a entrada legada/compatível da interface e chamar `frontend.app.main()`. |
| `Pokecable_tool/frontend/app.py` | Executar o loop principal da UI Pygame, montar telas, despachar eventos e controlar o fluxo visual. |
| `Pokecable_tool/frontend/session.py` | Guardar estado mutável da navegação, seleção de saves, prompts, resoluções de moves/itens e resultado da troca. |
| `Pokecable_tool/frontend/input.py` | Traduzir entradas do R36S/teclado para ações da interface. |
| `Pokecable_tool/frontend/input_mapping.py` | Carregar perfis automáticos de dispositivo, priorizar calibração local e converter botões físicos para ações lógicas. |
| `Pokecable_tool/frontend/display_scaling.py` | Criar a tela Pygame com resolução lógica 640x480 e escala automática quando suportada. |
| `Pokecable_tool/frontend/screens/*` | Separar telas de menu, seleção, confirmação, resolução de conflitos, troca e resultado. |
| `Pokecable_tool/frontend/components/*` | Fornecer primitvos visuais reutilizáveis, como painéis, listas, botões, badges e barras. |
| `Pokecable_tool/frontend/trade_flow.py` | Coordenar a troca local entre saves, incluindo prompts, evolução, item relocation e finalização. |
| `Pokecable_tool/frontend/sprites.py` e `item_sprites.py` | Resolver e carregar sprites de Pokémon e itens para exibição. |
| `Pokecable_tool/frontend/i18n.py`, `theme.py`, `fonts.py` | Centralizar idioma, paleta visual e fontes da interface. |
| `Pokecable_tool/r36s_pokecable_core.py` | Concentrar serviços gerais da aplicação, descoberta de saves, configuração e integração entre UI e backend local. |
| `Pokecable_tool/pokecable_save.py` | Ler saves, montar payloads de Pokémon, aplicar alterações, atualizar checksums e proteger escrita com backup. |
| `Pokecable_tool/pokecable_lan.py` | Fazer troca direta em rede local usando descoberta LAN, conexão TCP e mensagens JSON Lines. |
| `Pokecable_tool/save_curation.py` | Filtrar saves de desenvolvimento/teste para não poluir a seleção normal. |
| `Pokecable_tool/pokecable_logging.py` | Configurar caminhos e comportamento de logs locais. |
| `Pokecable_tool/version.py` | Expor a versão atual da tool. |
| `Pokecable_tool/pokecable_runtime/runtime_services.py` | Montar preflight de troca, enriquecer payloads, validar destino e resolver serviços de trade. |
| `Pokecable_tool/pokecable_runtime/canonical/*` | Definir o modelo canônico de Pokémon, moves, itens e dados independentes da geração. |
| `Pokecable_tool/pokecable_runtime/parsers/*` | Ler e escrever estruturas específicas de saves Gen 1, Gen 2, Gen 3 e Gen 4 quando suportado. |
| `Pokecable_tool/pokecable_runtime/converters/*` | Converter Pokémon entre gerações preservando o que for possível e registrando perdas. |
| `Pokecable_tool/pokecable_runtime/compatibility/*` | Validar regras de compatibilidade, matriz de modos e relatórios de perdas/transformações. |
| `Pokecable_tool/pokecable_runtime/evolutions/*` | Resolver evoluções por troca simples e por item quando habilitadas. |
| `Pokecable_tool/pokecable_runtime/data/*` | Manter dados estáticos de espécies, moves, itens, learnsets, growth rates, gênero, inventário e políticas. |
| `Pokecable_tool/pokecable_runtime/events/*` | Aplicar eventos e extras relacionados ao save quando a UI usar essa área. |
| `Pokecable_tool/pokecable_runtime/display.py` | Preparar dados derivados para apresentação na UI. |
| `Pokecable_tool/assets/*` | Guardar sprites, badges, fontes e outros recursos visuais usados localmente. |
| `Pokecable_tool/config/device_profiles.json` | Declarar presets conhecidos de controles por nome de dispositivo. |
| `Pokecable_tool/config/input_map.json` | Guardar calibração local do usuário quando criada. |
| `Pokecable_tool/dependence/python/*` | Disponibilizar dependências Python vendorizadas para uso offline no R36S. |
| `Pokecable_tool/logs/*` | Armazenar logs gerados pela execução local. |
| `tests/*` | Cobrir parsing, escrita, conversões, compatibilidade, roundtrip, LAN, UI e extras. |
| `tools/*` | Gerar ou atualizar dados auxiliares, learnsets e assets. |
| `tools/calibrate_input.py` | Calibrar um controle desconhecido e salvar o mapeamento local. |
| `docs/*` | Documentar arquitetura, telas, decisões e uso do projeto. |

## Fluxos principais

### Troca local comigo mesmo

1. UI seleciona dois saves locais e os Pokémon de origem/destino.
2. `trade_flow.py` pede preflight para `runtime_services.py`.
3. `runtime_services.py` usa canonical, parsers, converters, compatibility, evolutions e data.
4. UI resolve confirmações de moves, itens e evolução quando necessário.
5. `pokecable_save.py` cria backup, aplica alterações e atualiza checksums.

### Troca direta em rede

1. `pokecable_lan.py` anuncia ou descobre outra instância na LAN.
2. As duas instâncias trocam payloads por TCP JSON Lines.
3. Cada lado executa preflight local antes de aceitar.
4. Após confirmação, cada lado grava apenas o próprio save local com backup.

### Leitura e escrita de save

1. `pokecable_save.py` identifica geração/jogo e carrega o save.
2. Parsers específicos extraem party, box e metadados suportados.
3. Dados são convertidos para payload/canonical para UI e trade.
4. Na escrita, o módulo aplica bytes alterados, recalcula checksums e preserva backup.
