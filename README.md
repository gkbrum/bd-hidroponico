# 🌱 Sistema de Automação de Estufas — Interface Visual (PBD + SQLite)

Interface gráfica desenvolvida em **Python** e **Streamlit** com **SQLite embutido** para demonstração prática e interativa do projeto de Banco de Dados de Automação e Monitoramento de Estufas Agrícolas.

> **💡 Vantagem do SQLite:** Não precisa ter o PostgreSQL ou MySQL instalado ou rodando. O banco de dados é criado e povoado automaticamente em um arquivo local `estufas.db` ao abrir a aplicação.

---

## 🚀 Como Executar (Passo a Passo)

### 1. (Opcional) Criar o Ambiente Virtual (`venv`)

- **Windows:**
  ```powershell
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  ```
- **Linux / macOS:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

---

### 2. Instalar as Dependências

```bash
pip install -r requirements.txt
```

---

### 3. Iniciar a Aplicação

Execute o comando no terminal:

```bash
python -m streamlit run app.py
```

A interface abrirá automaticamente no seu navegador em **`http://localhost:8501`**.

---

## 🖥️ Funcionalidades da Interface

- **🏠 Visão Geral:** Estatísticas gerais do sistema e listagem das tabelas.
- **🔍 Consultas SQL:** Execução interativa das 6 consultas pré-definidas do relatório.
- **➕ Inserções:** Formulários para novos cultivos e leituras de sensores.
- **⚡ Gatilhos & Triggers:** Demonstração interativa dos 4 gatilhos em tempo real (atualização de timestamp de comunicação, bloqueio de 2 ciclos ativos e alertas de segurança por extrapolação de limites).
- **🔄 Resetar Banco:** Botão na barra lateral que limpa e recarrega os dados iniciais do banco a qualquer momento durante a apresentação.
