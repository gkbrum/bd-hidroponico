-- consulta 1: todos sensores de temperatura
SELECT sensor_id, nome, pino_digital, unidade_medida
FROM sensores
WHERE tipo = 'Temperatura'
ORDER BY nome;

-- consulta 2: cultivos com ph min >= 5.5 e temp ideal < 22
SELECT cultivo_id, nome, ph_min, ph_max, temp_ideal
FROM catalogo_cultivos
WHERE ph_min >= 5.5 AND temp_ideal < 22.0;

-- consulta 3: mostrar o que ta plantado em cada setor e estufa agora
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

-- consulta 4: log de erros com detalhes do esp32 e da estufa
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

-- consulta 5: leituras que estouraram os limites do catalogo pro ciclo ativo
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

-- consulta 6: quantidade de comandos por atuador e origem (mais de 1)
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

-- ============================================================================
-- CONSULTAS ADICIONAIS DE RASTREABILIDADE E INTERFACE (UTILIZADAS NO DASHBOARD)
-- ============================================================================

-- consulta 7: Rastreabilidade completa de leituras (Sensor -> Setor -> Estufa -> ESP32)
-- SELECT 
--     l.data_hora,
--     s.nome AS sensor_nome,
--     s.tipo AS sensor_tipo,
--     l.valor || ' ' || s.unidade_medida AS leitura,
--     setor.nome AS setor_origem,
--     e.nome AS estufa_origem,
--     m.mac_address AS esp32_mac
-- FROM log_leituras l
-- JOIN sensores s ON l.sensor_id = s.sensor_id
-- JOIN setores setor ON s.fk_setores_setor_id = setor.setor_id
-- JOIN estufas e ON setor.fk_estufas_estufa_id = e.estufa_id
-- JOIN microcontroladores m ON s.fk_microcontroladores_micro_id = m.micro_id
-- ORDER BY l.data_hora DESC;

-- consulta 8: Histórico detalhado de acionamentos de atuadores com localização (Setor ou Estufa)
-- SELECT 
--     lc.data_hora,
--     a.nome AS atuador_nome,
--     a.tipo AS tipo_atuador,
--     lc.estado,
--     lc.origem,
--     COALESCE(s.nome, 'Estufa Geral: ' || e.nome) AS localizacao
-- FROM log_comandos lc
-- JOIN atuadores a ON lc.atuador_id = a.atuador_id
-- LEFT JOIN setores s ON a.fk_setores_setor_id = s.setor_id
-- LEFT JOIN estufas e ON a.fk_estufas_estufa_id = e.estufa_id
-- ORDER BY lc.data_hora DESC;

-- consulta 9: Mapeamento completo de estufas, setores e microcontroladores conectados
-- SELECT 
--     e.nome AS estufa_nome,
--     e.localizacao,
--     s.nome AS setor_nome,
--     m.mac_address AS esp32_mac,
--     m.descricao AS esp32_descricao,
--     m.ultima_comunicacao
-- FROM estufas e
-- LEFT JOIN setores s ON s.fk_estufas_estufa_id = e.estufa_id
-- LEFT JOIN microcontroladores m ON m.fk_estufas_estufa_id = e.estufa_id
-- ORDER BY e.estufa_id;
