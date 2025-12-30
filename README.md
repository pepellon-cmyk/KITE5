```markdown
# Kite for Life — App de Avaliação de Desempenho (protótipo) — Versão com Dashboard, Pesos e Autenticação

O projeto contém:
- app.py — aplicação Streamlit com autenticação básica, dashboard, radar, import/export, e funcionalidades de pesos.
- create_user.py — script para criar/atualizar usuários locais (users.json).
- create_zip.py — script para criar kite_for_life_app.zip contendo os arquivos do projeto.
- users.json — arquivo de usuários (default contém admin/admin). **Altere a senha com create_user.py.**
- weights.json — arquivo com pesos (padrão igual). Pode ser sorteado via app.
- requirements.txt

Como executar
1. Crie e ative um ambiente virtual:
   - python -m venv .venv
   - source .venv/bin/activate (Linux/macOS) ou .venv\\Scripts\\activate (Windows)
2. Instale dependências:
   - pip install -r requirements.txt
3. (Opcional) Crie/edite usuário:
   - python create_user.py
   - Isso cria/atualiza users.json com usuário e senha (local).
4. Rode o app:
   - streamlit run app.py

Autenticação
- O app usa um arquivo local `users.json` com senhas como hash SHA-256.
- Um usuário padrão `admin` com senha `admin` é criado automaticamente na primeira execução. Troque esta senha com `python create_user.py`.

Pesos (média ponderada)
- A barra lateral exibe os pesos atuais (soma = 1).
- Use "Sortear pesos" para gerar pesos aleatórios (sorteio) e "Reset pesos igual" para distribuir uniformemente.
- Clique "Salvar pesos atuais" para gravar em `weights.json`.
- Ao adicionar uma nova avaliação há um checkbox "Aplicar pesos atuais ao salvar" — se marcado, grava `nota_ponderada` no banco.

Importação CSV
- O import tenta mapear colunas com variações e normaliza valores para escala 0–10 se detectar escala maior (ex.: 0–100).
- Ao importar, também é calculada a nota ponderada (se houver pesos).

Dashboard & Visual
- Dashboard com KPIs, gráfico de barras por critério, boxplots por critério, top avaliados, série temporal e comparação radar.
- Visual aprimorado com CSS e tema escuro para gráficos Plotly.

Export / ZIP
- Use `python create_zip.py` para gerar `kite_for_life_app.zip` com os arquivos do projeto (se existirem).

Segurança
- Este protótipo usa autenticação local simples e NÃO é adequado para produção exposto na internet.
- Para produção, use autenticação forte, armazenamento seguro de senhas e HTTPS.

Próximos passos que eu posso fazer
- Implementar OAuth (Google) ou integração com um servidor de autenticação.
- Adicionar permissões por papéis (ex.: avaliador x administrador).
- Remover usuário padrão e obrigar criação de novo admin no primeiro run.
- Deploy em servidor (Heroku, Render, Vercel + FastAPI backend), com banco Postgres.

```