# Tarefas da Engine de Batalha (Custom Hardcore)

## Fase 0: Arquitetura de Isolamento (Multi-Engine)
- [x] **0.1. Estrutura de Diretórios:** Isolar as engines em `app/engines/gen1`, `gen2` e `gen3`.
- [x] **0.2. BattleEngineRouter:** Implementar o roteador que despacha as batalhas para a engine correta baseado no `format_id`.
- [x] **0.3. Interfaces Comuns:** Definir `BattleEngineAdapter` para garantir interoperabilidade entre o servidor WebSocket e as diferentes gerações.

## Fase 1: Engine Gen 1 vs Gen 1 (Puro RBY)
- [x] **1.1. Modelos Gen 1:** Criar `PokemonGen1` com DVs (0-15), Stat Exp e Stat "Special" unificado.
- [x] **1.2. Matriz de Tipos Gen 1:** Implementar fraquezas clássicas (Ghost imune a Psychic, Bug vs Poison).
- [x] **1.3. Fórmula de Dano Gen 1:** Implementar a matemática original de Red/Blue/Yellow.
- [x] **1.4. Acertos Críticos Gen 1:** Chance baseada na `Base Speed`.
- [x] **1.5. Precisão Gen 1:** Implementar glitch do 1/256.
- [ ] **1.6. Status Condicionais Gen 1:** Sleep (perde turno ao acordar), Freeze (permanente).
- [ ] **1.7. Movimentos de Aprisionamento:** Wrap, Bind, Fire Spin bloqueando ações.
## Fase 3: Ações, Golpes e Efeitos (State Machine)
- [x] **3.1. Physical/Special Split:** Implementar a regra clássica onde o "Tipo" do golpe define se ele usa Attack ou Special Attack.
- [x] **3.2. Precisão e Esquiva:** Implementar o RNG para verificar se o ataque acerta (Accuracy vs Evasion).
- [x] **3.3. Modificadores de Status (Stat Stages):** Adicionar o suporte a golpes como *Swords Dance* ou *Growl* (-6 a +6 multiplicadores).
- [x] **3.4. Acertos Críticos:** Implementar a chance de causar o dobro de dano e ignorar penalidades de stat.
- [x] **3.5. Condições de Status Básicas:** Implementar Burn, Paralyze, Sleep, Poison, Toxic e Freeze, incluindo suas penalidades.
- [x] **3.6. Consumo de PP:** Implementar a redução de 1 PP por uso de golpe e desativação de golpes sem PP.

## Fase 4: Integração com WebSockets e Frontend
- [x] **4.1. Conversão de Comandos:** Fazer o servidor traduzir a requisição do jogador em uma ação que a Engine compreenda.
- [x] **4.2. Geração de Logs (Protocolo Showdown):** Fazer a nossa Engine cuspir as frases padronizadas que o frontend já sabe ler.
- [x] **4.3. Ligar a Chave:** Substituir o sistema temporário no arquivo `battle_engine.py` pelo nosso motor real.
- [x] **4.4. Correção de Fluxo de Troca:** Resolvido bug onde Pokémon desmaiados podiam ser reescolhidos.

## Fase 5: Testes Finais e Validação
- [x] **5.1. Testes Automatizados com Saves Reais:** Script de simulação validou o fluxo de turnos, normalização de stats e mecânicas de desmaio.
- [x] **5.2. Batalha Justa (Finetuning):** Ajustar o peso de golpes e efeitos (Status Chance, Multi-step Damage Floor).
- [x] **5.3. Testes de Interface:** Validar se as animações no frontend reagem corretamente aos novos logs gerados. (Verificado via integração WebSocket)

## Fase 6: Expansão de Fidelidade (Mecânicas Gen 3)
- [x] **6.1. Sistema de Abilities:** Implementar as habilidades passivas (ex: Levitate, Intimidate, Wonder Guard).
- [x] **6.2. Itens Segurados (Held Items):** Implementar o efeito de itens como Leftovers, Berries e Choice Band.
- [x] **6.3. Golpes Complexos:** Implementar golpes com efeitos especiais (ex: Recoil, Draining, Stat Boosting).
- [x] **6.4. Clima:** Implementar os efeitos de Rain, Sun, Sandstorm e Hail (que afetam o poder de golpes e causam dano por turno).
- [x] **6.5. Golpes de Multi-hit:** Implementar golpes como Fury Swipes ou Rock Blast (2-5 hits).
- [x] **6.6. Recalcular Status visual (Frontend):** Garantir que os nomes e HP dos Pokémon no frontend reflitam exatamente o estado da engine.

