-- Create the database
CREATE DATABASE IF NOT EXISTS blood_bank;
USE blood_bank;

-- Create Employee table
CREATE TABLE IF NOT EXISTS Employee (
    Emp_id INT AUTO_INCREMENT PRIMARY KEY,
    Emp_name VARCHAR(100) NOT NULL,
    Email VARCHAR(100) UNIQUE NOT NULL,
    Salary DECIMAL(10,2) NOT NULL,
    Designation VARCHAR(50) NOT NULL,
    Joining_date DATE NOT NULL,
    BB_contact VARCHAR(15) NOT NULL,
    BB_id INT NOT NULL,
    BB_address VARCHAR(255) NOT NULL,
    CONSTRAINT chk_employee_contact CHECK (BB_contact REGEXP '^[0-9]{10}$')
);

-- Create Donor table
CREATE TABLE IF NOT EXISTS Donor (
    Dona_id VARCHAR(20) PRIMARY KEY,
    Dona_name VARCHAR(100) NOT NULL,
    Blood_grp ENUM('A+', 'A-', 'B+', 'B-', 'O+', 'O-', 'AB+', 'AB-') NOT NULL,
    Dona_contact VARCHAR(15) NOT NULL,
    CONSTRAINT chk_donor_contact CHECK (Dona_contact REGEXP '^[0-9]{10}$')
);

-- Create Hospital table
CREATE TABLE IF NOT EXISTS Hospital (
    Hosp_id VARCHAR(20) PRIMARY KEY,
    Hosp_name VARCHAR(100) NOT NULL,
    Location VARCHAR(255) NOT NULL
);

-- Create Storage_House table
CREATE TABLE IF NOT EXISTS Storage_House (
    Storage_id VARCHAR(20) PRIMARY KEY,
    Blood_grp ENUM('A+', 'A-', 'B+', 'B-', 'O+', 'O-', 'AB+', 'AB-') NOT NULL,
    Quantity INT NOT NULL DEFAULT 0,
    CONSTRAINT chk_quantity CHECK (Quantity >= 0)
);

-- Create Orders table
CREATE TABLE IF NOT EXISTS Orders (
    Order_id VARCHAR(20) PRIMARY KEY,
    Hosp_id VARCHAR(20) NOT NULL,
    Blood_grp ENUM('A+', 'A-', 'B+', 'B-', 'O+', 'O-', 'AB+', 'AB-') NOT NULL,
    Quantity INT NOT NULL,
    Order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    Status ENUM('Pending', 'Fulfilled', 'Cancelled') DEFAULT 'Pending',
    CONSTRAINT chk_order_quantity CHECK (Quantity > 0),
    FOREIGN KEY (Hosp_id) REFERENCES Hospital(Hosp_id)
);

-- Create Supply table
CREATE TABLE IF NOT EXISTS Supply (
    Supply_id VARCHAR(20) PRIMARY KEY,
    Hosp_id VARCHAR(20) NOT NULL,
    Blood_grp ENUM('A+', 'A-', 'B+', 'B-', 'O+', 'O-', 'AB+', 'AB-') NOT NULL,
    Quantity INT NOT NULL,
    Supply_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_supply_quantity CHECK (Quantity > 0),
    FOREIGN KEY (Hosp_id) REFERENCES Hospital(Hosp_id)
);

-- Create Blood_Test table
CREATE TABLE IF NOT EXISTS Blood_Test (
    Test_id VARCHAR(20) PRIMARY KEY,
    Dona_id VARCHAR(20) NOT NULL,
    Test_date DATE NOT NULL,
    Hb_level DECIMAL(4,2) NOT NULL,
    Blood_pressure VARCHAR(10) NOT NULL,
    Result ENUM('Suitable', 'Unsuitable') NOT NULL,
    FOREIGN KEY (Dona_id) REFERENCES Donor(Dona_id)
);

-- Create views
CREATE VIEW Available_Blood AS
SELECT Blood_grp, SUM(Quantity) AS Total_Units
FROM Storage_House
GROUP BY Blood_grp;

CREATE VIEW Donor_Information AS
SELECT d.Dona_id, d.Dona_name, d.Blood_grp, d.Dona_contact, 
       COUNT(t.Test_id) AS Tests_Taken,
       SUM(CASE WHEN t.Result = 'Suitable' THEN 1 ELSE 0 END) AS Suitable_Donations
FROM Donor d
LEFT JOIN Blood_Test t ON d.Dona_id = t.Dona_id
GROUP BY d.Dona_id, d.Dona_name, d.Blood_grp, d.Dona_contact;

-- Stored Procedure
DELIMITER //
CREATE PROCEDURE Place_Order(
    IN p_order_id VARCHAR(20),
    IN p_hosp_id VARCHAR(20),
    IN p_blood_grp VARCHAR(3),
    IN p_quantity INT
)
BEGIN
    DECLARE available_qty INT;
    
    SELECT Quantity INTO available_qty 
    FROM Storage_House 
    WHERE Blood_grp = p_blood_grp;
    
    IF available_qty >= p_quantity THEN
        INSERT INTO Orders (Order_id, Hosp_id, Blood_grp, Quantity)
        VALUES (p_order_id, p_hosp_id, p_blood_grp, p_quantity);
        
        UPDATE Storage_House 
        SET Quantity = Quantity - p_quantity 
        WHERE Blood_grp = p_blood_grp;
        
        SELECT 'Order placed successfully' AS Message;
    ELSE
        SELECT 'Insufficient blood available' AS Message;
    END IF;
END //
DELIMITER ;

-- Trigger
DELIMITER //
CREATE TRIGGER after_supply_insert
AFTER INSERT ON Supply
FOR EACH ROW
BEGIN
    INSERT INTO Storage_House (Storage_id, Blood_grp, Quantity)
    VALUES (CONCAT('SUP', NEW.Supply_id), NEW.Blood_grp, NEW.Quantity)
    ON DUPLICATE KEY UPDATE Quantity = Quantity + NEW.Quantity;
END //
DELIMITER ;
