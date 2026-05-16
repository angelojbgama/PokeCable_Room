# Button Mapper - R36S

Ferramenta para mapear os botões do seu R36S e gerar configuração.

**Localização:** `PokeCable/ButtonMapper/`

## Dependências

```bash
sudo apt install python3-pygame
```

## Arquivos

- **button_mapper.py** - Ferramenta interativa de mapeamento
- **button_config.json** - Configuração gerada (criado após executar)
- **logs/** - Logs de mapeamento

## Como Usar

### 1. No R36S - Execute a ferramenta

```bash
cd /opt/system/ButtonMapper
python3 button_mapper.py
```

### 2. Pressione CADA botão

Na tela você verá:
- 4 botões grandes (A, B, X, Y)
- D-Pad (↑ ↓ ← →)
- Display do último botão pressionado

Pressione cada um para registrar.

### 3. Aperte ESC para salvar

A ferramenta vai:
- Salvar mapeamento em `button_config.json`
- Criar log detalhado em `logs/button_mapper_*.log`
- Exibir resumo dos botões mapeados

## Resultado

Após executar, você terá `button_config.json` com o mapeamento:

```json
{
  "button_0": "button_0",
  "button_1": "button_1",
  "dpad_up": "dpad_up",
  "dpad_down": "dpad_down",
  ...
}
```

## Copiar para R36S

```bash
# Do seu computador local:
scp -i ~/.ssh/id_ed25519_kinghost -r /mnt/c/Users/Angelo/Documents/projetos/PokeCable_Room/PokeCable/ButtonMapper ark@192.168.7.1:/opt/system/
```

## Copiar config para Tool_Pokecable

Após mapear, copie o arquivo de config:

```bash
cp button_config.json ../Tool_Pokecable/
```

## Debugging

Ver logs detalhados:
```bash
cat logs/button_mapper_*.log
tail -f logs/button_mapper_*.log
```

## Botões Padrão (SDL)

Mapeamento comum do SDL:
- Button 0 = A
- Button 1 = B
- Button 2 = Y
- Button 3 = X
- Hat = D-Pad
- Axis 1 = Analog UP/DOWN

Se os botões não forem esses, a ferramenta vai mostrar quais são reais.
