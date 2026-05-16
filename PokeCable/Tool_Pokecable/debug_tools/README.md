# PokeCable Debug Tools

Ferramentas para debug e diagnóstico do PokeCable.

## Ferramentas Disponíveis

### button_mapper.py

Ferramenta para mapear eventos de joystick e identificar códigos de botão.

**Uso:**
```bash
python3 button_mapper.py
```

**Saída esperada:**
```
Joystick 0: GO-Super Gamepad
Button 10: A (Select)
Button 1: B (Back)
Button 9: X
Button 11: Y
Button 6: L1
Button 7: R1
Axis 0: Left Analog X
Axis 1: Left Analog Y
Hat: D-Pad
```

## Debug Mode

Para ativar debug mode na ferramenta principal, execute:

```bash
POKECABLE_DEBUG=1 ./pokecable.sh
```

Ou:

```bash
export POKECABLE_DEBUG=1
./pokecable.sh
```

**Efeitos do debug mode:**
- Logs mais verbosos no arquivo de log
- Nível de log definido para DEBUG ao invés de INFO
- Arquivo de log em: `logs/pokecable_YYYYMMDD_HHMMSS.log`

**Desativar debug mode (produção):**
```bash
./pokecable.sh
```

ou explicitamente:

```bash
POKECABLE_DEBUG=0 ./pokecable.sh
```
