# Estrutura de Release - PokeCable Room

## 📦 O que vai no Release (R36S)

Quando você faz commit com `"up versão 1.0.0"`, o GitHub Actions cria:

```
PokeCable_Room-1.0.0.zip
└── Pokecable_tool/              ← TUDO que o R36S precisa
    ├── pokecable.sh
    ├── r36s_pokecable_core.py
    ├── pokecable_save.py
    ├── version.py               ← APP_VERSION = "1.0.0"
    ├── frontend/                ├── UI (pygame)
    │   ├── app.py
    │   ├── screens/
    │   └── components/
    ├── pokecable_runtime/       ├── Parsers, converters, etc
    │   ├── parsers/
    │   ├── converters/
    │   └── compatibility/
    ├── logs/
    └── UPDATE_GUIDE.md
```

## 📁 O que NÃO vai no Release (ficam locais)

```
PokeCable_Room/                 ← Repositório (não compactado)
├── .github/                    ← GitHub Actions
├── tests/                      ← Testes de integração
├── roms/                       ← ROMs para teste local
├── README.md                   ← Documentação dev
└── ...
```

---

## 🔄 Fluxo de Atualização

### Desenvolvedor (você)
```bash
# 1. Desenvolve e testa localmente
git add .
git commit -m "adiciona suporte a nova feature"
git push

# 2. Pronto para release
git commit --allow-empty -m "up versão 1.0.1"
git push origin main
# ↓ GitHub Actions detecta e cria automaticamente:
# - Tag: v1.0.1
# - Release: PokeCable_Room-1.0.1.zip
# - Assets: PokeCable_Room-1.0.1.zip
```

### Usuário R36S
```bash
# 1. Via Menu (automático)
Menu → "Verificar Atualização" → A (confirmar)
# App executa: git pull origin main
# App reinicia com nova versão

# 2. Via Download (manual)
# Download: PokeCable_Room-1.0.1.zip
# Extrai em: C:\Users\[user]\Downloads\
# Copia: Pokecable_tool para substituir
```

---

## 📋 Checklist Antes de Versionar

```bash
# 1. Atualizar version.py se necessário
# Pokecable_tool/version.py:
# APP_VERSION = "1.0.1"

# 2. Rodar testes locais
cd Pokecable_tool
pytest tests/

# 3. Testar manualmente se possível
bash pokecable.sh

# 4. Commit de desenvolvimento normal (sem "up versão")
git commit -m "fix: corrige bug no parser Gen4"

# 5. Quando tudo está pronto para release
git commit --allow-empty -m "up versão 1.0.1"
git push origin main
# ✓ GitHub Actions cria release automaticamente
```

---

## 🛠️ Verificação do ZIP Criado

O GitHub Actions executa:
```bash
cd Pokecable_tool
zip -r ../PokeCable_Room-1.0.1.zip . \
  -x ".git*" ".pytest_cache*" "__pycache__*" \
  "*.pyc" ".cache*" "logs/*" "*.egg-info*"
```

**Resultado:**
- ✅ `pokecable.sh`, `*.py`, `pokecable_runtime/`, `frontend/`
- ❌ `.git/`, `tests/`, `__pycache__/`, `logs/`

---

## 📊 Comparação de Tamanho

| Tipo | Tamanho | Descrição |
|------|---------|-----------|
| **Repositório completo** | ~500 MB | Inclui tests, .git, roms, caches |
| **Pokecable_tool (dev)** | ~50 MB | Com __pycache__, logs |
| **PokeCable_Room-X.Y.Z.zip** | ~10 MB | ZIP limpo pronto para R36S |

---

## 🔗 Links Importantes

- **Releases:** https://github.com/angelojbgama/PokeCable_Room/releases
- **Latest:** https://github.com/angelojbgama/PokeCable_Room/releases/latest
- **Download direto:** `gh release download vX.Y.Z --pattern "*.zip"`

---

## 📝 Versionamento

**Formato:** `X.Y.Z` (semântico)

Exemplos de commits:
```bash
git commit -m "up versão 1.0.0"   # Release 1.0.0
git commit -m "up versão 1.0.1"   # Patch (bug fix)
git commit -m "up versão 1.1.0"   # Minor (feature)
git commit -m "up versão 2.0.0"   # Major (breaking change)
```

Sempre atualize `Pokecable_tool/version.py` também:
```python
APP_VERSION = "1.0.1"  # Deve corresponder à tag
```

---

## 🚀 Próximos Passos

1. **Testar o workflow:**
   - Faça um commit com `"up versão 1.0.0"`
   - Vá para GitHub → Actions
   - Confirme que o ZIP foi criado

2. **Validar no R36S:**
   - Faça download do ZIP
   - Extraia e teste

3. **Integrar com app:**
   - Menu "Verificar Atualização" consulta releases
   - `git pull` atualiza código automaticamente
