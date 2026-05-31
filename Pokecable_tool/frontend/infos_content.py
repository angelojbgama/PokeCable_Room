"""Conteúdo dos artigos exibidos na tela 'Infos' do menu."""
from __future__ import annotations

# Cada artigo é uma lista de parágrafos. Quebras em parágrafos ficam por conta do wrap_text.
# Os textos estão em PT-BR; futuramente pode-se adicionar EN/ES no mesmo formato.

ARTICLES_PT = {
    "retrocompat": {
        "title": "Retrocompatibilidade",
        "paragraphs": [
            "Como o PokeCable converte Pokemon entre saves das geracoes 1, 2 e 3.",

            "SEMPRE PRESERVA:",
            "- Especie",
            "- Nivel e XP",
            "- ID do treinador",
            "- Apelido e OT",
            "- Movimentos compativeis e PP",
            "- Shiny quando os dados permitem",

            "RECRIADO OU RECALCULADO QUANDO FALTA:",
            "- Genero (Gen 1 nao tem)",
            "- Natureza e habilidade (Gen 3)",
            "- HP DV em Gen 1/2",
            "- Forma do Unown",

            "GEN 1 <-> GEN 2:",
            "E o caminho mais fiel. DV, Stat Exp, movimentos e dados principais voltam praticamente iguais.",
            "Gen 1 nao tem item segurado; quando necessario, o app pergunta o que fazer com o item antes da transferencia.",

            "GEN 1/2 -> GEN 3:",
            "DV (0-15) vira IV (0-31): IV = DV x 2.",
            "Stat Exp vira EV moderno dentro do limite da Gen 3.",
            "Genero, natureza e habilidade sao derivados dos dados gerados para a Gen 3.",

            "GEN 3 -> GEN 1/2:",
            "IV vira DV: DV = IV / 2 (perde o bit final).",
            "EV vira Stat Exp equivalente.",
            "Natureza, habilidade e outros campos que nao existem em Gen 1/2 nao sao gravados no destino.",

            "MOVIMENTOS:",
            "Se um movimento nao existe no jogo destino, o app pede um substituto valido ou permite deixar o slot vazio.",
            "A troca so grava depois que as escolhas pendentes forem resolvidas.",

            "ITENS SEGURADOS:",
            "Se o item existe e pode ser segurado no destino, ele acompanha o Pokemon.",
            "Se o destino nao pode receber o item segurado, o app pergunta se o item volta para a mochila, para o PC, ou se deve ser jogado fora no save de origem.",
            "Se nao houver espaco para guardar o item, a troca e bloqueada e o app pede para remover o item manualmente no jogo.",

            "EVOLUCAO POR TROCA:",
            "Quando a troca causaria evolucao, o app mostra a evolucao antes de gravar.",
            "Voce pode deixar evoluir ou cancelar a evolucao e manter a troca.",

            "SEGURANCA:",
            "Antes de gravar, o PokeCable cria backup do save.",
            "Na troca local entre dois saves, se algo falhar, o app tenta restaurar os backups.",
            "Na LAN, a gravacao so acontece depois que os dois lados confirmam.",

            "IDA E VOLTA:",
            "Gen 1 <-> Gen 2 e o ciclo mais estavel.",
            "Gen 1/2 -> Gen 3 -> Gen 1/2 preserva DV, mas valores derivados podem sofrer arredondamento.",
            "Gen 3 -> Gen 1/2 -> Gen 3 pode perder ate 1 ponto de IV por stat por causa da conversao IV/DV.",

            "OBSERVACOES:",
            "- Genero pode mudar se passa por Gen 1.",
            "- Campos que nao existem na geracao destino nao aparecem no save destino.",
            "- O app evita gravar quando uma escolha obrigatoria ainda nao foi feita.",

            "Testado em mais de 170 mil casos automaticos.",
        ],
    },
    "about": {
        "title": "Sobre o PokeCable",
        "paragraphs": [
            "PokeCable e uma ferramenta para trocar Pokemon entre arquivos de save das tres primeiras geracoes: Game Boy, Game Boy Color e Game Boy Advance.",

            "Existem dois fluxos principais. Em 'Trocar comigo', voce escolhe dois saves no mesmo aparelho e troca Pokemon entre eles. Em 'Sala em rede', dois aparelhos na mesma LAN fazem a troca diretamente.",

            "A LAN nao usa servidor externo nem internet. O app procura outro PokeCable na rede local, permite digitar IP/porta manualmente e encerra o processo de rede quando voce sai da LAN.",

            "O programa le e escreve direto nos arquivos .sav, recalculando checksums e preservando o maximo de informacao possivel entre formatos diferentes.",

            "Antes de cada gravacao, um backup e criado. O app tambem verifica se o save mudou no disco antes de aplicar uma troca em rede.",

            "Durante a troca, o PokeCable pode pedir confirmacao para evolucao por troca, substituicao de movimentos ou destino de item incompatível.",

            "Para saber detalhes sobre como os dados sao preservados entre geracoes, "
            "consulte o topico 'Retrocompatibilidade'.",
        ],
    },
}


def get_topics(language: str = "pt") -> list[tuple[str, str]]:
    """Return list of (topic_key, display_title) tuples in the order they should appear."""
    # i18n title comes from STRINGS; we just return keys here
    return [
        ("retrocompat", ARTICLES_PT["retrocompat"]["title"]),
        ("about", ARTICLES_PT["about"]["title"]),
    ]


def get_article(topic_key: str, language: str = "pt") -> dict:
    """Return {title, paragraphs} for a given topic."""
    # Currently only PT; future: branch by language
    return ARTICLES_PT.get(topic_key, ARTICLES_PT["retrocompat"])
