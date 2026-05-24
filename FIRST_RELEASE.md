# Como Fazer a Primeira Release

## ⚡ Quick Start (3 passos)

### Passo 1: Atualizar versão
```bash
cd Pokecable_tool
vi version.py
# Mude: APP_VERSION = "1.0.0"
```

### Passo 2: Fazer commit com versão
```bash
git add Pokecable_tool/version.py
git commit -m "up versão 1.0.0"
git push origin main
```

### Passo 3: Verificar Release
- Vá para: https://github.com/angelojbgama/PokeCable_Room/releases
- Veja o arquivo `PokeCable_Room-1.0.0.zip`
- ✅ Pronto!

---

## 📋 Checklist Completo

- [ ] Version.py atualizado com versão correta
- [ ] Testes passando localmente
- [ ] App funciona: `bash Pokecable_tool/pokecable.sh`
- [ ] Commit com mensagem exata: `"up versão 1.0.0"`
- [ ] Push feito: `git push origin main`
- [ ] GitHub Actions rodando (veja Actions tab)
- [ ] Release criada com ZIP

---

## ⚠️ Erros Comuns

### Erro: Release não foi criada
**Causa:** Mensagem de commit errada
- ❌ `"up versão 1.0.0"` com número?
- ✅ `"up versão 1.0.0"` exato!

**Solução:**
```bash
# Verifique o último commit
git log -1 --oneline

# Se errado, faça outro commit
git commit --allow-empty -m "up versão 1.0.0"
git push
```

### Erro: Arquivo ZIP vazio ou sem Pokecable_tool
**Causa:** Git não encontrou a pasta
**Solução:** Verifique que `Pokecable_tool/` existe no repo

### Erro: Version não bate
**Causa:** version.py tem `1.0.0` mas commit diz `1.0.1`
**Solução:**
- Sempre atualize `version.py` ANTES do commit
- Eles devem ser iguais

---

## 🔍 Como Verificar

### Ver arquivos no ZIP sem extrair
```bash
unzip -l PokeCable_Room-1.0.0.zip | head -20
```

### Ver se version.py está correto no ZIP
```bash
unzip -p PokeCable_Room-1.0.0.zip Pokecable_tool/version.py
```
**Esperado:**
```
APP_VERSION = "1.0.0"
```

### Ver releases via CLI
```bash
gh release list --repo angelojbgama/PokeCable_Room
```

---

## 📝 Exemplo Passo a Passo

```bash
# 1. Fazer desenvolvimento normal
git commit -m "fix: corrige bug Gen4"
git commit -m "feat: adiciona validação"
git push

# 2. Está pronto para release?
# Edite version.py
echo 'APP_VERSION = "1.0.1"' > Pokecable_tool/version.py

# 3. Commit de versão
git add Pokecable_tool/version.py
git commit -m "up versão 1.0.1"
git push origin main

# 4. GitHub Actions faz o resto automaticamente
# Espere 30-60 segundos
# Veja em: https://github.com/angelojbgama/PokeCable_Room/actions

# 5. Release criada com ZIP
# https://github.com/angelojbgama/PokeCable_Room/releases/tag/v1.0.1
# Arquivo: PokeCable_Room-1.0.1.zip
```

---

## 📦 O que User Faz com o ZIP

1. **Download:** `PokeCable_Room-1.0.1.zip`
2. **Extrai em:** `C:\Users\[seu_usuario]\Downloads\`
3. **Copia:** `Pokecable_tool` para R36S
4. **Reinicia** a app

Ou usa o menu de atualização automática se tiver `git` instalado.

---

## 🚀 Próximos Passos

1. Teste esta primeira release
2. Verifique que o ZIP foi criado corretamente
3. Teste extrair em outro lugar
4. Confirme que app roda normalmente

---

## ❓ Dúvidas?

Veja:
- `UPDATE_GUIDE.md` - Documentação completa
- `RELEASE_STRUCTURE.md` - Explicação da estrutura
- `.github/workflows/release.yml` - Workflow automatizado
