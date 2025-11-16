CREATE database IF NOT EXISTS campus_borrowing_system;

-- Schema for Campus Borrowing and Returning System
CREATE TABLE IF NOT EXISTS user_login (
  user_id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(100) NOT NULL UNIQUE,
  password VARCHAR(255) NOT NULL,
  role ENUM('user','admin') NOT NULL DEFAULT 'user'
);

CREATE TABLE IF NOT EXISTS equipment_inventory (
  equipment_id INT AUTO_INCREMENT PRIMARY KEY,
  equipment_name VARCHAR(255) NOT NULL,
  category ENUM('technical','sports','lab') NOT NULL,
  quantity_available INT NOT NULL DEFAULT 0,
  status ENUM('available','borrowed','maintenance') NOT NULL DEFAULT 'available'
);

CREATE TABLE IF NOT EXISTS borrow_request (
  request_id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  equipment_id INT NOT NULL,
  borrow_date DATETIME NOT NULL,
  status ENUM('pending','approved','denied') NOT NULL DEFAULT 'pending',
  FOREIGN KEY (user_id) REFERENCES user_login(user_id) ON DELETE CASCADE,
  FOREIGN KEY (equipment_id) REFERENCES equipment_inventory(equipment_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS return_request (
  return_id INT AUTO_INCREMENT PRIMARY KEY,
  borrow_id INT NOT NULL,
  return_date DATETIME NOT NULL,
  status ENUM('pending','approved') NOT NULL DEFAULT 'pending',
  FOREIGN KEY (borrow_id) REFERENCES borrow_request(request_id) ON DELETE CASCADE
);

-- Optional activity log
CREATE TABLE IF NOT EXISTS activity_log (
  log_id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT,
  action VARCHAR(255),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES user_login(user_id) ON DELETE SET NULL
);

-- Sample equipment
INSERT INTO equipment_inventory (equipment_name, category, quantity_available, status) VALUES
('Digital Multimeter', 'technical', 5, 'available'),
('Laptop - Lenovo', 'technical', 3, 'available'),
('Basketball', 'sports', 10, 'available'),
('Physics Lab Microscope', 'lab', 4, 'available');

-- Note: create users via the /api/register endpoint to ensure password hashing.
