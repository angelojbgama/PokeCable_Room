# Roadmap Cross-Generation

Cross-generation e uma direcao do PokeCable Room. A sala e unica: o usuario nao escolhe Time Capsule, Transfer ou Downconvert. O sistema deriva automaticamente o caminho de conversao necessario em cada direcao da troca.

Mesmo com conversores locais presentes, cross-generation continua atras de feature flags no client e no servidor.

## Modos Internos

- `same_generation`: modo estavel atual, usa raw payload somente entre saves da mesma geracao.
- `time_capsule_gen1_gen2`: modo Gen 1 <-> Gen 2 inspirado na Time Capsule oficial, com bloqueio de species/moves incompatíveis.
- `forward_transfer_to_gen3`: modo Gen 1/2 -> Gen 3 com recriacao local segura de dados Gen 3.
- `legacy_downconvert_experimental`: modo Gen 3 -> Gen 1/2, experimental e com perdas controladas de ability, nature, itens e metadados modernos.

Em uma troca Gen 1 <-> Gen 3, por exemplo, o jogador Gen 1 recebe pelo modo `legacy_downconvert_experimental`, enquanto o jogador Gen 3 recebe pelo modo `forward_transfer_to_gen3`.

## Regras

- Nunca copiar `raw_data_base64` entre geracoes diferentes.
- Cross-generation deve usar `CanonicalPokemon` e conversores por destino.
- `CanonicalPokemon` separa National Dex, ID nativo da geracao e espaco de ID.
- O servidor nao edita save e nao converte Pokemon.
- O servidor faz preflight de protocolo: se algum lado reportar incompatibilidade, ninguem recebe commit.
- O client gera backup antes de qualquer escrita.
- Se o save mudar enquanto a sala estiver aberta, a gravacao deve ser cancelada.

## Time Capsule Gen 1/2

Deve respeitar especies, moves e restricoes compatíveis com Gen 1/2. Held item, dados de breeding, genero e metadados que nao existem em Gen 1 precisam ser removidos ou reportados como perda de dados.

## Transfer Para Gen 3

Gen 1/2 -> Gen 3 nao deve escrever raw antigo no save GBA. O client precisa converter para modelo canonico e criar uma estrutura Gen 3 valida, recalculando checksums e preservando o que for compatível.

## Downconvert Experimental

Gen 3 -> Gen 1/2 exige perda explicita de dados modernos como nature, ability e parte de metadados de batalha. Esse modo deve permanecer atras de feature flag ate existir validacao forte.
