-- estufas (ids gerados: 1, 2)
INSERT INTO estufas (nome, data_criacao, localizacao) VALUES
('Estufa Principal (Norte)', '2026-01-10', 'Setor Norte - UFPel Campus Capão do Leão'),
('Estufa Experimental (Sul)', '2026-03-15', 'Setor Sul - UFPel Campus Capão do Leão');

-- esp32 (ids gerados: 1, 2, 3)
INSERT INTO microcontroladores (mac_address, descricao, ultima_comunicacao, fk_estufas_estufa_id) VALUES
('00:1A:2B:3C:4D:5E', 'Controlador Estufa Norte - Principal', '2026-07-16 23:00:00', 1),
('00:1A:2B:3C:4D:5F', 'Controlador Estufa Norte - Auxiliar', '2026-07-16 23:15:00', 1),
('11:22:33:44:55:66', 'Controlador Estufa Sul - Geral', '2026-07-16 22:50:00', 2);

-- setores (ids gerados: 1, 2, 3)
INSERT INTO setores (nome, fk_estufas_estufa_id) VALUES
('Setor Alpha', 1),
('Setor Beta', 1),
('Setor Gamma', 2);

-- sensores (ids gerados: 1, 2, 3, 4, 5)
INSERT INTO sensores (nome, tipo, pino_digital, unidade_medida, fk_microcontroladores_micro_id, fk_setores_setor_id) VALUES
('Sensor de Temp Alpha', 'Temperatura', 32, '°C', 1, 1),
('Sensor de Umidade Alpha', 'Umidade', 33, '%', 1, 1),
('Sensor de pH Alpha', 'pH', 34, 'pH', 2, 1),
('Sensor de CE Alpha', 'CE', 35, 'S/m', 2, 1),
('Sensor de Temp Gamma', 'Temperatura', 32, '°C', 3, 3);

-- atuadores (ids gerados: 1, 2, 3, 4)
-- bomba na estufa, valvula no setor
INSERT INTO atuadores (nome, tipo, pino_digital, fk_microcontroladores_micro_id, fk_estufas_estufa_id, fk_setores_setor_id) VALUES
('Bomba de Mistura Alpha', 'Bomba', 25, 1, 1, NULL),
('Válvula Solenoide Alpha', 'Valvula', 26, 1, NULL, 1),
('Válvula Solenoide Beta', 'Valvula', 27, 2, NULL, 2),
('Bomba de Mistura Gamma', 'Bomba', 25, 3, 2, NULL);

-- catalogo (ids gerados: 1, 2, 3)
INSERT INTO catalogo_cultivos (nome, ph_min, ph_max, ce_min, ce_max, temp_ideal) VALUES
('Morango Silvestre', 5.5, 6.5, 1.4, 1.8, 20.0),
('Alface Americana', 6.0, 7.0, 1.2, 1.6, 18.0),
('Tomate Cereja', 5.8, 6.8, 2.0, 2.5, 22.0);

-- ciclos (ids gerados: 1, 2, 3)
INSERT INTO ciclos_ativos (data_inicio, data_fim, fk_catalogo_cultivos_cultivo_id, fk_setores_setor_id) VALUES
('2026-05-01', '2026-06-15', 2, 1),
('2026-06-20', NULL, 1, 1),
('2026-07-01', NULL, 3, 3);

-- logs (sensor 1, 3, 4)
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

-- comandos (atuador 1, 2)
INSERT INTO log_comandos (atuador_id, data_hora, estado, origem) VALUES
(1, '2026-07-16 23:01:00', 'LIGADO', 'AUTOMATICO'),
(1, '2026-07-16 23:06:00', 'DESLIGADO', 'AUTOMATICO'),
(2, '2026-07-16 23:02:00', 'LIGADO', 'AUTOMATICO'),
(2, '2026-07-16 23:07:00', 'DESLIGADO', 'AUTOMATICO'),
(2, '2026-07-16 23:12:00', 'LIGADO', 'MANUAL'),
(2, '2026-07-16 23:17:00', 'DESLIGADO', 'MANUAL');

-- erros (dispositivo 1)
INSERT INTO log_erros (id_dispositivo, data_hora, cod_erro, mensagem) VALUES
(1, '2026-07-16 22:00:00', 503, 'Falha de conexão com o broker MQTT'),
(1, '2026-07-16 22:05:00', 404, 'Sensor de pH não responde no barramento I2C');
