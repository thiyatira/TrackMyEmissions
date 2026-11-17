-- TrackMyEmissions - Carbon Emission Management System: database setup
CREATE DATABASE IF NOT EXISTS carbon_db;
USE carbon_db;

-- Login users (passwords stored as SHA-256 hashes)
CREATE TABLE IF NOT EXISTS users (
    id       INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password CHAR(64) NOT NULL
);

-- Emission entries (co2_kg = quantity x emission factor, calculated by the app)
CREATE TABLE IF NOT EXISTS emissions (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    entry_date  DATE NOT NULL,
    department  VARCHAR(50) NOT NULL,
    category    VARCHAR(30) NOT NULL,
    quantity    DECIMAL(12,2) NOT NULL,
    co2_kg      DECIMAL(12,2) NOT NULL,
    notes       VARCHAR(255)
);

-- Default login: admin / admin123
INSERT IGNORE INTO users (username, password) VALUES ('admin', SHA2('admin123', 256));

-- Sample data. Factors (kg CO2 per unit): Electricity 0.82/kWh, Diesel 2.68/L,
-- Petrol 2.31/L, LPG 2.98/kg, Flights 0.15/km, Waste 0.50/kg
INSERT IGNORE INTO emissions VALUES
( 1, '2026-06-04', 'Production', 'Electricity', 5200, 5200*0.82, 'Main plant'),
( 2, '2026-06-10', 'Logistics',  'Diesel',       420,  420*2.68, 'Delivery trucks'),
( 3, '2026-06-18', 'Canteen',    'LPG',          120,  120*2.98, 'Kitchen'),
( 4, '2026-06-25', 'Admin',      'Flights',     3400, 3400*0.15, 'Chennai - Delhi trip'),
( 5, '2026-07-03', 'Production', 'Electricity', 5600, 5600*0.82, 'Main plant'),
( 6, '2026-07-12', 'IT',         'Electricity', 1800, 1800*0.82, 'Server room'),
( 7, '2026-07-20', 'Logistics',  'Diesel',       460,  460*2.68, 'Delivery trucks'),
( 8, '2026-07-28', 'Production', 'Waste',        900,  900*0.50, 'Scrap metal'),
( 9, '2026-08-05', 'Production', 'Electricity', 6100, 6100*0.82, 'Main plant'),
(10, '2026-08-14', 'Admin',      'Petrol',       150,  150*2.31, 'Staff cars'),
(11, '2026-08-21', 'Logistics',  'Diesel',       510,  510*2.68, 'Delivery trucks'),
(12, '2026-08-29', 'Canteen',    'LPG',          140,  140*2.98, 'Kitchen'),
(13, '2026-09-04', 'Production', 'Electricity', 5800, 5800*0.82, 'Main plant'),
(14, '2026-09-11', 'IT',         'Electricity', 1900, 1900*0.82, 'Server room'),
(15, '2026-09-19', 'Logistics',  'Diesel',       380,  380*2.68, 'Delivery trucks'),
(16, '2026-09-26', 'Admin',      'Flights',     5200, 5200*0.15, 'Client visit Mumbai'),
(17, '2026-10-03', 'Production', 'Electricity', 5400, 5400*0.82, 'Main plant'),
(18, '2026-10-12', 'Logistics',  'Diesel',       440,  440*2.68, 'Delivery trucks'),
(19, '2026-10-20', 'Production', 'Waste',        750,  750*0.50, 'Packaging waste'),
(20, '2026-10-27', 'Admin',      'Petrol',       130,  130*2.31, 'Staff cars'),
(21, '2026-11-03', 'Production', 'Electricity', 4900, 4900*0.82, 'Main plant'),
(22, '2026-11-07', 'IT',         'Electricity', 1700, 1700*0.82, 'Server room'),
(23, '2026-11-10', 'Logistics',  'Diesel',       400,  400*2.68, 'Delivery trucks'),
(24, '2026-11-14', 'Canteen',    'LPG',          110,  110*2.98, 'Kitchen');
