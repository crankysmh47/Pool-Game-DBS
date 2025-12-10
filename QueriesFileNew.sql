-- -----------------------------------------------------
-- Database pool_game_db
-- -----------------------------------------------------
DROP DATABASE IF EXISTS pool_game_db;
CREATE DATABASE pool_game_db;
USE pool_game_db;
SET default_storage_engine=InnoDB;

-- -----------------------------------------------------
-- 1. Table User (The Supertype)
-- Stores generic authentication data for everyone
-- -----------------------------------------------------
CREATE TABLE User (
  UserID INT NOT NULL AUTO_INCREMENT,
  Username VARCHAR(50) NOT NULL UNIQUE,
  PasswordHash VARCHAR(256) NOT NULL,
  Salt VARCHAR(128) NOT NULL,
  Role ENUM('PLAYER', 'ADMIN') NOT NULL,
  DateCreated TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (UserID)
);

-- -----------------------------------------------------
-- 2. Table Player (The Subtype)
-- Stores strictly gameplay related entity data
-- PlayerID is both the Primary Key and a Foreign Key to User
-- -----------------------------------------------------
CREATE TABLE Player (
  PlayerID INT NOT NULL,
  PRIMARY KEY (PlayerID),
  FOREIGN KEY (PlayerID) REFERENCES User(UserID) ON DELETE CASCADE
);

-- -----------------------------------------------------
-- 3. Table Admin (The Subtype)
-- Stores strictly admin related entity data
-- -----------------------------------------------------
CREATE TABLE Admin (
  AdminID INT NOT NULL,
  PRIMARY KEY (AdminID),
  FOREIGN KEY (AdminID) REFERENCES User(UserID) ON DELETE CASCADE
);

-- -----------------------------------------------------
-- Lookup Table: DifficultyLevel
-- -----------------------------------------------------
CREATE TABLE DifficultyLevel (
  DifficultyID INT NOT NULL,
  LevelName VARCHAR(25) NOT NULL,
  PRIMARY KEY (DifficultyID)
);

-- -----------------------------------------------------
-- Lookup Table: Pocket
-- -----------------------------------------------------
CREATE TABLE Pocket (
  PocketID INT NOT NULL,
  PocketName VARCHAR(25) NOT NULL,
  PRIMARY KEY (PocketID)
);

-- -----------------------------------------------------
-- Lookup Table: Achievement
-- -----------------------------------------------------
CREATE TABLE Achievement (
  AchievementID INT NOT NULL,
  Name VARCHAR(100) NOT NULL,
  Description TEXT,
  DifficultyID INT,
  PRIMARY KEY (AchievementID),
  FOREIGN KEY (DifficultyID) REFERENCES DifficultyLevel(DifficultyID)
);

-- -----------------------------------------------------
-- Table GameSession
-- -----------------------------------------------------
CREATE TABLE GameSession (
  GameSessionID INT NOT NULL AUTO_INCREMENT,
  DifficultyID INT NOT NULL,
  StartTime TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  EndTime TIMESTAMP NULL,
  PRIMARY KEY (GameSessionID),
  FOREIGN KEY (DifficultyID) REFERENCES DifficultyLevel(DifficultyID)
);

-- -----------------------------------------------------
-- Associative/Weak Table: GameParticipant (M:N)
-- Links GameSession to the PLAYER subtype
-- -----------------------------------------------------
CREATE TABLE GameParticipant (
  GameSessionID INT NOT NULL,
  PlayerID INT NOT NULL,
  Score INT NOT NULL DEFAULT 0,
  IsWinner BOOLEAN NOT NULL DEFAULT FALSE,
  PRIMARY KEY (GameSessionID, PlayerID),
  FOREIGN KEY (GameSessionID) REFERENCES GameSession(GameSessionID) ON DELETE CASCADE,
  FOREIGN KEY (PlayerID) REFERENCES Player(PlayerID) ON DELETE CASCADE
);

-- -----------------------------------------------------
-- Transactional Table: GameEvent (The Log)
-- Links to the PLAYER subtype
-- -----------------------------------------------------
CREATE TABLE GameEvent (
  EventID INT NOT NULL AUTO_INCREMENT,
  GameSessionID INT NOT NULL,
  PlayerID INT NOT NULL,
  PocketID INT NULL,
  BallPotted VARCHAR(20) NULL,
  EventType VARCHAR(20) NOT NULL,
  EventTime TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (EventID),
  FOREIGN KEY (GameSessionID) REFERENCES GameSession(GameSessionID) ON DELETE CASCADE,
  FOREIGN KEY (PlayerID) REFERENCES Player(PlayerID) ON DELETE CASCADE,
  FOREIGN KEY (PocketID) REFERENCES Pocket(PocketID)
);

-- -----------------------------------------------------
-- Associative/Weak Table: PlayerAchievement (M:N)
-- Links to the PLAYER subtype
-- -----------------------------------------------------
CREATE TABLE PlayerAchievement (
  PlayerID INT NOT NULL,
  AchievementID INT NOT NULL,
  DateEarned TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (PlayerID, AchievementID),
  FOREIGN KEY (PlayerID) REFERENCES Player(PlayerID) ON DELETE CASCADE,
  FOREIGN KEY (AchievementID) REFERENCES Achievement(AchievementID) ON DELETE CASCADE
);

-- =====================================================
-- DATA POPULATION
-- =====================================================

-- Populate Difficulty Levels
INSERT INTO DifficultyLevel (DifficultyID, LevelName) VALUES
(1, 'Easy'),
(2, 'Medium'), 
(3, 'Hard');

