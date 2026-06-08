-- =====================
-- Tabla 1 AGENCIAS
-- =====================
INSERT INTO
	AGENCIA (
		CODIGO_AGENCIA,
		PRIMER_NOMBRE,
		SEGUNDO_NOMBRE,
		MUNICIPIO,
		CALLE,
		BARRIO,
		FECHA_APERTURA
	)
VALUES
	(
		'AG001',
		'Tulua',
		'Centro',
		'Tulua',
		'Cra 25',
		'Centro',
		'2022-01-15'
	),
	(
		'AG002',
		'Comercial',
		'Occidente',
		'Cali',
		'Calle 15',
		'San Fernando',
		'2019-07-10'
	),
	(
		'AG003',
		'Empresarial',
		'Sur',
		'Buga',
		'Calle 26',
		'El Carmelo',
		'2020-01-22'
	);

-- =====================
-- Tabla 2 ASOCIADOS 10
-- =====================
INSERT INTO
	ASOCIADO (
		CEDULA_ASOCIADO,
		PRIMER_NOMBRE,
		SEGUNDO_NOMBRE,
		APELLIDO,
		FECHA_NAC,
		MUNICIPIO,
		CALLE,
		BARRIO,
		FECHA_INGRESO,
		ESTADO
	)
VALUES
	(
		'100000001',
		'Adriana',
		'Milena',
		'Noscue',
		'2005-05-19',
		'Florida',
		'Calle 9',
		'Pubenza',
		'2024-03-01',
		'activo'
	),
	(
		'100000002',
		'Juan',
		'Sebastian',
		'Martines',
		'2000-05-11',
		'tulua',
		'Carrera 26',
		'el principe',
		'2024-02-01',
		'activo'
	),
	(
		'100000003',
		'Juan',
		'Jose',
		'Lopez',
		'2002-02-01',
		'trujillo',
		'Carrera 12',
		'La Esperanza',
		'2025-03-02',
		'suspendido'
	),
	(
		'100000004',
		'Maria',
		'Kamila',
		'Llanos',
		'1999-01-01',
		'tulua',
		'Carrera 25',
		'farfan',
		'2025-05-16',
		'retirado'
	),
	(
		'100000005',
		'Juan',
		'felipe',
		'Llanos',
		'1998-04-01',
		'tulua',
		'Carrera 24',
		'farfan',
		'2024-05-16',
		'activo'
	),
	(
		'100000006',
		'Maria',
		'jose',
		'Jaramillo',
		'1988-02-01',
		'tulua',
		'Carrera 10',
		'La Cruz',
		'2026-02-16',
		'retirado'
	),
	(
		'100000007',
		'Jose',
		'David',
		'Jaramillo',
		'2001-01-01',
		'Buga',
		'Calle 2',
		'Ciudad Señora',
		'2024-03-16',
		'suspendido'
	),
	(
		'100000008',
		'Maria',
		'Paula',
		'Llanos',
		'1999-01-01',
		'tulua',
		'Carrera 25',
		'farfan',
		'2025-05-16',
		'retirado'
	),
	(
		'100000009',
		'Samuel',
		'Andres',
		'Londoño',
		'1991-02-01',
		'tulua',
		'Carrera 26',
		'farfan',
		'2023-05-16',
		'suspendido'
	),
	(
		'100000010',
		'Kamila',
		'Andrea',
		'Garcia',
		'1995-06-01',
		'trujillo',
		'Carrera 12',
		'La Esperanza',
		'2024-07-19',
		'suspendido'
	);

-- =====================
-- Tabla 3 telefono agencia  6
-- =====================
INSERT INTO
	AGENCIA_TELEFONO (CODIGO_AGENCIA, TELEFONO)
VALUES
	('AG001', '3100000001'),
	('AG002', '3100000002'),
	('AG002', '3100000003'),
	('AG003', '3100000004');

-- ==========================
-- Tabla 4: Asociado_Telefono
-- ==========================
INSERT INTO
	ASOCIADO_TELEFONO (CEDULA_ASOCIADO, TELEFONO)
