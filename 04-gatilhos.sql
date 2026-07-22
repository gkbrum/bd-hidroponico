-- gatilho 1: quando entra leitura de sensor, atualiza ultima_comunicacao do esp
CREATE OR REPLACE FUNCTION atualizar_ultima_comunicacao_sensor()
RETURNS TRIGGER AS $$
DECLARE
    v_micro_id INTEGER;
BEGIN
    SELECT fk_microcontroladores_micro_id INTO v_micro_id
    FROM sensores
    WHERE sensor_id = NEW.sensor_id;
    
    IF v_micro_id IS NOT NULL THEN
        UPDATE microcontroladores
        SET ultima_comunicacao = NEW.data_hora
        WHERE micro_id = v_micro_id;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trg_atualizar_comunicacao_sensor
AFTER INSERT ON log_leituras
FOR EACH ROW
EXECUTE FUNCTION atualizar_ultima_comunicacao_sensor();


-- gatilho 2: quando manda comando pro atuador, atualiza ultima_comunicacao do esp
CREATE OR REPLACE FUNCTION atualizar_ultima_comunicacao_atuador()
RETURNS TRIGGER AS $$
DECLARE
    v_micro_id INTEGER;
BEGIN
    SELECT fk_microcontroladores_micro_id INTO v_micro_id
    FROM atuadores
    WHERE atuador_id = NEW.atuador_id;
    
    IF v_micro_id IS NOT NULL THEN
        UPDATE microcontroladores
        SET ultima_comunicacao = NEW.data_hora
        WHERE micro_id = v_micro_id;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trg_atualizar_comunicacao_atuador
AFTER INSERT ON log_comandos
FOR EACH ROW
EXECUTE FUNCTION atualizar_ultima_comunicacao_atuador();


-- gatilho 3: nao deixa ter dois ciclos ativos no mesmo setor
CREATE OR REPLACE FUNCTION validar_ciclo_ativo_setor()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.data_fim IS NULL THEN
        IF EXISTS (
            SELECT 1 
            FROM ciclos_ativos 
            WHERE fk_setores_setor_id = NEW.fk_setores_setor_id 
              AND data_fim IS NULL 
              AND ciclo_id <> NEW.ciclo_id
        ) THEN
            RAISE EXCEPTION 'erro: o setor % ja tem um ciclo ativo. finaliza o outro primeiro.', 
                NEW.fk_setores_setor_id;
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trg_validar_ciclo_ativo
BEFORE INSERT OR UPDATE ON ciclos_ativos
FOR EACH ROW
EXECUTE FUNCTION validar_ciclo_ativo_setor();


-- procedimento de verdade (procedure) chamado pelo gatilho 4 para segurança
CREATE OR REPLACE PROCEDURE verificar_limites_leitura(
    p_sensor_id INTEGER, 
    p_data_hora TIMESTAMP, 
    p_valor FLOAT
)
AS $$
DECLARE
    v_tipo VARCHAR(50);
    v_ph_min FLOAT;
    v_ph_max FLOAT;
    v_ce_min FLOAT;
    v_ce_max FLOAT;
    v_cultivo_nome VARCHAR(100);
BEGIN
    -- tipo do sensor
    SELECT tipo INTO v_tipo FROM sensores WHERE sensor_id = p_sensor_id;
    
    -- limites do cultivo ativo pro setor do sensor
    SELECT c.nome, c.ph_min, c.ph_max, c.ce_min, c.ce_max 
    INTO v_cultivo_nome, v_ph_min, v_ph_max, v_ce_min, v_ce_max
    FROM sensores s
    JOIN ciclos_ativos ca ON s.fk_setores_setor_id = ca.fk_setores_setor_id
    JOIN catalogo_cultivos c ON ca.fk_catalogo_cultivos_cultivo_id = c.cultivo_id
    WHERE s.sensor_id = p_sensor_id AND ca.data_fim IS NULL;
    
    -- se achar cultivo ativo, checa os limites de ph ou ce
    IF v_cultivo_nome IS NOT NULL THEN
        IF v_tipo = 'pH' AND (p_valor < v_ph_min OR p_valor > v_ph_max) THEN
            INSERT INTO alertas_seguranca (sensor_id, data_hora, valor, mensagem)
            VALUES (p_sensor_id, p_data_hora, p_valor, 
                    'ALERTA pH fora da faixa para ' || v_cultivo_nome || ' (limites: ' || v_ph_min || '-' || v_ph_max || ', lido: ' || p_valor || ')');
        ELSIF v_tipo = 'CE' AND (p_valor < v_ce_min OR p_valor > v_ce_max) THEN
            INSERT INTO alertas_seguranca (sensor_id, data_hora, valor, mensagem)
            VALUES (p_sensor_id, p_data_hora, p_valor, 
                    'ALERTA CE fora da faixa para ' || v_cultivo_nome || ' (limites: ' || v_ce_min || '-' || v_ce_max || ', lido: ' || p_valor || ')');
        END IF;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- gatilho 4: chama o procedimento de alerta apos inserir leitura
CREATE OR REPLACE FUNCTION trg_func_verificar_leituras()
RETURNS TRIGGER AS $$
BEGIN
    CALL verificar_limites_leitura(NEW.sensor_id, NEW.data_hora, NEW.valor);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trg_verificar_leituras
AFTER INSERT ON log_leituras
FOR EACH ROW
EXECUTE FUNCTION trg_func_verificar_leituras();
