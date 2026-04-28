# Roadmap Cross-Generation

Cross-generation e uma direcao do PokeCable Room. O bloqueio atual e uma feature guard de seguranca por modo: mesmo com conversores locais presentes, cada modo precisa ser habilitado explicitamente no client e no servidor antes de uso real.

## Modos Planejados

- `same_generation`: modo estavel atual, usa raw payload somente entre saves da mesma geracao.
- `time_capsule_gen1_gen2`: modo Gen 1 <-> Gen 2 inspirado na Time Capsule oficial, com bloqueio de species/moves incompatíveis.
- `forward_transfer_to_gen3`: modo Gen 1/2 -> Gen 3 com recriacao local segura de dados Gen 3.
- `legacy_downconvert_experimental`: modo Gen 3 -> Gen 1/2, experimental e com perdas controladas de ability, nature, itens e metadados modernos.

## Regras

- Nunca copiar `raw_data_base64` entre geracoes diferentes.
- Cross-generation deve usar `CanonicalPokemon` e conversores por destino.
- `CanonicalPokemon` separa National Dex, ID nativo da geracao e espaco de ID.
- O servidor nao edita save e nao converte Pokemon.
- O client gera backup antes de qualquer escrita.
- Se o save mudar enquanto a sala estiver aberta, a gravacao deve ser cancelada.

## Time Capsule Gen 1/2

Deve respeitar especies, moves e restricoes compatíveis com Gen 1/2. Held item, dados de breeding, genero e metadados que nao existem em Gen 1 precisam ser removidos ou reportados como perda de dados.

## Transfer Para Gen 3

Gen 1/2 -> Gen 3 nao deve escrever raw antigo no save GBA. O client precisa converter para modelo canonico e criar uma estrutura Gen 3 valida, recalculando checksums e preservando o que for compatível.

## Downconvert Experimental

Gen 3 -> Gen 1/2 exige perda explicita de dados modernos como nature, ability e parte de metadados de batalha. Esse modo deve permanecer atras de feature flag ate existir validacao forte.