-- Populate Pockets
INSERT INTO Pocket (PocketID, PocketName) VALUES
(1, 'Top-Left'),
(2, 'Top-Middle'),
(3, 'Top-Right'),
(4, 'Bottom-Left'),
(5, 'Bottom-Middle'),
(6, 'Bottom-Right');

-- Populate Achievements
INSERT INTO Achievement (AchievementID, Name, Description, DifficultyID) VALUES
(1, 'Speed Demon', 'Win a game in under 90 seconds.', NULL),
(2, 'Sharpshooter', 'Win a game in 10 shots or less.', NULL),
(3, 'Pool Shark', 'Win a game on Hard difficulty.', 3),
(4, 'Hardcore', 'Win on Hard difficulty with 0 fouls.', 3),
(5, 'First Victory', 'Win your first game.', NULL),
(6, 'On the Board', 'Play your first game to completion.', NULL),
(7, 'Combo Shot', 'Pot 2 or more balls in a single shot.', NULL),
(8, 'First Potter', 'Pot your very first ball.', NULL);

-- =====================================================
-- STORED PROCEDURE
-- =====================================================

DELIMITER $$

DROP PROCEDURE IF EXISTS sp_CheckPlayerAchievements$$

CREATE PROCEDURE sp_CheckPlayerAchievements (
    IN p_PlayerID INT,
    IN p_DifficultyID INT,
    IN p_Timer FLOAT,
    IN p_Shots INT,
    IN p_Fouls INT,
    IN p_DidWin BOOLEAN
)
BEGIN
    DECLARE total_wins INT;
    DECLARE total_games INT;
    
    -- 1. Create a temporary table to store the achievements we grant
    CREATE TEMPORARY TABLE IF NOT EXISTS NewAchievements (
        AchievementID INT,
        Name VARCHAR(100)
    );
    
    TRUNCATE TABLE NewAchievements;

    -- 2. Check "Win-Only" Achievements
    IF p_DidWin THEN
    
        -- Achievement ID 1: "Speed Demon"
        IF p_Timer < 90 THEN
            INSERT IGNORE INTO PlayerAchievement (PlayerID, AchievementID, DateEarned)
            VALUES (p_PlayerID, 1, NOW());
            IF ROW_COUNT() > 0 THEN
                INSERT INTO NewAchievements (AchievementID, Name)
                SELECT AchievementID, Name FROM Achievement WHERE AchievementID = 1;
            END IF;
        END IF;
        
        -- Achievement ID 2: "Sharpshooter"
        IF p_Shots <= 10 THEN
            INSERT IGNORE INTO PlayerAchievement (PlayerID, AchievementID, DateEarned)
            VALUES (p_PlayerID, 2, NOW());
            IF ROW_COUNT() > 0 THEN
                INSERT INTO NewAchievements (AchievementID, Name)
                SELECT AchievementID, Name FROM Achievement WHERE AchievementID = 2;
            END IF;
        END IF;

        -- Achievement ID 3: "Pool Shark" (Win on Hard)
        IF p_DifficultyID = (SELECT DifficultyID FROM Achievement WHERE AchievementID = 3) THEN
            INSERT IGNORE INTO PlayerAchievement (PlayerID, AchievementID, DateEarned)
            VALUES (p_PlayerID, 3, NOW());
            IF ROW_COUNT() > 0 THEN
                INSERT INTO NewAchievements (AchievementID, Name)
                SELECT AchievementID, Name FROM Achievement WHERE AchievementID = 3;
            END IF;
        END IF;
        
        -- Achievement ID 4: "Hardcore" (Win on Hard, 0 fouls)
        IF p_DifficultyID = (SELECT DifficultyID FROM Achievement WHERE AchievementID = 4) AND p_Fouls = 0 THEN
            INSERT IGNORE INTO PlayerAchievement (PlayerID, AchievementID, DateEarned)
            VALUES (p_PlayerID, 4, NOW());
            IF ROW_COUNT() > 0 THEN
                INSERT INTO NewAchievements (AchievementID, Name)
                SELECT AchievementID, Name FROM Achievement WHERE AchievementID = 4;
            END IF;
        END IF;
        
        -- Achievement ID 5: "First Victory"
        SELECT COUNT(*) INTO total_wins
        FROM GameParticipant
        WHERE PlayerID = p_PlayerID AND IsWinner = 1;
        
        IF total_wins = 1 THEN
            INSERT IGNORE INTO PlayerAchievement (PlayerID, AchievementID, DateEarned)
            VALUES (p_PlayerID, 5, NOW());
            IF ROW_COUNT() > 0 THEN
                INSERT INTO NewAchievements (AchievementID, Name)
                SELECT AchievementID, Name FROM Achievement WHERE AchievementID = 5;
            END IF;
        END IF;
        
    END IF; 

    -- 3. Check "Any Game" Achievements (Win or Lose)
    
    -- Achievement ID 6: "On the Board"
    SELECT COUNT(*) INTO total_games
    FROM GameParticipant
    WHERE PlayerID = p_PlayerID;
    
    IF total_games = 1 THEN
        INSERT IGNORE INTO PlayerAchievement (PlayerID, AchievementID, DateEarned)
        VALUES (p_PlayerID, 6, NOW());
        IF ROW_COUNT() > 0 THEN
            INSERT INTO NewAchievements (AchievementID, Name)
            SELECT AchievementID, Name FROM Achievement WHERE AchievementID = 6;
        END IF;
    END IF;
    
    -- 4. Return all newly granted achievements
    SELECT * FROM NewAchievements;

END$$

DELIMITER ;