## Fase 7: Mecânicas Avançadas e Casos Extremos (Roadmap 100% Gen 3)
- [x] **7.1. Condições Voláteis (Minor Status):** Implementar Confusion e Flinch.
- [x] **7.2. Movimentos de Múltiplos Turnos:** Implementar Fly, Dig, Dive, Bounce (que tornam o usuário semi-invulnerável) e ataques de carga (Solar Beam, Skull Bash).
- [x] **7.3. Movimentos de Proteção:** Implementar Protect e Detect (com chance de falha em uso consecutivo).
- [x] **7.4. Habilidades Avançadas:** Implementar Synchronize (passa status). [Habilidades de Clima (Drizzle, Drought, Sand Stream) Concluídas]
- [x] **7.4.1. Trace:** Implementar Trace (copia habilidade ao entrar). Concluído.
- [x] **7.5. Movimentos de Cura:** Implementar Recover, Softboiled, Milk Drink, e Rest (cura total + Sleep).
- [x] **7.6. Movimentos de Phazing e Trapping:** Implementar Roar/Whirlwind (forçam troca), Mean Look e Partial Trapping (Bind/Fire Spin). Concluído.
- [x] **7.7. Struggle:** Lógica para quando um Pokémon ficar sem PP em todos os ataques (causa dano e recoil de 1/4 da vida máxima).
- [x] **7.8. Entry Hazards:** Implementar Spikes (dano na entrada de troca).
- [x] **7.9. Batalhas em Dupla (2v2):** Suporte para o principal formato competitivo introduzido na Geração 3. Concluído.
- [x] **7.10. Substitute:** Boneco de 25% de HP que bloqueia danos e status secundários. Concluído.
- [x] **7.11. Leech Seed:** Drenagem de 1/8 HP por turno e cura do usuário. Concluído.
- [x] **7.12. Taunt, Encore e Disable:** Mecânicas de bloqueio de escolha de golpes. Concluído.
- [x] **7.13. Golpes de Dano Fixo:** Seismic Toss, Night Shade, Psywave e Sonic Boom. Concluído.
- [x] **7.14. OHKO Moves:** Horn Drill, Fissure, Guillotine e Sheer Cold. Concluído.
- [x] **7.15. Timer e Limites:** Sistema para impedir batalhas infinitas no servidor (Turn Limit de 100 turnos implementado).
- [x] **7.16. Habilidades Restantes:** Implementar Swift Swim/Chlorophyll (velocidade no clima), Guts, Marvel Scale, Intimidate (refinamento). Concluído.

## Fase 8: Fidelidade Total Gen 3 (Movimentos e Status)
- [x] **8.1. Telas e Barreiras:** Implementar Reflect, Light Screen e Safeguard (redução de dano e prevenção de status).
- [x] **8.2. Movimentos de Passagem e Substituição:** Baton Pass (repassar stat stages, confusion e Substitute) e Memento.
- [x] **8.3. Movimentos de Instakill/Sacrifício:** Destiny Bond, Perish Song, Explosion e Self-Destruct.
- [x] **8.4. Counters e Absorções:** Counter, Mirror Coat e Bide (retornar o dobro do dano recebido).
- [x] **8.5. Movimentos Dinâmicos:** Flail, Reversal, Eruption e Water Spout (poder baseado no HP) e Low Kick (poder baseado no peso do alvo).
- [x] **8.6. Hidden Power e Frustration/Return:** Implementar a lógica real baseada em IVs e Felicidade (Happiness).
- [x] **8.7. Clima Avançado:** Weather Ball (muda de tipo e dobra poder), Thunder (100% accuracy na chuva), e Solar Beam (sem carga no sol).
- [x] **8.8. Movimentos de Bloqueio/Aprisionamento:** Outrage, Petal Dance, Thrash (ataque forçado e confusão), Hyper Beam e Blast Burn (turno de recarga após uso).

## Fase 9: Fidelidade Total Gen 3 (Abilities e Items)
- [x] **9.1. Auditoria das 76 Abilities:** Identificar e implementar todas as habilidades competitivas faltantes da Gen 3 (ex: Speed Boost, Shed Skin, Clear Body, Huge Power, Thick Fat).
- [x] **9.2. Auditoria de Itens de Batalha:** Implementar Choice Band, Lum Berry, Sitrus Berry, Leftovers, White Herb, Mental Herb e Pinch Berries.
- [x] **9.3. Itens Específicos de Espécie:** Light Ball (Pikachu), Thick Club (Cubone/Marowak), Soul Dew (Latias/Latios) e DeepSeaTooth/Scale (Clamperl).

## Fase 10: Importação e Compatibilidade Retroativa (Gen 1 & 2 -> Gen 3)
- [x] **10.1. Geração de Personality Value (PV):** Algoritmo determinístico baseado em IVs e Trainer ID para consistência em Nature/Ability.
- [x] **10.2. Conversão e Balanceamento de DVs para IVs:** DV range 0-15 mapeado para 0-31 IVs.
- [x] **10.3. Conversão de Stat Exp para EVs:** Normalizado para o Cap de 510 EVs (Balanceamento para Batalhas Justas).
- [x] **10.4. Tradução de Itens (Gen 2 -> Gen 3):** Mapeamento funcional para itens compatíveis entre gerações.
- [x] **10.5. Movesets Retroativos Exclusivos:** Suporte garantido para golpes herdados de Gerações anteriores.

## Fase 11: Polimento Final e Extremos (Roadmap 100% Blending)
- [ ] **11.1. Auditoria de Efeitos de Golpes Raros:** Implementar Skill Swap, Role Play, Trick, Thief (roubo de item real na engine).
- [ ] **11.2. Habilidades de Suporte:** Magnet Pull (prende Steel), Arena Trap (prende terrestres), Soundproof (imune a sons).
- [ ] **11.3. Sistema de Berry Consumption:** Implementar ativação imediata de Berries ao sofrer dano ou no fim do turno (conforme o tipo).
- [ ] **11.4. Shiny Status Real:** Garantir que o brilho (Shiny) no frontend reflita o PV e TID calculados.
