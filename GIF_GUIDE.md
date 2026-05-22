# 🎬 Guia de GIFs para Portfólio

Este documento explica como capturar e adicionar GIFs ao projeto para demonstrar em ação.

---

## 📸 GIFs Recomendados

### 1. Dashboard Principal (15-20 segundos)

**O que mostrar:**
- Página carregando
- KPI cards exibindo dados
- Gráficos interativos

**Como capturar:**
```bash
# Usar ferramenta como ffmpeg, ScreenToGif, ou OBS
# Abrir: http://localhost:8050
# Fazer login com admin/admin123
# Navegar pelo dashboard, mostrar cards e gráficos
# Parar ao chegar em rankings
```

**Arquivo:** `assets/demo/dashboard.gif`

---

### 2. Login & RBAC (10-15 segundos)

**O que mostrar:**
- Tela de login
- Fazer login com usuário ADMIN
- Dashboard do ADMIN (visão completa)
- Logout
- Fazer login com MANAGER (ver dados diferentes)

**Como capturar:**
```bash
# 1. Estar na página de login
# 2. Digitar credenciais admin/admin123
# 3. Enter e aguardar dashboard
# 4. Voltar para login
# 5. Digitar credenciais manager (se existir)
# 6. Mostrar que dados são diferentes
```

**Arquivo:** `assets/demo/login.gif`

---

### 3. Callbacks Interativos (15-20 segundos)

**O que mostrar:**
- Abrir filtros (calendário, seleção, etc)
- Clicar em diferentes filtros
- Dashboard atualizar sem recarregar página
- Velocidade de resposta (<1 segundo)

**Como capturar:**
```bash
# 1. Dashboard já carregado
# 2. Clicar em filtro de data
# 3. Selecionar período diferente
# 4. Dashboard atualiza smoothly
# 5. Abrir seletor de vendedor
# 6. Escolher vendedor diferente
# 7. Dados atualizam em tempo real
```

**Arquivo:** `assets/demo/callbacks.gif`

---

## 🛠️ Como Capturar GIFs

### Opção 1: ScreenToGif (Windows/Mac)
```bash
# Download: https://www.screentogif.com
# Fácil de usar, interface gráfica
# Permite ajustar duração, FPS, tamanho
```

### Opção 2: OBS Studio (Todos OS)
```bash
# Download: https://obsproject.com
# 1. Abrir OBS
# 2. Add "Display Capture" (mostrar tela)
# 3. REC para gravar
# 4. Exportar como .mp4
# 5. Converter para .gif com ffmpeg (veja abaixo)
```

### Opção 3: ffmpeg (CLI, Mais Control)
```bash
# Gravar tela (Linux)
ffmpeg -f x11grab -s 1920x1080 -r 30 -i :0 video.mp4

# Converter MP4 para GIF
ffmpeg -i video.mp4 -vf "fps=10,scale=1280:-1" output.gif

# Converter MP4 para GIF (otimizado, menor tamanho)
ffmpeg -i video.mp4 -vf "fps=8,scale=800:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" output.gif
```

### Opção 4: Gifcap (Mac)
```bash
# Download: https://www.gifcap.dev
# Simples e rápido
```

---

## 📁 Estrutura para GIFs

Crie a pasta:
```bash
mkdir -p assets/demo
```

Adicione os GIFs:
```
assets/
└── demo/
    ├── dashboard.gif          (500-800 KB)
    ├── login.gif              (200-400 KB)
    └── callbacks.gif          (300-500 KB)
```

---

## 📝 Adicionar GIFs ao README.md

Após capturar, adicione ao `README.md` (após o título, antes de "Principais Recursos"):

```markdown
## 🎬 Demo & Capturas

### Dashboard Principal
![Dashboard Demo](assets/demo/dashboard.gif)
*Interface Glassmorphism com KPIs em tempo real*

### Login & RBAC
![Login Demo](assets/demo/login.gif)
*Autenticação de 3 níveis (ADMIN, MANAGER, SELLER)*

### Callbacks Interativos
![Callbacks Demo](assets/demo/callbacks.gif)
*Filtros dinâmicos sem recarregar página*

---
```

---

## 🎬 Tamanho Ideal dos GIFs

| GIF | Duração | Tamanho Recomendado | FPS |
|-----|---------|-------------------|-----|
| Dashboard | 15-20s | 500-800 KB | 10 |
| Login | 10-15s | 200-400 KB | 10 |
| Callbacks | 15-20s | 300-500 KB | 8 |

**Dica:** GIFs menores carregam mais rápido no GitHub!

---

## 💡 Dicas para Bons GIFs

1. ✅ **Calma:** Não clique muito rápido, deixar legível
2. ✅ **Foco:** Mostrar apenas a parte importante
3. ✅ **Limpeza:** Fechar abas, notificações, etc
4. ✅ **Resolução:** Usar 1920x1080 mínimo
5. ✅ **Loop:** GIF vai repetir infinito, fazer faz sentido
6. ✅ **Títulos:** Adicionar subtítulo descritivo

---

## 🚀 Após Capturar

### 1. Adicionar GIFs ao Repositório
```bash
cd /home/sup/dash_ticket_vendedor

# Criar pasta
mkdir -p assets/demo

# Copiar GIFs
cp ~/Downloads/dashboard.gif assets/demo/
cp ~/Downloads/login.gif assets/demo/
cp ~/Downloads/callbacks.gif assets/demo/

# Commitar
git add assets/demo/
git commit -m "assets: adicionar GIFs de demonstração do projeto"
git push origin main
```

### 2. Atualizar README.md
Edite `README.md` e adicione a seção de GIFs (veja acima).

### 3. Fazer Commit
```bash
git add README.md
git commit -m "docs: adicionar GIFs de demonstração ao README"
git push origin main
```

---

## 📊 Impacto dos GIFs

**Antes:**
- Recruiter abre GitHub
- Lê README estático
- Interessado, mas não sabe como funciona
- Vai explorar código (demora)

**Depois:**
- Recruiter abre GitHub
- Vê 3 GIFs funcionando
- Wow! Entendeu tudo em 30 segundos
- Clica em SETUP_LOCAL.md para rodar localmente
- Impressionado! 🎉

---

## ⚡ Alternativa: Usar Assets do GitHub

Se não quiser capturar, pode usar placeholders e adicionar depois:

```markdown
## 🎬 Demo & Capturas

![Dashboard Demo - Em breve](https://via.placeholder.com/800x600.gif?text=Dashboard+Demo)
```

Mas recomendo capturar para ser autêntico!

---

## 🎯 Próximas Ações

- [ ] Baixar ferramenta (ScreenToGif ou OBS)
- [ ] Capturar 3 GIFs (dashboard, login, callbacks)
- [ ] Otimizar tamanho (ffmpeg)
- [ ] Adicionar pasta `assets/demo/` ao repositório
- [ ] Atualizar README.md com GIFs
- [ ] Fazer push
- [ ] Verificar no GitHub

---

**Última atualização:** Maio 2026
**Status:** Guia completo para adicionar GIFs
