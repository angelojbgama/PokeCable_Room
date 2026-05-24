# Guia de Atualização do PokeCable

## Como funciona o sistema de atualização

### 1. **Verificação de Atualização (check_for_update)**
- Consulta a GitHub API para verificar a versão mais recente
- Compara com a versão local (`APP_VERSION`)
- Mostra na tela se há uma nova versão disponível

### 2. **Aplicação de Atualização (apply_update)**
- **Método 1 (Recomendado):** `git pull` se git estiver disponível
  - Automático e limpo
  - Requer git instalado no dispositivo
- **Método 2 (Manual):** Download do ZIP e extração
  - Para dispositivos sem git

---

## Para Desenvolvedores: Criar uma Nova Release

### Passo 1: Commit com versão
```bash
git add .
git commit -m "up versão 1.0.1"
git push origin main
```

**GitHub Actions fará automaticamente:**
1. Detecta commit com `"up versão X.Y.Z"`
2. Cria arquivo ZIP: `PokeCable_Room-X.Y.Z.zip`
3. Compacta **apenas** `Pokecable_tool/` (exclui testes, .cache, etc)
4. Cria Release no GitHub com o ZIP como asset

### Passo 2: O que está no ZIP
```
PokeCable_Room-1.0.1.zip
└── Pokecable_tool/
    ├── pokecable_save.py
    ├── r36s_pokecable_core.py
    ├── pokecable_runtime/
    ├── frontend/
    ├── version.py          ← versão da aplicação
    └── ... (código completo)
```

**Excluído do ZIP:**
- `.git/`, `.github/` (desenvolvimento)
- `tests/` (testes)
- `__pycache__/`, `.pytest_cache/`, `logs/` (temp)
- `*.pyc`, `.egg-info/` (build artifacts)

---

## Para Usuários R36S: Atualizar

### Opção 1: Via Menu (Automático com git)
1. Na tela principal → "Verificar Atualização"
2. Se houver nova versão → Pressione **A**
3. Sistema faz `git pull origin main`
4. Reinicie a aplicação

**Pré-requisito:** Git instalado no R36S

### Opção 2: Download Manual (sem git)
1. Acesse: https://github.com/angelojbgama/PokeCable_Room/releases
2. Baixe `PokeCable_Room-X.Y.Z.zip`
3. Extraia em `C:\Users\[seu_usuário]\Downloads\`
4. Copie a pasta `Pokecable_tool` para substituir a antiga

---

## Informações de Versão

- **Versão Atual:** definida em `Pokecable_tool/version.py` (`APP_VERSION`)
- **Versão Remota:** lida do `tag_name` da release (v1.0.0)
- **Comparação:** `1.0.0 >= 1.0.0` (string comparison, funciona para versionamento semântico)

**Exemplo:**
```python
# Pokecable_tool/version.py
APP_VERSION = "1.0.1"
```

Ao fazer commit com `"up versão 1.0.1"`:
- Release criada com tag `v1.0.1`
- ZIP nomeado `PokeCable_Room-1.0.1.zip`
- App detecta que `1.0.1` > `1.0.0` e oferece atualizar

---

## Logs de Atualização

Todos os detalhes são registrados em `logs/error.log`:
```
UPDATE CHECK: versão atual: 1.0.0
UPDATE CHECK: consultando URL: https://api.github.com/repos/angelojbgama/PokeCable_Room/releases/latest
UPDATE CHECK: versão remota: 1.0.1
UPDATE CHECK: ⚠ Nova versão disponível: 1.0.1

UPDATE APPLY: executando 'git pull origin main'...
UPDATE APPLY: stdout: Updating abc1234..def5678
UPDATE APPLY: ✓ Git pull executado com sucesso
```

---

## Troubleshooting

### "Git não disponível"
- Mensagem: "Git não disponível. Faça download manualmente no GitHub."
- **Causa:** Git não está instalado ou não está no PATH
- **Solução:** 
  - Instale git no dispositivo, OU
  - Use opção manual (download ZIP)

### "Timeout ao atualizar"
- **Causa:** Conexão lenta ou repositório grande
- **Solução:** 
  - Verifique conexão de rede
  - Tente novamente
  - Use download manual se persistir

### "Versão mais recente"
- **Causa:** Não há versão mais nova no GitHub
- **Solução:** Desenvolvimento ainda em progresso

---

## Estrutura de Desenvolvimento

```
PokeCable_Room/
├── .github/workflows/
│   └── release.yml           ← Cria release automaticamente
├── Pokecable_tool/           ← ⭐ ISSO vai no R36S
│   ├── version.py            ← Versão atual
│   ├── pokecable_save.py
│   ├── r36s_pokecable_core.py
│   ├── pokecable_runtime/
│   ├── frontend/
│   └── tests/                ← NÃO vai no ZIP
├── tests/                    ← Testes de integração
└── README.md
```

---

## Comandos Úteis

**Ver versão atual:**
```bash
grep "APP_VERSION" Pokecable_tool/version.py
```

**Simular commit de versão (local):**
```bash
git commit --allow-empty -m "up versão 1.0.1"
# Depois: git push origin main
```

**Verificar releases no GitHub:**
```bash
gh release list --repo angelojbgama/PokeCable_Room
```

**Fazer download do ZIP:**
```bash
gh release download v1.0.1 --repo angelojbgama/PokeCable_Room --pattern "*.zip"
```
