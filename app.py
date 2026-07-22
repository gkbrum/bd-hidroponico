import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime

# ==========================================
# CONFIGURAÇÃO DA PÁGINA & ESTILO ESCURO
# ==========================================
st.set_page_config(
    page_title="Sistema de Automação de Estufas (PBD)",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .metric-card {
        background-color: #1E293B;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
    }
    .metric-value {
        font-size: 2.2rem;
        font-weight: 700;
        color: #10B981;
    }
    .metric-label {
        font-size: 0.95rem;
        color: #94A3B8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .trigger-badge {
        background-color: #064E3B;
        color: #34D399;
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 0.85rem;
        font-weight: 600;
        display: inline-block;
        margin-bottom: 8px;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #1E293B;
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
        color: #94A3B8;
    }
    .stTabs [aria-selected="true"] {
        background-color: #10B981 !important;
        color: #FFFFFF !important;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

DB_FILE = "estufas.db"

# ==========================================
# INICIALIZAÇÃO E GESTÃO DO BANCO SQLITE
# ==========================================
def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db(force_reset=False):
    if force_reset and os.path.exists(DB_FILE):
        os.remove(DB_FILE)
    
    conn = get_connection()
    cur = conn.cursor()
    
    # Criar tabelas
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS estufas (
        estufa_id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        data_criacao TEXT,
        localizacao TEXT
    );

    CREATE TABLE IF NOT EXISTS microcontroladores (
        micro_id INTEGER PRIMARY KEY AUTOINCREMENT,
        mac_address TEXT UNIQUE NOT NULL,
        descricao TEXT,
        ultima_comunicacao TEXT,
        fk_estufas_estufa_id INTEGER NOT NULL,
        FOREIGN KEY (fk_estufas_estufa_id) REFERENCES estufas (estufa_id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS setores (
        setor_id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        fk_estufas_estufa_id INTEGER NOT NULL,
        FOREIGN KEY (fk_estufas_estufa_id) REFERENCES estufas (estufa_id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS sensores (
        sensor_id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        tipo TEXT,
        pino_digital INTEGER,
        unidade_medida TEXT,
        fk_microcontroladores_micro_id INTEGER NOT NULL,
        fk_setores_setor_id INTEGER NOT NULL,
        FOREIGN KEY (fk_microcontroladores_micro_id) REFERENCES microcontroladores (micro_id) ON DELETE RESTRICT,
        FOREIGN KEY (fk_setores_setor_id) REFERENCES setores (setor_id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS atuadores (
        atuador_id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        tipo TEXT NOT NULL,
        pino_digital INTEGER,
        fk_microcontroladores_micro_id INTEGER NOT NULL,
        fk_setores_setor_id INTEGER,
        fk_estufas_estufa_id INTEGER,
        FOREIGN KEY (fk_microcontroladores_micro_id) REFERENCES microcontroladores (micro_id) ON DELETE RESTRICT,
        FOREIGN KEY (fk_setores_setor_id) REFERENCES setores (setor_id) ON DELETE CASCADE,
        FOREIGN KEY (fk_estufas_estufa_id) REFERENCES estufas (estufa_id) ON DELETE CASCADE,
        CHECK (
            (tipo = 'Bomba' AND fk_estufas_estufa_id IS NOT NULL AND fk_setores_setor_id IS NULL) OR
            (tipo = 'Valvula' AND fk_setores_setor_id IS NOT NULL AND fk_estufas_estufa_id IS NULL)
        )
    );

    CREATE TABLE IF NOT EXISTS log_leituras (
        sensor_id INTEGER NOT NULL,
        data_hora TEXT NOT NULL,
        valor REAL NOT NULL,
        PRIMARY KEY (sensor_id, data_hora),
        FOREIGN KEY (sensor_id) REFERENCES sensores (sensor_id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS log_comandos (
        atuador_id INTEGER NOT NULL,
        data_hora TEXT NOT NULL,
        estado TEXT NOT NULL,
        origem TEXT,
        PRIMARY KEY (atuador_id, data_hora),
        FOREIGN KEY (atuador_id) REFERENCES atuadores (atuador_id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS catalogo_cultivos (
        cultivo_id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        ph_min REAL,
        ph_max REAL,
        ce_min REAL,
        ce_max REAL,
        temp_ideal REAL
    );

    CREATE TABLE IF NOT EXISTS ciclos_ativos (
        ciclo_id INTEGER PRIMARY KEY AUTOINCREMENT,
        data_inicio TEXT NOT NULL,
        data_fim TEXT,
        fk_catalogo_cultivos_cultivo_id INTEGER NOT NULL,
        fk_setores_setor_id INTEGER NOT NULL,
        FOREIGN KEY (fk_catalogo_cultivos_cultivo_id) REFERENCES catalogo_cultivos (cultivo_id) ON DELETE RESTRICT,
        FOREIGN KEY (fk_setores_setor_id) REFERENCES setores (setor_id) ON DELETE RESTRICT
    );

    CREATE TABLE IF NOT EXISTS log_erros (
        id_dispositivo INTEGER NOT NULL,
        data_hora TEXT NOT NULL,
        cod_erro INTEGER,
        mensagem TEXT,
        PRIMARY KEY (id_dispositivo, data_hora),
        FOREIGN KEY (id_dispositivo) REFERENCES microcontroladores (micro_id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS alertas_seguranca (
        alerta_id INTEGER PRIMARY KEY AUTOINCREMENT,
        sensor_id INTEGER NOT NULL,
        data_hora TEXT NOT NULL,
        valor REAL NOT NULL,
        mensagem TEXT NOT NULL,
        FOREIGN KEY (sensor_id) REFERENCES sensores (sensor_id) ON DELETE CASCADE
    );
    """)

    # Criar Gatilhos (Triggers) em SQLite
    cur.executescript("""
    CREATE TRIGGER IF NOT EXISTS trg_atualizar_comunicacao_sensor
    AFTER INSERT ON log_leituras
    FOR EACH ROW
    BEGIN
        UPDATE microcontroladores
        SET ultima_comunicacao = NEW.data_hora
        WHERE micro_id = (SELECT fk_microcontroladores_micro_id FROM sensores WHERE sensor_id = NEW.sensor_id);
    END;

    CREATE TRIGGER IF NOT EXISTS trg_atualizar_comunicacao_atuador
    AFTER INSERT ON log_comandos
    FOR EACH ROW
    BEGIN
        UPDATE microcontroladores
        SET ultima_comunicacao = NEW.data_hora
        WHERE micro_id = (SELECT fk_microcontroladores_micro_id FROM atuadores WHERE atuador_id = NEW.atuador_id);
    END;

    CREATE TRIGGER IF NOT EXISTS trg_validar_ciclo_ativo
    BEFORE INSERT ON ciclos_ativos
    FOR EACH ROW
    WHEN NEW.data_fim IS NULL AND EXISTS (
        SELECT 1 FROM ciclos_ativos 
        WHERE fk_setores_setor_id = NEW.fk_setores_setor_id 
          AND data_fim IS NULL 
          AND ciclo_id <> NEW.ciclo_id
    )
    BEGIN
        SELECT RAISE(ABORT, 'erro: o setor ja tem um ciclo ativo. finaliza o outro primeiro.');
    END;

    CREATE TRIGGER IF NOT EXISTS trg_verificar_leituras_alertas
    AFTER INSERT ON log_leituras
    FOR EACH ROW
    BEGIN
        INSERT INTO alertas_seguranca (sensor_id, data_hora, valor, mensagem)
        SELECT 
            NEW.sensor_id, 
            NEW.data_hora, 
            NEW.valor,
            'ALERTA pH fora da faixa para ' || c.nome || ' (limites: ' || c.ph_min || '-' || c.ph_max || ', lido: ' || NEW.valor || ')'
        FROM sensores s
        JOIN ciclos_ativos ca ON s.fk_setores_setor_id = ca.fk_setores_setor_id
        JOIN catalogo_cultivos c ON ca.fk_catalogo_cultivos_cultivo_id = c.cultivo_id
        WHERE s.sensor_id = NEW.sensor_id 
          AND ca.data_fim IS NULL
          AND s.tipo = 'pH'
          AND (NEW.valor < c.ph_min OR NEW.valor > c.ph_max);

        INSERT INTO alertas_seguranca (sensor_id, data_hora, valor, mensagem)
        SELECT 
            NEW.sensor_id, 
            NEW.data_hora, 
            NEW.valor,
            'ALERTA CE fora da faixa para ' || c.nome || ' (limites: ' || c.ce_min || '-' || c.ce_max || ', lido: ' || NEW.valor || ')'
        FROM sensores s
        JOIN ciclos_ativos ca ON s.fk_setores_setor_id = ca.fk_setores_setor_id
        JOIN catalogo_cultivos c ON ca.fk_catalogo_cultivos_cultivo_id = c.cultivo_id
        WHERE s.sensor_id = NEW.sensor_id 
          AND ca.data_fim IS NULL
          AND s.tipo = 'CE'
          AND (NEW.valor < c.ce_min OR NEW.valor > c.ce_max);
    END;
    """)

    # Povoar dados iniciais
    cur.execute("SELECT COUNT(*) FROM estufas")
    if cur.fetchone()[0] == 0:
        cur.executescript("""
        INSERT INTO estufas (nome, data_criacao, localizacao) VALUES
        ('Estufa Principal (Norte)', '2026-01-10', 'Setor Norte - UFPel Campus Capão do Leão'),
        ('Estufa Experimental (Sul)', '2026-03-15', 'Setor Sul - UFPel Campus Capão do Leão');

        INSERT INTO microcontroladores (mac_address, descricao, ultima_comunicacao, fk_estufas_estufa_id) VALUES
        ('00:1A:2B:3C:4D:5E', 'Controlador Estufa Norte - Principal', '2026-07-16 23:00:00', 1),
        ('00:1A:2B:3C:4D:5F', 'Controlador Estufa Norte - Auxiliar', '2026-07-16 23:15:00', 1),
        ('11:22:33:44:55:66', 'Controlador Estufa Sul - Geral', '2026-07-16 22:50:00', 2);

        INSERT INTO setores (nome, fk_estufas_estufa_id) VALUES
        ('Setor Alpha', 1),
        ('Setor Beta', 1),
        ('Setor Gamma', 2);

        INSERT INTO sensores (nome, tipo, pino_digital, unidade_medida, fk_microcontroladores_micro_id, fk_setores_setor_id) VALUES
        ('Sensor de Temp Alpha', 'Temperatura', 32, '°C', 1, 1),
        ('Sensor de Umidade Alpha', 'Umidade', 33, '%', 1, 1),
        ('Sensor de pH Alpha', 'pH', 34, 'pH', 2, 1),
        ('Sensor de CE Alpha', 'CE', 35, 'S/m', 2, 1),
        ('Sensor de Temp Gamma', 'Temperatura', 32, '°C', 3, 3);

        INSERT INTO atuadores (nome, tipo, pino_digital, fk_microcontroladores_micro_id, fk_estufas_estufa_id, fk_setores_setor_id) VALUES
        ('Bomba de Mistura Alpha', 'Bomba', 25, 1, 1, NULL),
        ('Válvula Solenoide Alpha', 'Valvula', 26, 1, NULL, 1),
        ('Válvula Solenoide Beta', 'Valvula', 27, 2, NULL, 2),
        ('Bomba de Mistura Gamma', 'Bomba', 25, 3, 2, NULL);

        INSERT INTO catalogo_cultivos (nome, ph_min, ph_max, ce_min, ce_max, temp_ideal) VALUES
        ('Morango Silvestre', 5.5, 6.5, 1.4, 1.8, 20.0),
        ('Alface Americana', 6.0, 7.0, 1.2, 1.6, 18.0),
        ('Tomate Cereja', 5.8, 6.8, 2.0, 2.5, 22.0);

        INSERT INTO ciclos_ativos (data_inicio, data_fim, fk_catalogo_cultivos_cultivo_id, fk_setores_setor_id) VALUES
        ('2026-05-01', '2026-06-15', 2, 1),
        ('2026-06-20', NULL, 1, 1),
        ('2026-07-01', NULL, 3, 3);

        INSERT INTO log_leituras (sensor_id, data_hora, valor) VALUES
        (1, '2026-07-16 23:00:00', 19.5),
        (1, '2026-07-16 23:05:00', 20.2),
        (1, '2026-07-16 23:10:00', 20.8),
        (3, '2026-07-16 23:00:00', 5.8),
        (3, '2026-07-16 23:05:00', 6.2),
        (3, '2026-07-16 23:10:00', 5.3),
        (3, '2026-07-16 23:15:00', 6.7),
        (4, '2026-07-16 23:00:00', 1.5),
        (4, '2026-07-16 23:05:00', 1.3),
        (4, '2026-07-16 23:10:00', 1.9);

        INSERT INTO log_comandos (atuador_id, data_hora, estado, origem) VALUES
        (1, '2026-07-16 23:01:00', 'LIGADO', 'AUTOMATICO'),
        (1, '2026-07-16 23:06:00', 'DESLIGADO', 'AUTOMATICO'),
        (2, '2026-07-16 23:02:00', 'LIGADO', 'AUTOMATICO'),
        (2, '2026-07-16 23:07:00', 'DESLIGADO', 'AUTOMATICO'),
        (2, '2026-07-16 23:12:00', 'LIGADO', 'MANUAL'),
        (2, '2026-07-16 23:17:00', 'DESLIGADO', 'MANUAL');

        INSERT INTO log_erros (id_dispositivo, data_hora, cod_erro, mensagem) VALUES
        (1, '2026-07-16 22:00:00', 503, 'Falha de conexão com o broker MQTT'),
        (1, '2026-07-16 22:05:00', 404, 'Sensor de pH não responde no barramento I2C');
        """)
    
    conn.commit()
    conn.close()

init_db()

# ==========================================
# FUNÇÕES DE CONSULTA E EXECUÇÃO
# ==========================================
def run_query(query, params=None):
    try:
        conn = get_connection()
        if params:
            df = pd.read_sql(query, conn, params=params)
        else:
            df = pd.read_sql(query, conn)
        conn.close()
        return df, None
    except Exception as e:
        return None, str(e)

def execute_statement(query, params=None):
    try:
        conn = get_connection()
        cur = conn.cursor()
        if params:
            cur.execute(query, params)
        else:
            cur.execute(query)
        conn.commit()
        cur.close()
        conn.close()
        return True, "Operação realizada com sucesso!"
    except Exception as e:
        return False, str(e)

# ==========================================
# BARRA LATERAL (SIDEBAR)
# ==========================================
st.sidebar.image("https://img.icons8.com/color/96/greenhouse.png", width=70)
st.sidebar.title("Banco SQLite Ativo")
st.sidebar.success("Banco embutido (Zero Configuração)")

if st.sidebar.button("Resetar Banco de Dados"):
    init_db(force_reset=True)
    st.sidebar.success("Banco resetado para o estado inicial!")
    st.rerun()

# ==========================================
# CORPO DA APLICAÇÃO
# ==========================================
st.title("Projeto Final PBD: Automação de Estufas")
st.caption("Interface Visual Completa — Monitoramento, Consultas, Rastreabilidade de Logs e Gatilhos")

aba1, aba2, aba3, aba4, aba5 = st.tabs([
    "Visão Geral",
    "Logs & Rastreabilidade",
    "Consultas SQL",
    "Inserções & Cadastros",
    "Gatilhos & Triggers"
])

# ------------------------------------------
# ABA 1: VISÃO GERAL
# ------------------------------------------
with aba1:
    st.subheader("Estatísticas e Estado Atual do Sistema")
    
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    
    df_estufas, _ = run_query("SELECT COUNT(*) AS total FROM estufas")
    df_micros, _ = run_query("SELECT COUNT(*) AS total FROM microcontroladores")
    df_sensores, _ = run_query("SELECT COUNT(*) AS total FROM sensores")
    df_alertas, _ = run_query("SELECT COUNT(*) AS total FROM alertas_seguranca")
    
    n_estufas = df_estufas["total"].iloc[0] if df_estufas is not None and not df_estufas.empty else 0
    n_micros = df_micros["total"].iloc[0] if df_micros is not None and not df_micros.empty else 0
    n_sensores = df_sensores["total"].iloc[0] if df_sensores is not None and not df_sensores.empty else 0
    n_alertas = df_alertas["total"].iloc[0] if df_alertas is not None and not df_alertas.empty else 0

    with col_m1:
        st.markdown(f"""<div class="metric-card"><div class="metric-value">{n_estufas}</div><div class="metric-label">Estufas</div></div>""", unsafe_allow_html=True)
    with col_m2:
        st.markdown(f"""<div class="metric-card"><div class="metric-value">{n_micros}</div><div class="metric-label">ESP32s</div></div>""", unsafe_allow_html=True)
    with col_m3:
        st.markdown(f"""<div class="metric-card"><div class="metric-value">{n_sensores}</div><div class="metric-label">Sensores</div></div>""", unsafe_allow_html=True)
    with col_m4:
        st.markdown(f"""<div class="metric-card"><div class="metric-value">{n_alertas}</div><div class="metric-label">Alertas</div></div>""", unsafe_allow_html=True)

    st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
        st.write("### Estufas e Setores Cadastrados")
        df_es, _ = run_query("""
            SELECT e.estufa_id, e.nome AS estufa, e.localizacao, s.nome AS setor 
            FROM estufas e 
            LEFT JOIN setores s ON s.fk_estufas_estufa_id = e.estufa_id
            ORDER BY e.estufa_id;
        """)
        if df_es is not None:
            st.dataframe(df_es, use_container_width=True)

    with col2:
        st.write("### Dispositivos ESP32")
        df_mc, _ = run_query("""
            SELECT m.micro_id, m.mac_address, m.descricao, m.ultima_comunicacao, e.nome AS estufa
            FROM microcontroladores m
            JOIN estufas e ON m.fk_estufas_estufa_id = e.estufa_id
            ORDER BY m.micro_id;
        """)
        if df_mc is not None:
            st.dataframe(df_mc, use_container_width=True)

    st.divider()
    col3, col4 = st.columns(2)
    with col3:
        st.write("### Ciclos Ativos Atualmente")
        df_ca, _ = run_query("""
            SELECT ca.ciclo_id, s.nome AS setor, e.nome AS estufa, c.nome AS cultivo, ca.data_inicio
            FROM ciclos_ativos ca
            JOIN setores s ON ca.fk_setores_setor_id = s.setor_id
            JOIN estufas e ON s.fk_estufas_estufa_id = e.estufa_id
            JOIN catalogo_cultivos c ON ca.fk_catalogo_cultivos_cultivo_id = c.cultivo_id
            WHERE ca.data_fim IS NULL;
        """)
        if df_ca is not None:
            st.dataframe(df_ca, use_container_width=True)
            
    with col4:
        st.write("### Catálogo de Cultivos")
        df_cc, _ = run_query("SELECT * FROM catalogo_cultivos;")
        if df_cc is not None:
            st.dataframe(df_cc, use_container_width=True)

# ------------------------------------------
# ABA 2: LOGS E RASTREABILIDADE
# ------------------------------------------
with aba2:
    st.subheader("Central de Logs e Rastreabilidade Completa")
    st.markdown("Aqui você pode acompanhar todas as leituras de sensores, acionamentos de atuadores e erros de hardware, rastreando a qual setor e estufa pertencem.")

    sub_tab1, sub_tab2, sub_tab3 = st.tabs([
        "Logs de Leituras (Com Rastreio de Setor/Estufa)", 
        "Logs de Comandos em Atuadores", 
        "Logs de Erros de Dispositivos"
    ])

    with sub_tab1:
        st.write("#### Rastreabilidade de Leituras por Sensor, Setor e Estufa")
        st.caption("JOIN entre log_leituras → sensores → setores → estufas")
        df_r, _ = run_query("""
            SELECT 
                l.data_hora,
                s.nome AS sensor,
                s.tipo,
                l.valor || ' ' || s.unidade_medida AS leitura,
                setor.nome AS setor_origem,
                e.nome AS estufa_origem,
                m.mac_address AS esp32_mac
            FROM log_leituras l
            JOIN sensores s ON l.sensor_id = s.sensor_id
            JOIN setores setor ON s.fk_setores_setor_id = setor.setor_id
            JOIN estufas e ON setor.fk_estufas_estufa_id = e.estufa_id
            JOIN microcontroladores m ON s.fk_microcontroladores_micro_id = m.micro_id
            ORDER BY l.data_hora DESC;
        """)
        if df_r is not None:
            st.dataframe(df_r, use_container_width=True)

    with sub_tab2:
        st.write("#### Logs de Comandos Enviados aos Atuadores (Bombas / Válvulas)")
        df_lc, _ = run_query("""
            SELECT 
                lc.data_hora,
                a.nome AS atuador,
                a.tipo AS tipo_atuador,
                lc.estado,
                lc.origem,
                COALESCE(s.nome, 'Estufa Geral: ' || e.nome) AS localizacao
            FROM log_comandos lc
            JOIN atuadores a ON lc.atuador_id = a.atuador_id
            LEFT JOIN setores s ON a.fk_setores_setor_id = s.setor_id
            LEFT JOIN estufas e ON a.fk_estufas_estufa_id = e.estufa_id
            ORDER BY lc.data_hora DESC;
        """)
        if df_lc is not None:
            st.dataframe(df_lc, use_container_width=True)

    with sub_tab3:
        st.write("#### Logs de Erros dos Microcontroladores")
        df_le, _ = run_query("""
            SELECT 
                le.data_hora,
                le.cod_erro,
                le.mensagem,
                m.mac_address,
                m.descricao AS dispositivo,
                e.nome AS estufa
            FROM log_erros le
            JOIN microcontroladores m ON le.id_dispositivo = m.micro_id
            JOIN estufas e ON m.fk_estufas_estufa_id = e.estufa_id
            ORDER BY le.data_hora DESC;
        """)
        if df_le is not None:
            st.dataframe(df_le, use_container_width=True)

# ------------------------------------------
# ABA 3: CONSULTAS SQL
# ------------------------------------------
with aba3:
    st.subheader("Consultas Pré-definidas do Relatório e Dashboard")
    st.markdown("Selecione uma das consultas do projeto para executar em tempo real:")

    consultas_dict = {
        "Consulta 1: Sensores de Temperatura": {
            "sql": """
SELECT sensor_id, nome, pino_digital, unidade_medida
FROM sensores
WHERE tipo = 'Temperatura'
ORDER BY nome;
            """,
            "desc": "Lista todos os sensores do tipo Temperatura e seus respectivos pinos digitais."
        },
        "Consulta 2: Cultivos com pH >= 5.5 e Temp < 22°C": {
            "sql": """
SELECT cultivo_id, nome, ph_min, ph_max, temp_ideal
FROM catalogo_cultivos
WHERE ph_min >= 5.5 AND temp_ideal < 22.0;
            """,
            "desc": "Filtra espécies do catálogo exigentes em pH e temperatura mais fria."
        },
        "Consulta 3: Cultivos e Ciclos Ativos por Setor": {
            "sql": """
SELECT 
    s.nome AS setor_nome, 
    e.nome AS estufa_nome, 
    c.nome AS cultivo_nome, 
    ca.data_inicio AS inicio_do_ciclo
FROM setores s
JOIN estufas e ON s.fk_estufas_estufa_id = e.estufa_id
JOIN ciclos_ativos ca ON ca.fk_setores_setor_id = s.setor_id
JOIN catalogo_cultivos c ON ca.fk_catalogo_cultivos_cultivo_id = c.cultivo_id
WHERE ca.data_fim IS NULL;
            """,
            "desc": "Relatório das estufas e setores com produção agrícola em andamento."
        },
        "Consulta 4: Log de Erros dos Dispositivos ESP32": {
            "sql": """
SELECT 
    le.data_hora, 
    le.cod_erro, 
    le.mensagem, 
    m.mac_address, 
    m.descricao AS dispositivo, 
    e.nome AS estufa_nome
FROM log_erros le
JOIN microcontroladores m ON le.id_dispositivo = m.micro_id
JOIN estufas e ON m.fk_estufas_estufa_id = e.estufa_id
ORDER BY le.data_hora DESC;
            """,
            "desc": "Histórico de erros de hardware registrados com os dados da estufa de origem."
        },
        "Consulta 5: Leituras que Estouraram Limites do Cultivo": {
            "sql": """
SELECT 
    ll.data_hora,
    s.nome AS sensor_nome,
    s.tipo AS sensor_tipo,
    ll.valor AS valor_lido,
    s.unidade_medida,
    c.nome AS cultivo_nome,
    CASE 
        WHEN s.tipo = 'pH' THEN c.ph_min 
        WHEN s.tipo = 'CE' THEN c.ce_min 
    END AS limite_minimo,
    CASE 
        WHEN s.tipo = 'pH' THEN c.ph_max 
        WHEN s.tipo = 'CE' THEN c.ce_max 
    END AS limite_maximo
FROM log_leituras ll
JOIN sensores s ON ll.sensor_id = s.sensor_id
JOIN ciclos_ativos ca ON s.fk_setores_setor_id = ca.fk_setores_setor_id
JOIN catalogo_cultivos c ON ca.fk_catalogo_cultivos_cultivo_id = c.cultivo_id
WHERE ca.data_fim IS NULL
  AND (
      (s.tipo = 'pH' AND (ll.valor < c.ph_min OR ll.valor > c.ph_max))
      OR 
      (s.tipo = 'CE' AND (ll.valor < c.ce_min OR ll.valor > c.ce_max))
  )
ORDER BY ll.data_hora DESC;
            """,
            "desc": "Identifica medições críticas que extrapolaram a faixa recomendada para o cultivo ativo."
        },
        "Consulta 6: Frequência de Comandos por Atuador e Origem": {
            "sql": """
SELECT 
    a.nome AS atuador_nome,
    a.tipo AS atuador_tipo,
    COALESCE(s.nome, 'Estufa: ' || e.nome) AS localizacao,
    lc.origem,
    COUNT(lc.data_hora) AS total_comandos
FROM log_comandos lc
JOIN atuadores a ON lc.atuador_id = a.atuador_id
LEFT JOIN setores s ON a.fk_setores_setor_id = s.setor_id
LEFT JOIN estufas e ON a.fk_estufas_estufa_id = e.estufa_id
GROUP BY a.nome, a.tipo, s.nome, e.nome, lc.origem
HAVING COUNT(lc.data_hora) > 1
ORDER BY total_comandos DESC;
            """,
            "desc": "Contagem de acionamentos por bomba ou válvula agrupados por origem (Manual/Automático)."
        },
        "Consulta 7: Rastreabilidade Completa de Leituras": {
            "sql": """
SELECT 
    l.data_hora,
    s.nome AS sensor_nome,
    s.tipo AS sensor_tipo,
    l.valor || ' ' || s.unidade_medida AS leitura,
    setor.nome AS setor_origem,
    e.nome AS estufa_origem,
    m.mac_address AS esp32_mac
FROM log_leituras l
JOIN sensores s ON l.sensor_id = s.sensor_id
JOIN setores setor ON s.fk_setores_setor_id = setor.setor_id
JOIN estufas e ON setor.fk_estufas_estufa_id = e.estufa_id
JOIN microcontroladores m ON s.fk_microcontroladores_micro_id = m.micro_id
ORDER BY l.data_hora DESC;
            """,
            "desc": "Rastreamento completo da medição conectando o Sensor ao Setor, Estufa e ESP32."
        },
        "Consulta 8: Histórico de Comandos em Atuadores": {
            "sql": """
SELECT 
    lc.data_hora,
    a.nome AS atuador_nome,
    a.tipo AS tipo_atuador,
    lc.estado,
    lc.origem,
    COALESCE(s.nome, 'Estufa Geral: ' || e.nome) AS localizacao
FROM log_comandos lc
JOIN atuadores a ON lc.atuador_id = a.atuador_id
LEFT JOIN setores s ON a.fk_setores_setor_id = s.setor_id
LEFT JOIN estufas e ON a.fk_estufas_estufa_id = e.estufa_id
ORDER BY lc.data_hora DESC;
            """,
            "desc": "Relatório detalhado de comandos enviados aos atuadores com a localização exata."
        },
        "Consulta 9: Mapeamento de Estufas, Setores e Dispositivos": {
            "sql": """
SELECT 
    e.nome AS estufa_nome,
    e.localizacao,
    s.nome AS setor_nome,
    m.mac_address AS esp32_mac,
    m.descricao AS esp32_descricao,
    m.ultima_comunicacao
FROM estufas e
LEFT JOIN setores s ON s.fk_setores_setor_id = e.estufa_id
LEFT JOIN microcontroladores m ON m.fk_estufas_estufa_id = e.estufa_id
ORDER BY e.estufa_id;
            """,
            "desc": "Visão geral da infraestrutura mapeando Estufas, Setores e Dispositivos ESP32 conectados."
        }
    }

    sc = st.selectbox("Escolha uma Consulta para Executar:", list(consultas_dict.keys()))
    st.info(f"**Descrição:** {consultas_dict[sc]['desc']}")
    
    with st.expander("Ver Código SQL da Consulta"):
        st.code(consultas_dict[sc]["sql"], language="sql")

    if st.button("Executar Consulta SQL"):
        res_df, err = run_query(consultas_dict[sc]["sql"])
        if err:
            st.error(f"Erro na execução da consulta: {err}")
        else:
            st.success(f"Consulta executada com sucesso! Retornou {len(res_df)} linha(s).")
            st.dataframe(res_df, use_container_width=True)

# ------------------------------------------
# ABA 4: INSERÇÕES & CADASTROS
# ------------------------------------------
with aba4:
    st.subheader("Cadastro e Inserção de Dados")
    
    tipo_ins = st.radio("Selecione o que deseja cadastrar:", [
        "Nova Estufa", 
        "Novo ESP32 (Microcontrolador)", 
        "Novo Atuador (Bomba / Válvula)", 
        "Novo Cultivo no Catálogo",
        "Nova Leitura de Sensor"
    ], horizontal=True)

    # 1. NOVA ESTUFA
    if tipo_ins == "Nova Estufa":
        st.markdown("#### Cadastrar Nova Estufa no Sistema")
        with st.form("form_estufa", clear_on_submit=True):
            nome_e = st.text_input("Nome da Estufa (Ex: Estufa Didática Leste)")
            loc_e = st.text_input("Localização (Ex: Campus Capão do Leão)")
            data_e = datetime.now().strftime("%Y-%m-%d")
            
            if st.form_submit_button("Salvar Estufa"):
                if not nome_e:
                    st.warning("Preencha o nome da estufa!")
                else:
                    ok, msg = execute_statement("INSERT INTO estufas (nome, data_criacao, localizacao) VALUES (?, ?, ?);", (nome_e, data_e, loc_e))
                    if ok:
                        st.success(f"Estufa '{nome_e}' cadastrada com sucesso!")
                    else:
                        st.error(f"Erro: {msg}")
        
        st.divider()
        st.write("#### Estufas Atuais:")
        df_e_cur, _ = run_query("SELECT * FROM estufas ORDER BY estufa_id DESC;")
        if df_e_cur is not None:
            st.dataframe(df_e_cur, use_container_width=True)

    # 2. NOVO ESP32
    elif tipo_ins == "Novo ESP32 (Microcontrolador)":
        st.markdown("#### Cadastrar Novo ESP32")
        df_estufas_sel, _ = run_query("SELECT estufa_id, nome FROM estufas ORDER BY estufa_id;")
        if df_estufas_sel is not None and not df_estufas_sel.empty:
            e_map = {f"ID {r['estufa_id']} - {r['nome']}": r['estufa_id'] for _, r in df_estufas_sel.iterrows()}
            with st.form("form_esp", clear_on_submit=True):
                mac_esp = st.text_input("MAC Address (Ex: 00:1A:2B:3C:4D:99)")
                desc_esp = st.text_input("Descrição do Dispositivo (Ex: Controlador Secundário)")
                estufa_esp = st.selectbox("Vincular à Estufa:", list(e_map.keys()))
                
                if st.form_submit_button("Salvar ESP32"):
                    if not mac_esp:
                        st.warning("Preencha o MAC Address!")
                    else:
                        id_e = e_map[estufa_esp]
                        ok, msg = execute_statement("""
                            INSERT INTO microcontroladores (mac_address, descricao, fk_estufas_estufa_id)
                            VALUES (?, ?, ?);
                        """, (mac_esp, desc_esp, id_e))
                        if ok:
                            st.success(f"ESP32 '{mac_esp}' cadastrado com sucesso!")
                        else:
                            st.error(f"Erro: {msg}")
        else:
            st.warning("Cadastre uma estufa primeiro!")

        st.divider()
        st.write("#### Dispositivos Cadastrados:")
        df_esp_cur, _ = run_query("SELECT * FROM microcontroladores ORDER BY micro_id DESC;")
        if df_esp_cur is not None:
            st.dataframe(df_esp_cur, use_container_width=True)

    # 3. NOVO ATUADOR (Respeitando a Constraint CHECK Bomba/Valvula)
    elif tipo_ins == "Novo Atuador (Bomba / Válvula)":
        st.markdown("#### Cadastrar Novo Atuador")
        st.info("**Regra de Banco (CHECK):** Se for **Bomba**, o vínculo é com a **Estufa Geral**. Se for **Válvula**, o vínculo é com o **Setor** específico.")
        
        df_micros_sel, _ = run_query("SELECT micro_id, descricao FROM microcontroladores ORDER BY micro_id;")
        df_estufas_all, _ = run_query("SELECT estufa_id, nome FROM estufas ORDER BY estufa_id;")
        df_setores_all, _ = run_query("SELECT setor_id, nome FROM setores ORDER BY setor_id;")
        
        if df_micros_sel is not None and not df_micros_sel.empty:
            m_map = {f"ID {r['micro_id']} - {r['descricao']}": r['micro_id'] for _, r in df_micros_sel.iterrows()}
            
            nome_atu = st.text_input("Nome do Atuador (Ex: Bomba Auxiliar / Válvula Setor 2)")
            tipo_atu = st.radio("Tipo de Atuador:", ["Bomba", "Valvula"], horizontal=True)
            pino_atu = st.number_input("Pino Digital (GPIO):", value=25, step=1)
            esp_atu = st.selectbox("Microcontrolador ESP32:", list(m_map.keys()))
            
            fk_e_val = None
            fk_s_val = None
            
            if tipo_atu == "Bomba":
                e_map_a = {f"ID {r['estufa_id']} - {r['nome']}": r['estufa_id'] for _, r in df_estufas_all.iterrows()}
                sel_e_a = st.selectbox("Selecione a Estufa (Obrigatório para Bomba):", list(e_map_a.keys()))
                fk_e_val = e_map_a[sel_e_a]
            else:
                s_map_a = {f"ID {r['setor_id']} - {r['nome']}": r['setor_id'] for _, r in df_setores_all.iterrows()}
                sel_s_a = st.selectbox("Selecione o Setor (Obrigatório para Válvula):", list(s_map_a.keys()))
                fk_s_val = s_map_a[sel_s_a]
                
            if st.button("Cadastrar Atuador"):
                if not nome_atu:
                    st.warning("Preencha o nome do atuador!")
                else:
                    id_m = m_map[esp_atu]
                    ok, msg = execute_statement("""
                        INSERT INTO atuadores (nome, tipo, pino_digital, fk_microcontroladores_micro_id, fk_estufas_estufa_id, fk_setores_setor_id)
                        VALUES (?, ?, ?, ?, ?, ?);
                    """, (nome_atu, tipo_atu, int(pino_atu), id_m, fk_e_val, fk_s_val))
                    if ok:
                        st.success(f"Atuador '{nome_atu}' ({tipo_atu}) cadastrado com sucesso!")
                    else:
                        st.error(f"Erro no Banco (Constraint): {msg}")
        else:
            st.warning("Cadastre um microcontrolador ESP32 primeiro!")

        st.divider()
        st.write("#### Atuadores Cadastrados:")
        df_atu_cur, _ = run_query("SELECT * FROM atuadores ORDER BY atuador_id DESC;")
        if df_atu_cur is not None:
            st.dataframe(df_atu_cur, use_container_width=True)

    # 4. NOVO CULTIVO
    elif tipo_ins == "Novo Cultivo no Catálogo":
        st.markdown("#### Cadastrar Nova Espécie Vegetal")
        with st.form("form_cultivo", clear_on_submit=True):
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                nome_c = st.text_input("Nome do Cultivo (Ex: Rúcula Hydro)")
                ph_min_c = st.number_input("pH Mínimo", value=5.5, step=0.1)
                ph_max_c = st.number_input("pH Máximo", value=6.5, step=0.1)
            with col_c2:
                ce_min_c = st.number_input("CE Mínimo (mS/cm)", value=1.5, step=0.1)
                ce_max_c = st.number_input("CE Máximo (mS/cm)", value=2.5, step=0.1)
                temp_c = st.number_input("Temperatura Ideal (°C)", value=22.0, step=0.5)
            
            btn_cad = st.form_submit_button("Salvar Cultivo")
            if btn_cad:
                if not nome_c:
                    st.warning("Preencha o nome do cultivo!")
                else:
                    sql_ins = "INSERT INTO catalogo_cultivos (nome, ph_min, ph_max, ce_min, ce_max, temp_ideal) VALUES (?, ?, ?, ?, ?, ?);"
                    ok, msg = execute_statement(sql_ins, (nome_c, ph_min_c, ph_max_c, ce_min_c, ce_max_c, temp_c))
                    if ok:
                        st.success(f"Cultivo '{nome_c}' cadastrado com sucesso!")
                    else:
                        st.error(f"Erro: {msg}")

        st.divider()
        st.write("#### Catálogo de Cultivos Atual:")
        df_cat, _ = run_query("SELECT * FROM catalogo_cultivos ORDER BY cultivo_id DESC;")
        if df_cat is not None:
            st.dataframe(df_cat, use_container_width=True)

    # 5. NOVA LEITURA
    elif tipo_ins == "Nova Leitura de Sensor":
        st.markdown("#### Inserir Leitura Manual em Sensor")
        sensors_df, _ = run_query("SELECT sensor_id, nome, tipo, unidade_medida FROM sensores ORDER BY sensor_id;")
        if sensors_df is not None and not sensors_df.empty:
            s_dict = {f"ID {r['sensor_id']} - {r['nome']} ({r['tipo']})": r['sensor_id'] for _, r in sensors_df.iterrows()}
            s_choice = st.selectbox("Selecione o Sensor:", list(s_dict.keys()))
            val_lido = st.number_input("Valor Lido:", value=6.0, step=0.1)
            
            if st.button("Registrar Leitura"):
                sid = s_dict[s_choice]
                agora_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                sql_lei = "INSERT INTO log_leituras (sensor_id, data_hora, valor) VALUES (?, ?, ?);"
                ok, msg = execute_statement(sql_lei, (sid, agora_str, val_lido))
                if ok:
                    st.success("Leitura registrada com sucesso! (O gatilho atualizou a comunicação e checou os limites).")
                else:
                    st.error(f"Erro ao registrar leitura: {msg}")

# ------------------------------------------
# ABA 5: GATILHOS E TRIGGERS EM AÇÃO
# ------------------------------------------
with aba5:
    st.subheader("Demonstração Prática dos Gatilhos (Triggers)")
    st.markdown("Demonstração ao vivo da execução autônoma dos gatilhos no banco SQLite.")

    tab_g1, tab_g3, tab_g4 = st.tabs([
        "Gatilho 1 & 2: Atualização de ESP32", 
        "Gatilho 3: Validação de Ciclos", 
        "Gatilho 4: Alertas de Segurança"
    ])

    with tab_g1:
        st.markdown('<span class="trigger-badge">TRIGGER: trg_atualizar_comunicacao_sensor</span>', unsafe_allow_html=True)
        st.write("""
        **Regra do Gatilho:** Sempre que uma nova leitura entra em `log_leituras`, o gatilho descobre qual ESP32 é o dono daquele sensor e atualiza automaticamente a coluna `ultima_comunicacao` do microcontrolador com o `timestamp` exato da leitura.
        """)
        
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            st.write("##### Estado dos ESP32 (Antes/Agora):")
            df_before, _ = run_query("SELECT micro_id, mac_address, descricao, ultima_comunicacao FROM microcontroladores ORDER BY micro_id;")
            st.dataframe(df_before, use_container_width=True)
        
        with col_t2:
            st.write("##### Disparar Gatilho:")
            sensors_df, _ = run_query("SELECT sensor_id, nome FROM sensores ORDER BY sensor_id;")
            if sensors_df is not None and not sensors_df.empty:
                s_map = {f"Sensor {r['sensor_id']} ({r['nome']})": r['sensor_id'] for _, r in sensors_df.iterrows()}
                s_sel = st.selectbox("Escolha o sensor:", list(s_map.keys()), key="g1_sens")
                val_test = st.number_input("Valor da medição:", value=24.5, key="g1_val")
                
                if st.button("Inserir e Ver Gatilho Atualizar o ESP32"):
                    sid = s_map[s_sel]
                    agora_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    ok, msg = execute_statement("INSERT INTO log_leituras (sensor_id, data_hora, valor) VALUES (?, ?, ?);", (sid, agora_str, val_test))
                    if ok:
                        st.success("Leitura inserida! O gatilho atualizou a coluna 'ultima_comunicacao' instantaneamente abaixo:")
                        df_after, _ = run_query("SELECT micro_id, mac_address, descricao, ultima_comunicacao FROM microcontroladores ORDER BY micro_id;")
                        st.dataframe(df_after, use_container_width=True)
                    else:
                        st.error(f"Erro: {msg}")

    with tab_g3:
        st.markdown('<span class="trigger-badge">TRIGGER: trg_validar_ciclo_ativo</span>', unsafe_allow_html=True)
        st.write("""
        **Regra do Gatilho:** Impede que um mesmo setor de estufa tenha **2 ciclos agrícolas ativos** (sem `data_fim`) ao mesmo tempo. Se tentar, o gatilho interrompe a ação com `RAISE(ABORT)`.
        """)
        
        df_ciclos, _ = run_query("""
            SELECT ca.ciclo_id, s.nome AS setor, c.nome AS cultivo, ca.data_inicio, ca.data_fim 
            FROM ciclos_ativos ca
            JOIN setores s ON ca.fk_setores_setor_id = s.setor_id
            JOIN catalogo_cultivos c ON ca.fk_catalogo_cultivos_cultivo_id = c.cultivo_id
            WHERE ca.data_fim IS NULL;
        """)
        st.write("##### Ciclos Atualmente Ativos nos Setores:")
        st.dataframe(df_ciclos, use_container_width=True)
        
        st.write("##### Teste de Bloqueio (Tentar Inserir Duplicado):")
        setores_df, _ = run_query("SELECT setor_id, nome FROM setores ORDER BY setor_id;")
        cultivos_df, _ = run_query("SELECT cultivo_id, nome FROM catalogo_cultivos ORDER BY cultivo_id;")
        
        if setores_df is not None and cultivos_df is not None:
            set_map = {r['nome']: r['setor_id'] for _, r in setores_df.iterrows()}
            cul_map = {r['nome']: r['cultivo_id'] for _, r in cultivos_df.iterrows()}
            
            sel_setor = st.selectbox("Escolha um setor:", list(set_map.keys()))
            sel_cultivo = st.selectbox("Escolha um cultivo:", list(cul_map.keys()))
            
            if st.button("Tentar Cadastrar 2º Ciclo neste Setor"):
                id_s = set_map[sel_setor]
                id_c = cul_map[sel_cultivo]
                hoje_str = datetime.now().strftime("%Y-%m-%d")
                ok, msg = execute_statement("""
                    INSERT INTO ciclos_ativos (data_inicio, fk_catalogo_cultivos_cultivo_id, fk_setores_setor_id)
                    VALUES (?, ?, ?);
                """, (hoje_str, id_c, id_s))
                
                if ok:
                    st.warning("O ciclo foi inserido (significa que o setor não tinha ciclo ativo).")
                else:
                    st.error(f"BLOQUEADO PELO GATILHO!\nMensagem do Banco de Dados:\n{msg}")

    with tab_g4:
        st.markdown('<span class="trigger-badge">TRIGGER: trg_verificar_leituras_alertas</span>', unsafe_allow_html=True)
        st.write("""
        **Regra do Gatilho:** Quando uma leitura de pH ou CE entra, se o valor estiver **fora dos limites mínimo/máximo do cultivo ativo** daquele setor, o gatilho cria autonomamente um registro na tabela `alertas_seguranca`.
        """)
        
        st.write("##### Simular Leitura com Anomalia (Ex: pH Muito Alto ou Muito Baixo):")
        
        col_a1, col_a2 = st.columns(2)
        with col_a1:
            sensores_ph, _ = run_query("SELECT sensor_id, nome FROM sensores WHERE tipo IN ('pH', 'CE') ORDER BY sensor_id;")
            if sensores_ph is not None and not sensores_ph.empty:
                ph_map = {f"ID {r['sensor_id']} - {r['nome']}": r['sensor_id'] for _, r in sensores_ph.iterrows()}
                ph_sel = st.selectbox("Sensor de pH / CE:", list(ph_map.keys()))
                val_anomalo = st.number_input("Valor Extremo/Anômalo (Ex: pH 11.5 ou 2.0):", value=11.5, step=0.5)
                
                if st.button("Inserir Leitura Anômala"):
                    sid = ph_map[ph_sel]
                    agora_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    ok, msg = execute_statement("INSERT INTO log_leituras (sensor_id, data_hora, valor) VALUES (?, ?, ?);", (sid, agora_str, val_anomalo))
                    if ok:
                        st.success("Leitura gravada! Verifique o alerta gerado automaticamente ao lado ->")
                    else:
                        st.error(f"Erro: {msg}")
        
        with col_a2:
            st.write("##### Tabela `alertas_seguranca` (Gerada por Gatilho):")
            df_alertas, _ = run_query("SELECT * FROM alertas_seguranca ORDER BY alerta_id DESC LIMIT 10;")
            st.dataframe(df_alertas, use_container_width=True)
