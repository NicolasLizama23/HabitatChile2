-- Script para inicializar la base de datos SQLite
CREATE TABLE IF NOT EXISTS REGIONES (
    id_region INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_region VARCHAR(100) NOT NULL,
    codigo_region VARCHAR(10),
    capital_regional VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS MUNICIPIOS (
    id_municipio INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_municipio VARCHAR(100) NOT NULL,
    codigo_municipio VARCHAR(10),
    id_region INTEGER,
    poblacion INTEGER,
    superficie_km2 DECIMAL(10,2),
    FOREIGN KEY (id_region) REFERENCES REGIONES(id_region)
);

CREATE TABLE IF NOT EXISTS EMPRESAS_CONSTRUCTORAS (
    id_empresa INTEGER PRIMARY KEY AUTOINCREMENT,
    rut_empresa VARCHAR(20) UNIQUE,
    razon_social VARCHAR(200) NOT NULL,
    telefono VARCHAR(20),
    email VARCHAR(100),
    direccion VARCHAR(200),
    certificacion_industrializada BOOLEAN,
    años_experiencia INTEGER,
    capacidad_construccion_anual INTEGER,
    estado_empresa VARCHAR(50),
    fecha_registro DATE
);

CREATE TABLE IF NOT EXISTS TERRENOS (
    id_terreno INTEGER PRIMARY KEY AUTOINCREMENT,
    direccion VARCHAR(200),
    id_municipio INTEGER,
    superficie_total DECIMAL(10,2),
    coordenadas_gps VARCHAR(50),
    servicios_agua BOOLEAN,
    servicios_electricidad BOOLEAN,
    servicios_alcantarillado BOOLEAN,
    acceso_transporte BOOLEAN,
    factibilidad_construccion BOOLEAN,
    estado_terreno VARCHAR(50),
    precio_m2 DECIMAL(10,2),
    fecha_registro DATE,
    FOREIGN KEY (id_municipio) REFERENCES MUNICIPIOS(id_municipio)
);

CREATE TABLE IF NOT EXISTS PROYECTOS_HABITACIONALES (
    id_proyecto INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_proyecto VARCHAR(200),
    descripcion TEXT,
    id_municipio INTEGER,
    id_empresa_constructora INTEGER,
    id_terreno INTEGER,
    numero_viviendas INTEGER,
    tipo_vivienda VARCHAR(100),
    superficie_vivienda DECIMAL(8,2),
    precio_unitario DECIMAL(12,2),
    fecha_inicio DATE,
    fecha_fin_estimada DATE,
    estado_proyecto VARCHAR(50),
    certificacion_ambiental VARCHAR(50),
    tecnologia_construccion VARCHAR(100),
    FOREIGN KEY (id_municipio) REFERENCES MUNICIPIOS(id_municipio),
    FOREIGN KEY (id_empresa_constructora) REFERENCES EMPRESAS_CONSTRUCTORAS(id_empresa),
    FOREIGN KEY (id_terreno) REFERENCES TERRENOS(id_terreno)
);

CREATE TABLE IF NOT EXISTS BENEFICIARIOS (
    id_beneficiario INTEGER PRIMARY KEY AUTOINCREMENT,
    rut VARCHAR(20) UNIQUE,
    nombre VARCHAR(100),
    apellidos VARCHAR(100),
    fecha_nacimiento DATE,
    telefono VARCHAR(20),
    email VARCHAR(100),
    direccion VARCHAR(200),
    id_municipio INTEGER,
    estado_civil VARCHAR(50),
    ingresos_familiares DECIMAL(12,2),
    numero_integrantes INTEGER,
    puntaje_socioeconomico INTEGER,
    estado_beneficiario VARCHAR(50),
    fecha_registro DATE,
    FOREIGN KEY (id_municipio) REFERENCES MUNICIPIOS(id_municipio)
);

CREATE TABLE IF NOT EXISTS POSTULACIONES (
    id_postulacion INTEGER PRIMARY KEY AUTOINCREMENT,
    id_beneficiario INTEGER,
    id_proyecto INTEGER,
    fecha_postulacion DATE,
    estado_postulacion VARCHAR(50),
    puntaje_asignado INTEGER,
    fecha_asignacion DATE,
    observaciones TEXT,
    documentos_adjuntos TEXT,
    FOREIGN KEY (id_beneficiario) REFERENCES BENEFICIARIOS(id_beneficiario),
    FOREIGN KEY (id_proyecto) REFERENCES PROYECTOS_HABITACIONALES(id_proyecto)
);

CREATE TABLE IF NOT EXISTS INSTITUCIONES (
    id_institucion INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_institucion VARCHAR(200),
    tipo_institucion VARCHAR(100),
    rut_institucion VARCHAR(20),
    direccion VARCHAR(200),
    telefono VARCHAR(20),
    email_contacto VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS USUARIOS_SISTEMA (
    id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(100) UNIQUE,
    password_hash VARCHAR(255),
    email VARCHAR(100),
    nombre VARCHAR(100),
    apellidos VARCHAR(100),
    tipo_usuario VARCHAR(50),
    id_institucion INTEGER,
    estado_usuario VARCHAR(50),
    fecha_ultimo_acceso DATETIME,
    fecha_registro DATE,
    FOREIGN KEY (id_institucion) REFERENCES INSTITUCIONES(id_institucion)
);