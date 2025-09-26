-- schema.sql
-- Tao database
CREATE DATABASE IF NOT EXISTS clinic_scheduler
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE clinic_scheduler;

-- Bang nguoidung (tai khoan)
CREATE TABLE IF NOT EXISTS nguoidung (
    id_nguoidung INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL, -- luu password da hash
    email VARCHAR(255),
    role ENUM('user','admin','doctor') NOT NULL DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Bang bacsi
CREATE TABLE IF NOT EXISTS bacsi (
    id_bacsi INT AUTO_INCREMENT PRIMARY KEY,
    ten_bacsi VARCHAR(200) NOT NULL,
    kinh_nghiem VARCHAR(255),
    hocvan VARCHAR(255),
    mo_ta TEXT,
    id_user INT NOT NULL, -- tham chieu den nguoidung
    hinhanh VARCHAR(300),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_user) REFERENCES nguoidung(id_nguoidung) ON DELETE CASCADE,
    INDEX (id_user)
) ENGINE=InnoDB;

-- Bang benhnhan
CREATE TABLE IF NOT EXISTS benhnhan (
    id_benhnhan INT AUTO_INCREMENT PRIMARY KEY,
    ten_benhnhan VARCHAR(200) NOT NULL,
    sodienthoai VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Bang lichlamviec
CREATE TABLE IF NOT EXISTS lichlamviec (
    id_lichlamviec INT AUTO_INCREMENT PRIMARY KEY,
    id_bacsi INT NOT NULL,
    lichlam TEXT NOT NULL, -- co the luu JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_bacsi) REFERENCES bacsi(id_bacsi) ON DELETE CASCADE,
    INDEX (id_bacsi)
) ENGINE=InnoDB;

-- Bang lichhen
CREATE TABLE IF NOT EXISTS lichhen (
    id_lichhen INT AUTO_INCREMENT PRIMARY KEY,
    id_bacsi INT NOT NULL,
    id_benhnhan INT NOT NULL,
    id_nguoidung INT NOT NULL,
    ThoiGianHen DATETIME NOT NULL,
    mota TEXT,
    trang_thai ENUM('dang_cho','xac_nhan','da_huy','da_kham') DEFAULT 'dang_cho',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_bacsi) REFERENCES bacsi(id_bacsi) ON DELETE CASCADE,
    FOREIGN KEY (id_benhnhan) REFERENCES benhnhan(id_benhnhan) ON DELETE CASCADE,
    FOREIGN KEY (id_nguoidung) REFERENCES nguoidung(id_nguoidung) ON DELETE SET NULL,
    INDEX (id_bacsi),
    INDEX (id_benhnhan),
    INDEX (id_nguoidung),
    INDEX (ThoiGianHen)
) ENGINE=InnoDB;

-- Bang review
CREATE TABLE IF NOT EXISTS review (
    id_review INT AUTO_INCREMENT PRIMARY KEY,
    id_nguoidung INT NOT NULL,
    id_bacsi INT NOT NULL,
    so_sao TINYINT NOT NULL CHECK (so_sao BETWEEN 1 AND 5),
    binhluan TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_nguoidung) REFERENCES nguoidung(id_nguoidung) ON DELETE CASCADE,
    FOREIGN KEY (id_bacsi) REFERENCES bacsi(id_bacsi) ON DELETE CASCADE,
    INDEX (id_bacsi),
    INDEX (id_nguoidung)
) ENGINE=InnoDB;

-- Du lieu mau
INSERT INTO nguoidung (username, password, email, role)
VALUES 
('admin', 'admin123', 'admin@example.com', 'admin'),
('drnguyen', 'doctor123', 'dr.nguyen@example.com', 'doctor'),
('user01', 'user123', 'user01@example.com', 'user');

INSERT INTO bacsi (ten_bacsi, kinh_nghiem, hocvan, mo_ta, id_user, hinhanh)
VALUES ('Nguyen Van A', '10 nam', 'Dai hoc Y Ha Noi', 'Chuyen khoa Noi tong hop', 2, '/static/uploads/dr_a.jpg');

INSERT INTO benhnhan (ten_benhnhan, sodienthoai)
VALUES ('Le Thi B', '0987654321');

INSERT INTO lichlamviec (id_bacsi, lichlam)
VALUES (1, '[{"ngay":"2025-09-25","batdau":"09:00","ketthuc":"12:00"},{"ngay":"2025-09-26","batdau":"14:00","ketthuc":"17:00"}]');

INSERT INTO lichhen (id_bacsi, id_benhnhan, id_nguoidung, ThoiGianHen, mota, trang_thai)
VALUES (1, 1, 3, '2025-09-25 09:30:00', 'Kham tong quat', 'xac_nhan');

INSERT INTO review (id_nguoidung, id_bacsi, so_sao, binhluan)
VALUES (3, 1, 5, 'Bac si tu van rat tan tam!');
