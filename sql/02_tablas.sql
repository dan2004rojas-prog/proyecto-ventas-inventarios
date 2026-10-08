
CREATE TABLE Proveedores (
    id_proveedor   INT IDENTITY(1,1) PRIMARY KEY,
    nombre         VARCHAR(100) NOT NULL,
    pais           VARCHAR(50),
    lead_time_dias INT NOT NULL
);

CREATE TABLE Productos (
    id_producto    INT IDENTITY(1,1) PRIMARY KEY,
    nombre         VARCHAR(100) NOT NULL,
    categoria      VARCHAR(50),
    id_proveedor   INT NOT NULL,
    costo_unitario DECIMAL(10,2) NOT NULL,
    precio         DECIMAL(10,2) NOT NULL,
    CONSTRAINT FK_Productos_Proveedores
        FOREIGN KEY (id_proveedor) REFERENCES Proveedores(id_proveedor)
);

CREATE TABLE Ventas (
    id_venta    INT IDENTITY(1,1) PRIMARY KEY,
    fecha       DATE NOT NULL,
    id_producto INT NOT NULL,
    cantidad    INT NOT NULL,
    monto       DECIMAL(12,2) NOT NULL,
    CONSTRAINT FK_Ventas_Productos
        FOREIGN KEY (id_producto) REFERENCES Productos(id_producto)
);

CREATE TABLE Inventario (
    id_producto  INT NOT NULL,
    fecha        DATE NOT NULL,
    stock_actual INT NOT NULL,
    stock_minimo INT NOT NULL,
    CONSTRAINT PK_Inventario PRIMARY KEY (id_producto, fecha),
    CONSTRAINT FK_Inventario_Productos
        FOREIGN KEY (id_producto) REFERENCES Productos(id_producto)
);

-- Índices que ayudarán a las consultas por fecha
CREATE INDEX IX_Ventas_Fecha ON Ventas(fecha, id_producto);

SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES;