VALUES
	('100000001', '3117500841'),
	('100000002', '3117500842'),
	('100000003', '3117500843'),
	('100000004', '3117500844'),
	('100000005', '3117500845'),
	('100000006', '3117500846'),
	('100000007', '3117500847'),
	('100000008', '3117500848'),
	('100000009', '3117500849'),
	('100000010', '3117500810');

-- =====================
-- Tabla 5 : CORREOS ASOCIADOS
-- =====================
INSERT INTO
	ASOCIADO_CORREO (CEDULA_ASOCIADO, CORREO)
VALUES
	('100000001', '100000001@gamil.com'),
	('100000002', '100000002@gamil.com'),
	('100000003', '100000003@gamil.com'),
	('100000004', '100000004@gamil.com'),
	('100000005', '100000005@gamil.com'),
	('100000006', '100000006@gamil.com'),
	('100000007', '100000007@gamil.com'),
	('100000008', '100000008@gamil.com'),
	('100000009', '100000009@gamil.com'),
	('100000010', '100000010@gamil.com');

-- =====================
-- Tabla 6 fundador
-- =====================
INSERT INTO
	FUNDADOR (
		CEDULA_ASOCIADO,
		NUMERO_ACTA,
		ANIO_RECONOCIMIENTO,
		DES_BENEFICIOS
	)
VALUES
	(
		'100000001',
		'ACTA001',
		2021,
		'Prioridad en programas de bienestar social.'
	),
	(
		'100000002',
		'ACTA002',
		2022,
		'Acceso preferencial a líneas de crédito especiales.'
	);

-- =====================
-- Tabla 7 Beneficiarios
-- =====================
INSERT INTO
	BENEFICIARIOS (
		DOCUMENTO_BENEF,
		PRIMER_NOMBRE,
		SEGUNDO_NOMBRE,
		APELLIDO,
		PARENTESCO,
		PORCENTAJE_PARTICIPACION,
		CEDULA_ASOCIADO
	)
VALUES
	(
		'200000001',
		'Laura',
		'Patricia',
		'Gomez',
		'conyuge',
		50.00,
		'100000001'
	),
	(
		'200000002',
		'Juan',
		'David',
		'Gomez',
		'hijo',
		50.00,
		'100000002'
	),
	(
		'200000003',
		'Maria',
		'Fermanda',
		'Correa',
		'otro',
		60.00,
		'100000003'
	),
	(
		'200000004',
		'Carlos',
		'Andres',
		'Correa',
		'hijo',
		40.00,
		'100000004'
	);

-- =====================
-- Tabla 9 EMPLEADOS 
-- =====================
INSERT INTO
	EMPLEADO (
		CEDULA_EMPLEADO,
		PRIMER_NOMBRE,
		APELLIDO,
		FECHA_INGRESO,
		SALARIO_BASE,
		ESTADO_LABORAL,
		CARGO,
		CORREO_CORP,
		CODIGO_AGENCIA,
		CEDULA_SUPERVISOR
	)
VALUES
	(
		'100000011',
		'Manuel',
		'Rodriguez',
		'2023-02-01',
		2500000.00,
		'activo',
		'Director de agencia',
		'manuel.rodriguez@gmail.com',
		'AG001',
		NULL
	),
	(
		'100000012',
		'Manuela',
		'Mora',
		'2024-02-01',
		2700000.00,
		'en_licencia',
		'Asesor',
		'manuelamora@gmail.com',
		'AG002',
		NULL
	),
	(
		'100000013',
		'Diana',
		'Estupiñan',
		'2025-02-01',
		3700000.00,
		'retirado',
		'Asesor',
		'diana.estupinan2@gmail.com',
		'AG002',
		NULL
	),
	(
		'100000014',
		'Laura',
		'Salazar',
		'2022-05-02',
		3700000.00,
		'retirado',
		'Cajero',
		'laura.salazar@gmail.com',
		'AG002',
		NULL
	),
	(
		'100000015',
		'Natalia',
		'Salazar',
		'2023-04-02',
		2200000.00,
		'activo',
		'Cajero',
		'natalia.salazar@gmail.com',
		'AG003',
		NULL
	),
	(
		'100000016',
		'Rene',
		'Salazar',
		'2025-01-02',
		3700000.00,
		'en_licencia',
		'Cajero',
		'rene.salazar@gmail.com',
		'AG002',
		NULL
	);

