# Roadmap de Implementação: Engines de Batalha Isoladas

Este documento descreve o plano para implementar engines de batalha específicas para cada geração, garantindo fidelidade às mecânicas originais de cada jogo.

## Estrutura de Diretórios
- `app/engines/base/`: Interfaces e contratos comuns.
- `app/engines/gen1/`: Engine fiel a Red/Blue/Yellow.
- `app/engines/gen2/`: Engine fiel a Gold/Silver/Crystal (Futuro).
- `app/engines/gen3/`: Engine fiel a Ruby/Sapphire/Emerald (Engine Hardcore atual).

---

## 1. Fase 1: Engine Gen 1 vs Gen 1 (Foco Atual)

### 1.1. Modelos de Dados (Gen 1)
- [x] 
 Criar `PokemonGen1`:
  - Sistema de DVs (0-15) em vez de IVs.
  - Stat Exp em vez de EVs.
  - Stat "Special" único (usado tanto para dano especial quanto defesa especial).
  - Cálculo de HP e Status seguindo a fórmula da Gen 1.
- [x] 
 Mapeamento de Tipos Gen 1:
  - Poison forte contra Bug (e vice-versa).
  - Ghost sem efeito em Psychic (Bug original).
  - Ice neutro contra Fire.

### 1.2. Mecânicas de Combate (Gen 1)
- [x] 
 **Acertos Críticos**: Chance baseada na `Base Speed`. Moves de alto crítico (Slash, Razor Leaf) multiplicam por 8.
- [x] 
 **Precisão**: Bug do 1/256 (golpes 100% podem errar, exceto Swift).
- [x] 
 **Fórmula de Dano**: Implementar a matemática exata da Gen 1 (arredondamentos específicos e multiplicador 217-255).
- [x] 
 **Physical/Special Split**: Baseado puramente no tipo do golpe.

### 1.3. Estados de Status (Gen 1)
- [x] 
 **Sleep**: Pokémon não ataca no turno em que acorda.
- [x] 
 **Freeze**: Pokémon nunca descongela sozinho (apenas via Haze ou dano Fire).
- [x] 
 **Paralyze/Burn**: Re-calculo de stats ao sofrer debuffs adicionais (Re-roll glitch).

### 1.4. Movimentos Complexos
- [x] 
 **Trap Moves**: Wrap, Bind, Fire Spin bloqueiam o oponente por 2-5 turnos.
- [x] 
 **Hyper Beam**: Sem turno de recarga se nocautear o alvo ou quebrar Substitute.
- [x] 
 **Substitute**: Lógica de absorção e bugs de interface fiéis.
- [x] 
 **Haze**: Limpeza total de todos os modificadores e status (exceto do próprio Haze).

---

## 2. Fase 2: Engine Gen 2 vs Gen 2
- [x] 
 Adição dos tipos Dark e Steel.
- [x] 
 Divisão do stat Special em Special Attack e Special Defense (mantendo DVs para retrocompatibilidade).
- [x] 
 Introdução de Held Items.
- [x] 
 Introdução do Clima (Rain, Sun, Sandstorm).

---

## 3. Fase 3: Engine Gen 3 vs Gen 3
- [x] 
 (Em andamento) Habilidades (Abilities).
- [x] 
 Sistema de Natures.
- [x] 
 Sistema de IVs (0-31) e EVs (Cap 510).
- [x] 
 Batalhas em Dupla (2v2).
