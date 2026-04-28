# Roadmap Cross-Generation

Cross-generation ainda nao existe no produto.

Regras atuais:

- Gen 1 somente com Gen 1.
- Gen 2 somente com Gen 2.
- Gen 3 somente com Gen 3.
- Nunca copiar `raw_data_base64` entre geracoes diferentes.

## Possibilidade Futura

Um modo especial Gen 1 <-> Gen 2 pode ser estudado no futuro, inspirado na Time Capsule dos jogos oficiais.

Mesmo nesse caso, nao deve ser feito por copia bruta de payload. Seria necessario converter especies, moves, metadados, restricoes e integridade de save com regras explicitas.

Gen 3 <-> Gen 1/2 exigiria uma conversao propria ainda mais cuidadosa e nao deve reutilizar `raw_data_base64` diretamente.