-- =====================
-- Taba 10 Cajero
-- =====================
INSERT INTO
	CAJERO (CEDULA_EMPLEADO, NRO_CAJA)
VALUES
	('100000014', 1);

-- =====================
-- Tabla 11 Asesor
-- =====================
INSERT INTO
	ASESOR (CEDULA_EMPLEADO, COMISION)
VALUES
	('100000012', 5.50),
	('100000013', 7.25);

-- =====================
-- Tabla 12 director de agencia 
-- =====================
INSERT INTO
	DIRECTOR_AGENCIA (CEDULA_EMPLEADO, CLAVE_ACCESO)
VALUES
	('100000011', 'Dir2025AG001');

-- =====================
-- Tabla 13 TELEFONOS EMPLEADOS
-- =====================
INSERT INTO
	EMPLEADO_TELEFONO (CEDULA_EMPLEADO, TELEFONO)
VALUES
	('100000011', '3101234567'),
	('100000012', '3112345678');

-- =====================
-- Tabla 14 atiende
-- =====================
INSERT INTO
	ATIENDE (CEDULA_EMPLEADO, CEDULA_ASOCIADO, FECHA_INICIO)
VALUES
	('100000012', '100000001', '2025-03-01'),
	('100000013', '100000002', '2025-04-15');

-- =====================
-- Tabla 15 credito
-- =====================
INSERT INTO
	CREDITO (
		NUMERO_RADICADO,
		VLR_SOLICITADO,
		VLR_APROBADO,
		LINEA_CREDITO,
		TASA_INTERES,
		PLAZO_MESES,
		FECHA_APROBACION,
		FECHA_PRIMER_VENCIMIENTO,
		ESTADO_CREDITO,
		CEDULA_ASOCIADO,
		CODIGO_AGENCIA
	)
VALUES
	(
		'CR001',
		10000000.00,
		9000000.00,
		'educativo',
		1.20,
		24,
		'2025-01-15',
		'2025-02-15',
		'aprobado',
		'100000001',
		'AG001'
	),
	(
		'CR002',
		15000000.00,
		14000000.00,
		'vivienda',
		1.10,
		60,
		'2025-03-20',
		'2025-04-20',
		'aprobado',
		'100000005',
		'AG002'
	),
	(
		'CR003',
		5000000.00,
		4500000.00,
		'libre_inversion',
		1.50,
		18,
		'2025-04-10',
		'2025-05-10',
		'en_estudio',
		'100000007',
		'AG001'
	),
	(
		'CR004',
		8000000.00,
		7500000.00,
		'libre_inversion',
		1.30,
		36,
		'2025-02-03',
		'2026-01-03',
		'cancelado',
		'100000009',
		'AG003'
	);

-- =====================
-- tabla 16 CUENTAS DE AHORRO
-- =====================
INSERT INTO
	CUENTA_DE_AHORROS (
		NUMERO_CUENTA,
		FECHA_APERTURA,
		ESTADO,
		CEDULA_ASOCIADO,
		CODIGO_AGENCIA
	)
VALUES
	(
		'CA001',
		'2023-02-01',
		'activa',
		'100000001',
		'AG001'
	),
	(
		'CA002',
		'2024-03-01',
		'inactiva',
		'100000002',
		'AG002'
	),
	(
		'CA003',
		'2024-04-02',
		'embargada',
		'100000003',
		'AG003'
	),
	(
		'CA004',
		'2023-09-01',
		'activa',
		'100000006',
		'AG002'
	),
	(
		'CA005',
		'2022-04-02',
		'inactiva',
		'100000007',
		'AG001'
	),
	(
		'CA006',
		'2025-05-01',
		'inactiva',
		'100000009',
		'AG003'
	);

-- =====================
-- tabla 17 movimientos
-- =====================
INSERT INTO
	MOVIMIENTOS (
		NUMERO_TRANSACCION,
		TIPO_MOVIMIENTO,
		VALOR,
		CANAL,
		FECHA_HORA,
		NUMERO_CUENTA
	)
