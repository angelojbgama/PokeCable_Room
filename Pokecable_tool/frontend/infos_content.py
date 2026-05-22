"""Conteúdo dos artigos exibidos na tela 'Infos' do menu."""
from __future__ import annotations

# Cada artigo é uma lista de parágrafos. Quebras em parágrafos ficam por conta do wrap_text.
# Os textos estão em PT-BR; futuramente pode-se adicionar EN/ES no mesmo formato.

ARTICLES_PT = {
    "retrocompat": {
        "title": "Retrocompatibilidade",
        "paragraphs": [
            "Como a troca entre geracoes funciona.",

            "SEMPRE PRESERVA:",
            "- Especie",
            "- Nivel e XP",
            "- ID do treinador",
            "- Apelido e OT",
            "- Movimentos e PP",

            "RECRIADO QUANDO FALTA:",
            "- Genero (Gen 1 nao tem)",
            "- Natureza e Habilidade (so Gen 3)",
            "- HP IV em Gen 1/2 (vem dos outros)",

            "GEN 1 <-> GEN 2:",
            "Sem perdas. Tudo volta igual.",
            "Item nao existe em Gen 1, fica vazio.",

            "GEN 1/2 -> GEN 3:",
            "DV (0-15) vira IV (0-31): IV = DV x 2.",
            "Stat Exp (0-65535) vira EV (0-252).",
            "Genero, natureza e habilidade vem do PID.",

            "GEN 3 -> GEN 1/2:",
            "IV vira DV: DV = IV / 2 (perde o bit final).",
            "EV vira Stat Exp: EV x 256.",
            "Natureza e Habilidade somem.",

            "ITENS SEGURADOS:",
            "Nada e descartado nunca.",
            "1. Se o item nao existe na geracao destino,",
            "   a troca e recusada (remova o item antes).",
            "2. Se a Gen destino tem o item, ele segue na mao.",
            "3. Se a Gen destino nao tem held items (Gen 1),",
            "   o item vai para a mochila do treinador.",
            "4. Se a mochila esta cheia, vai para o PC.",
            "5. Se ambos estao cheios, a troca e recusada.",

            "IDA E VOLTA:",

            "Gen 1 <-> Gen 2: 100% identico.",

            "Gen 1/2 -> Gen 3 -> Gen 1/2:",
            "DV volta igual. EV pode cair ate 255.",

            "Gen 3 -> Gen 1/2 -> Gen 3:",
            "IV perde no maximo 1 ponto por stat.",
            "Stats finais podem diferir em 1 ponto.",
            "Exemplo: ATK 267 vira 266.",

            "OBSERVACOES:",
            "- Shiny e mantido.",
            "- Genero pode mudar se passa por Gen 1.",
            "- Forma do Unown e recalculada.",
            "- Item nunca e perdido (ver topico acima).",

            "Testado em mais de 170 mil casos automaticos.",
        ],
    },
    "about": {
        "title": "Sobre o PokeCable",
        "paragraphs": [
            "PokeCable e uma ferramenta de troca de Pokemon entre saves das tres primeiras "
            "geracoes (Game Boy, Game Boy Color, Game Boy Advance).",

            "Voce pode trocar localmente entre dois saves seus (modo 'Trocar comigo') ou "
            "entrar numa sala em rede para trocar com outra pessoa.",

            "O programa le e escreve direto nos arquivos .sav, recalculando checksums e "
            "preservando o maximo de informacao possivel entre formatos diferentes.",

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
