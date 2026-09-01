-- Sologix Solar Proposal System — Database Schema
-- Run as MySQL root: mysql -u root -p < database/schema.sql

CREATE DATABASE IF NOT EXISTS sologix_proposals CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'sologix_app'@'127.0.0.1' IDENTIFIED BY 'SologixApp2026!';
GRANT ALL PRIVILEGES ON sologix_proposals.* TO 'sologix_app'@'127.0.0.1';
FLUSH PRIVILEGES;

USE sologix_proposals;

CREATE TABLE IF NOT EXISTS company_settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    `key` VARCHAR(100) NOT NULL UNIQUE,
    `value` TEXT NOT NULL,
    description VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_key (`key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('MASTER','USER') NOT NULL DEFAULT 'USER',
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_username (username),
    INDEX idx_role (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS templates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    system_type ENUM('ONGRID','HYBRID') NOT NULL,
    version INT NOT NULL DEFAULT 1,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    html_file VARCHAR(255),
    created_by INT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id),
    UNIQUE KEY uk_name_version (name, version),
    INDEX idx_system_type (system_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS proposals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    proposal_number VARCHAR(20) NOT NULL UNIQUE,
    customer_name VARCHAR(150) NOT NULL,
    customer_address TEXT NOT NULL,
    customer_contact VARCHAR(20),
    system_type ENUM('ONGRID','HYBRID') NOT NULL,
    plant_capacity DECIMAL(8,2) NOT NULL,
    total_area DECIMAL(10,2) NOT NULL,
    mounting_type ENUM('RCC','SEATMOUNT','CARPORT','GROUNDMOUNT') NOT NULL,
    tilt_angle VARCHAR(20) DEFAULT '15-22 degrees',
    inverter_capacity DECIMAL(8,2) NOT NULL,
    base_price DECIMAL(12,2) NOT NULL DEFAULT 0,
    addon_total DECIMAL(12,2) NOT NULL DEFAULT 0,
    subtotal DECIMAL(12,2) NOT NULL DEFAULT 0,
    discount_percent DECIMAL(5,2) NOT NULL DEFAULT 0,
    discount_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
    grand_total DECIMAL(12,2) NOT NULL DEFAULT 0,
    cfa_amount DECIMAL(12,2) NOT NULL DEFAULT 78000,
    status ENUM('DRAFT','GENERATED','ACCEPTED','REJECTED') NOT NULL DEFAULT 'DRAFT',
    proposal_date DATE,
    snapshot JSON,
    created_by INT NOT NULL,
    template_id INT,
    template_version INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id),
    FOREIGN KEY (template_id) REFERENCES templates(id),
    INDEX idx_status (status),
    INDEX idx_created_by (created_by),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS proposal_modules (
    id INT AUTO_INCREMENT PRIMARY KEY,
    proposal_id INT NOT NULL,
    module_type ENUM('DCR','NDCR') NOT NULL,
    quantity INT NOT NULL DEFAULT 0,
    wattage VARCHAR(20),
    make VARCHAR(200),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (proposal_id) REFERENCES proposals(id) ON DELETE CASCADE,
    INDEX idx_proposal_id (proposal_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS proposal_battery (
    id INT AUTO_INCREMENT PRIMARY KEY,
    proposal_id INT NOT NULL UNIQUE,
    capacity_kwh DECIMAL(8,2),
    quantity INT DEFAULT 1,
    make VARCHAR(100),
    chemistry VARCHAR(50) DEFAULT 'FeLiO4P',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (proposal_id) REFERENCES proposals(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS proposal_addons (
    id INT AUTO_INCREMENT PRIMARY KEY,
    proposal_id INT NOT NULL,
    sequence INT NOT NULL DEFAULT 1,
    name VARCHAR(200) NOT NULL,
    amount DECIMAL(12,2) NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (proposal_id) REFERENCES proposals(id) ON DELETE CASCADE,
    INDEX idx_proposal_id (proposal_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS proposal_payments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    proposal_id INT NOT NULL,
    sequence INT NOT NULL,
    milestone VARCHAR(200) NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (proposal_id) REFERENCES proposals(id) ON DELETE CASCADE,
    INDEX idx_proposal_id (proposal_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS proposal_versions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    proposal_id INT NOT NULL,
    version_number INT NOT NULL DEFAULT 1,
    template_id INT,
    template_version INT,
    generated_by INT NOT NULL,
    generated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    snapshot JSON,
    FOREIGN KEY (proposal_id) REFERENCES proposals(id),
    FOREIGN KEY (generated_by) REFERENCES users(id),
    INDEX idx_proposal_id (proposal_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS proposal_files (
    id INT AUTO_INCREMENT PRIMARY KEY,
    proposal_id INT NOT NULL,
    proposal_version_id INT,
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size INT,
    sha256 VARCHAR(64),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (proposal_id) REFERENCES proposals(id),
    FOREIGN KEY (proposal_version_id) REFERENCES proposal_versions(id),
    INDEX idx_proposal_id (proposal_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS accepted_proposals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    proposal_id INT NOT NULL UNIQUE,
    accepted_by INT NOT NULL,
    accepted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    FOREIGN KEY (proposal_id) REFERENCES proposals(id),
    FOREIGN KEY (accepted_by) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS rejected_proposals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    proposal_id INT NOT NULL UNIQUE,
    rejected_by INT NOT NULL,
    rejected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    reason TEXT NOT NULL,
    FOREIGN KEY (proposal_id) REFERENCES proposals(id),
    FOREIGN KEY (rejected_by) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS audit_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    action VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50),
    entity_id INT,
    details JSON,
    ip_address VARCHAR(45),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_user_id (user_id),
    INDEX idx_action (action),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Company settings seed data
INSERT INTO company_settings (`key`, `value`, description) VALUES
('company_name', 'Sologix Energy Private Limited', 'Company legal name'),
('company_address_line1', '2nd Floor, Tower Two', 'Address line 1'),
('company_address_line2', 'Software Technology Park of India,', 'Address line 2'),
('company_address_line3', 'Namkum Industrial Area, Ranchi', 'Address line 3'),
('company_address_line4', 'Jharkhand- 834010', 'Address line 4'),
('company_gstin', '20AAZCS9296C1ZT', 'GSTIN'),
('company_pan', 'AAZCS9296C', 'PAN number'),
('bank_name', 'Canara Bank, Chutia, Ranchi, Jharkhand - 834001', 'Bank name and branch'),
('bank_account_number', '125009426214', 'Bank account number'),
('bank_account_name', 'Sologix Energy Private Limited', 'Bank account name'),
('bank_ifsc', 'CNRB0001969', 'RTGS/NEFT IFSC code'),
('bank_upi_id', '8287766474@okbizaxis', 'UPI ID'),
('cfa_amount', '78000', 'CFA (DBT) amount in rupees'),
('tilt_angle', '15-22 degrees', 'Default tilt angle'),
('dcr_module_wattage', '580W-620W', 'DCR module wattage range'),
('ndcr_module_wattage', '580W-620W', 'NDCR module wattage range'),
('module_makes', 'Rayzon Solar/Premier Energy/RenewSys/Pahal/Adani/TATA Power', 'Module makes'),
('inverter_makes', 'Growatt/Deye', 'Inverter makes'),
('mounting_structure_make', 'HDGI', 'Mounting structure make'),
('battery_chemistry', 'FeLiO4P', 'Battery chemistry'),
('earthing_quantity', '3 nos.', 'Earthing quantity'),
('lightning_arrestor_quantity', '1 no.', 'Lightning arrestor quantity'),
('warranty_module_defect', '12 Years warranty on solar modules against manufacturing defects', 'Module warranty'),
('warranty_module_performance', '30 Years linear performance guarantee on solar modules', 'Performance warranty'),
('warranty_inverter', '8 years warranty on solar on-grid Inverters.', 'Inverter warranty'),
('note_approach', 'Easy approach to the work site to be provided by the consumer.', 'Note'),
('note_shadow', 'Shadow free space on the roof should be provided for the installation of solar panels.', 'Note'),
('note_sim', 'Sim Data Service for remote monitoring is free for the first year. Thereafter a charge of Rs. 1500 per year.', 'Note'),
('note_raised_structure', 'The cost of the Raised Structure will be Rs. 5000 per kW.', 'Note'),
('payment_reminder', 'Details for making payment including in proposal, do not forget to collect receipt of payment.', 'Payment note'),
('company_signatory', '2nd Floor, STPI, Namkum, Ranchi- 834010', 'Company address for acceptance')
ON DUPLICATE KEY UPDATE `value` = VALUES(`value`);
