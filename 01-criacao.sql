-- estufas
CREATE TABLE estufas (
    estufa_id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    data_criacao DATE,
    localizacao VARCHAR(255)
);

-- esp32
CREATE TABLE microcontroladores (
    micro_id SERIAL PRIMARY KEY,
    mac_address VARCHAR(17) UNIQUE NOT NULL,
    descricao VARCHAR(255),
    ultima_comunicacao TIMESTAMP,
    fk_estufas_estufa_id INTEGER NOT NULL,
    CONSTRAINT FK_microcontroladores_estufas FOREIGN KEY (fk_estufas_estufa_id)
        REFERENCES estufas (estufa_id) ON DELETE CASCADE
);

-- setores
CREATE TABLE setores (
    setor_id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    fk_estufas_estufa_id INTEGER NOT NULL,
    CONSTRAINT FK_setores_estufas FOREIGN KEY (fk_estufas_estufa_id)
        REFERENCES estufas (estufa_id) ON DELETE CASCADE
);

-- sensores
CREATE TABLE sensores (
    sensor_id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    tipo VARCHAR(50),
    pino_digital INTEGER,
    unidade_medida VARCHAR(20),
    fk_microcontroladores_micro_id INTEGER NOT NULL,
    fk_setores_setor_id INTEGER NOT NULL,
    CONSTRAINT FK_sensores_microcontroladores FOREIGN KEY (fk_microcontroladores_micro_id)
        REFERENCES microcontroladores (micro_id) ON DELETE RESTRICT,
    CONSTRAINT FK_sensores_setores FOREIGN KEY (fk_setores_setor_id)
        REFERENCES setores (setor_id) ON DELETE CASCADE
);

-- atuadores (bomba na estufa, valvula no setor)
CREATE TABLE atuadores (
    atuador_id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    tipo VARCHAR(50) NOT NULL, -- 'Bomba' ou 'Valvula'
    pino_digital INTEGER,
    fk_microcontroladores_micro_id INTEGER NOT NULL,
    fk_setores_setor_id INTEGER, -- NULL se for Bomba
    fk_estufas_estufa_id INTEGER, -- NULL se for Valvula
    CONSTRAINT FK_atuadores_microcontroladores FOREIGN KEY (fk_microcontroladores_micro_id)
        REFERENCES microcontroladores (micro_id) ON DELETE RESTRICT,
    CONSTRAINT FK_atuadores_setores FOREIGN KEY (fk_setores_setor_id)
        REFERENCES setores (setor_id) ON DELETE CASCADE,
    CONSTRAINT FK_atuadores_estufas FOREIGN KEY (fk_estufas_estufa_id)
        REFERENCES estufas (estufa_id) ON DELETE CASCADE,
    CONSTRAINT CK_atuador_localizacao CHECK (
        (tipo = 'Bomba' AND fk_estufas_estufa_id IS NOT NULL AND fk_setores_setor_id IS NULL) OR
        (tipo = 'Valvula' AND fk_setores_setor_id IS NOT NULL AND fk_estufas_estufa_id IS NULL)
    )
);

-- log leituras
CREATE TABLE log_leituras (
    sensor_id INTEGER NOT NULL,
    data_hora TIMESTAMP NOT NULL,
    valor FLOAT NOT NULL,
    PRIMARY KEY (sensor_id, data_hora),
    CONSTRAINT FK_log_leituras_sensores FOREIGN KEY (sensor_id)
        REFERENCES sensores (sensor_id) ON DELETE CASCADE
);

-- log comandos
CREATE TABLE log_comandos (
    atuador_id INTEGER NOT NULL,
    data_hora TIMESTAMP NOT NULL,
    estado VARCHAR(10) NOT NULL,
    origem VARCHAR(50),
    PRIMARY KEY (atuador_id, data_hora),
    CONSTRAINT FK_log_comandos_atuadores FOREIGN KEY (atuador_id)
        REFERENCES atuadores (atuador_id) ON DELETE CASCADE
);

-- catalogo
CREATE TABLE catalogo_cultivos (
    cultivo_id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    ph_min FLOAT,
    ph_max FLOAT,
    ce_min FLOAT,
    ce_max FLOAT,
    temp_ideal FLOAT
);

-- ciclos
CREATE TABLE ciclos_ativos (
    ciclo_id SERIAL PRIMARY KEY,
    data_inicio DATE NOT NULL,
    data_fim DATE,
    fk_catalogo_cultivos_cultivo_id INTEGER NOT NULL,
    fk_setores_setor_id INTEGER NOT NULL,
    CONSTRAINT FK_ciclos_ativos_cultivos FOREIGN KEY (fk_catalogo_cultivos_cultivo_id)
        REFERENCES catalogo_cultivos (cultivo_id) ON DELETE RESTRICT,
    CONSTRAINT FK_ciclos_ativos_setores FOREIGN KEY (fk_setores_setor_id)
        REFERENCES setores (setor_id) ON DELETE RESTRICT
);

-- so 1 ativo por vez
CREATE UNIQUE INDEX idx_setor_ciclo_ativo 
ON ciclos_ativos (fk_setores_setor_id) 
WHERE (data_fim IS NULL);

-- erros
CREATE TABLE log_erros (
    id_dispositivo INTEGER NOT NULL,
    data_hora TIMESTAMP NOT NULL,
    cod_erro INTEGER,
    mensagem VARCHAR(255),
    PRIMARY KEY (id_dispositivo, data_hora),
    CONSTRAINT FK_log_erros_microcontroladores FOREIGN KEY (id_dispositivo)
        REFERENCES microcontroladores (micro_id) ON DELETE CASCADE
);

-- alertas de seguranca
CREATE TABLE alertas_seguranca (
    alerta_id SERIAL PRIMARY KEY,
    sensor_id INTEGER NOT NULL,
    data_hora TIMESTAMP NOT NULL,
    valor FLOAT NOT NULL,
    mensagem VARCHAR(255) NOT NULL,
    CONSTRAINT FK_alertas_seguranca_sensores FOREIGN KEY (sensor_id)
        REFERENCES sensores (sensor_id) ON DELETE CASCADE
);