VALUES
	(
		'MOV001',
		'deposito',
		500000.00,
		'presencial',
		'2025-05-10 10:30:00',
		'CA001'
	),
	(
		'MOV002',
		'retiro',
		200000.00,
		'cajero_automatico',
		'2025-05-11 08:15:00',
		'CA001'
	),
	(
		'MOV003',
		'deposito',
		350000.00,
		'presencial',
		'2025-05-12 09:40:00',
		'CA002'
	),
	(
		'MOV004',
		'transferencia_entrante',
		150000.00,
		'app_movil',
		'2025-05-12 14:20:00',
		'CA003'
	),
	(
		'MOV005',
		'retiro',
		100000.00,
		'cajero_automatico',
		'2025-05-13 11:05:00',
		'CA004'
	),
	(
		'MOV006',
		'deposito',
		700000.00,
		'presencial',
		'2025-05-14 15:30:00',
		'CA005'
	),
	(
		'MOV007',
		'transferencia_entrante',
		250000.00,
		'app_movil',
		'2025-05-15 10:10:00',
		'CA006'
	),
	(
		'MOV008',
		'deposito',
		450000.00,
		'presencial',
		'2025-05-16 13:45:00',
		'CA001'
	),
	(
		'MOV009',
		'retiro',
		300000.00,
		'cajero_automatico',
		'2025-05-17 16:25:00',
		'CA002'
	),
	(
		'MOV010',
		'deposito',
		600000.00,
		'app_movil',
		'2025-05-18 09:00:00',
		'CA003'
	),
	(
		'MOV011',
		'transferencia_saliente',
		180000.00,
		'app_movil',
		'2025-05-18 12:50:00',
		'CA004'
	),
	(
		'MOV012',
		'retiro',
		120000.00,
		'cajero_automatico',
		'2025-05-19 17:10:00',
		'CA005'
	),
	(
		'MOV013',
		'deposito',
		900000.00,
		'presencial',
		'2025-05-20 08:35:00',
		'CA006'
	),
	(
		'MOV014',
		'transferencia_saliente',
		220000.00,
		'app_movil',
		'2025-05-20 14:40:00',
		'CA001'
	),
	(
		'MOV015',
		'retiro',
		175000.00,
		'cajero_automatico',
		'2025-05-21 10:55:00',
		'CA004'
	);

-- =====================
-- tabla 18 CUOTAS
-- =====================
INSERT INTO
	CUOTAS (
		NUMERO_CUOTA,
		FECHA_VENCIMIENTO,
		ESTADO_CUOTA,
		NUMERO_RADICADO
	)
VALUES
	(1, '2025-02-15', 'pendiente', 'CR001'),
	(2, '2025-03-15', 'a_tiempo', 'CR001'),
	(3, '2025-04-15', 'a_tiempo', 'CR001'),
	(4, '2025-05-15', 'con_mora', 'CR001'),
	(1, '2025-05-20', 'a_tiempo', 'CR002'),
	(2, '2025-06-20', 'a_tiempo', 'CR002'),
	(3, '2025-07-20', 'pendiente', 'CR002'),
	(1, '2025-06-10', 'a_tiempo', 'CR003'),
	(2, '2025-07-10', 'con_mora', 'CR003'),
	(1, '2025-08-01', 'pendiente', 'CR004');

-- =====================
-- tabla 19 PAGOS
-- =====================
INSERT INTO
	PAGOS (FECHA_PAGO, VALOR_PAGADO, ESTADO_PAGO, ID_CUOTA)
VALUES
	('2025-03-10', 450000.00, 'a_tiempo', 1),
	('2025-04-14', 450000.00, 'a_tiempo', 3),
	('2025-05-18', 315000.00, 'a_tiempo', 5),
	('2025-06-19', 315000.00, 'a_tiempo', 6),
	('2025-06-08', 280000.00, 'a_tiempo', 8),
	('2025-07-18', 280000.00, 'con_mora', 9);

-- =====================
-- tabla 20 
-- =====================
INSERT INTO
	CODEUDORA (CEDULA_CODEUDOR, NUMERO_RADICADO, FECHA_FIRMA)
VALUES
	('100000002', 'CR001', '2025-01-10'),
	('100000003', 'CR002', '2025-02-10');

-- =====================
-- tabla 21 
-- =====================
INSERT INTO
	SUPERVISA (CEDULA_SUPERVISOR, CEDULA_SUPERVISADO)
VALUES
	('100000011', '100000012');