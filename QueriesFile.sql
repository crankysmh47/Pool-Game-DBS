-- -----------------------------------------------------
-- Database pool_game_db
-- -----------------------------------------------------
-- We are using InnoDB because it supports foreign keys
SET default_storage_engine=InnoDB;

-- -----------------------------------------------------
-- Table Player (with secure password hashing)
-- -----------------------------------------------------
CREATE TABLE Player (
  PlayerID INT NOT NULL AUTO_INCREMENT,
  Username VARCHAR(50) NOT NULL UNIQUE,
  PasswordHash VARCHAR(256) NOT NULL,
  Salt VARCHAR(128) NOT NULL,
  DateCreated TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (PlayerID)
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
  PRIMARY KEY (AchievementID)
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
-- -----------------------------------------------------
CREATE TABLE GameParticipant (
  GameSessionID INT NOT NULL,
  PlayerID INT NOT NULL,
  Score INT NOT NULL DEFAULT 0,
  IsWinner BOOLEAN NOT NULL DEFAULT FALSE,
  -- Composite Primary Key
  PRIMARY KEY (GameSessionID, PlayerID),
  -- Foreign Keys
  FOREIGN KEY (GameSessionID) REFERENCES GameSession(GameSessionID) ON DELETE CASCADE,
  FOREIGN KEY (PlayerID) REFERENCES Player(PlayerID) ON DELETE CASCADE
);

-- -----------------------------------------------------
-- Transactional Table: GameEvent (The Log)
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
  -- Foreign Keys
  FOREIGN KEY (GameSessionID) REFERENCES GameSession(GameSessionID) ON DELETE CASCADE,
  FOREIGN KEY (PlayerID) REFERENCES Player(PlayerID) ON DELETE CASCADE,
  FOREIGN KEY (PocketID) REFERENCES Pocket(PocketID)
);

-- -----------------------------------------------------
-- Associative/Weak Table: PlayerAchievement (M:N)
-- -----------------------------------------------------
CREATE TABLE PlayerAchievement (
  PlayerID INT NOT NULL,
  AchievementID INT NOT NULL,
  DateEarned TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  -- Composite Primary Key
  PRIMARY KEY (PlayerID, AchievementID),
  -- Foreign Keys
  FOREIGN KEY (PlayerID) REFERENCES Player(PlayerID) ON DELETE CASCADE,
  FOREIGN KEY (AchievementID) REFERENCES Achievement(AchievementID) ON DELETE CASCADE
);
  
  // A unique, random string (e.g., 16 bytes) generated 
  // at registration, also stored as a string.
  Salt varchar(128) [not null]
  
  DateCreated timestamp [default: `now()`]
}


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


-- 2. Insert the complete, correct list
INSERT INTO Achievement (AchievementID, Name, Description,difficultyID) VALUES
(1, 'Speed Demon', 'Win a game in under 90 seconds.',NULL),
(2, 'Sharpshooter', 'Win a game in 10 shots or less.',NULL),
(3, 'Pool Shark', 'Win a game on Hard difficulty.',3),
(4, 'Hardcore', 'Win on Hard difficulty with 0 fouls.',3),
(5, 'First Victory', 'Win your first game.',NULL),
(6, 'On the Board', 'Play your first game to completion.',NULL),
(7, 'Combo Shot', 'Pot 2 or more balls in a single shot.',NULL),
(8, 'First Potter', 'Pot your very first ball.',NULL);



alter table achievement
add column DifficultyID int;

alter table achievement
add constraint 
foreign key (DifficultyID)
references difficultylevel(DifficultyID);

-- Set a custom delimiter
DELIMITER $$

-- This line drops the old version if it exists, so you can re-run this file
DROP PROCEDURE IF EXISTS sp_CheckPlayerAchievements$$

-- Create the new procedure
CREATE PROCEDURE sp_CheckPlayerAchievements (
    -- These are the "inputs" from your Python game
    IN p_PlayerID INT,
    IN p_DifficultyID INT,
    IN p_Timer FLOAT,
    IN p_Shots INT,
    IN p_Fouls INT,
    IN p_DidWin BOOLEAN
)
BEGIN
    -- --- Declare variables at the top ---
    DECLARE total_wins INT;
    DECLARE total_games INT;
    
    -- --- THIS IS THE KEY ---
    -- 1. Create a temporary table to store the achievements we grant
    CREATE TEMPORARY TABLE IF NOT EXISTS NewAchievements (
        AchievementID INT,
        Name VARCHAR(100)
    );
    
    -- Clear it for this session
    TRUNCATE TABLE NewAchievements;


    -- --- 2. Check "Win-Only" Achievements ---
    IF p_DidWin THEN
    
        -- Achievement ID 1: "Speed Demon"
        IF p_Timer < 90 THEN
            INSERT IGNORE INTO PlayerAchievement (PlayerID, AchievementID, DateEarned)
            VALUES (p_PlayerID, 1, NOW());
            -- If we inserted a row, add it to our temporary table
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

        -- --- THIS IS YOUR NEW LOGIC ---
        -- Achievement ID 3: "Pool Shark" (Win on Hard)
        -- Check if player difficulty matches the required difficulty from the table
        IF p_DifficultyID = (SELECT DifficultyID FROM Achievement WHERE AchievementID = 3) THEN
            INSERT IGNORE INTO PlayerAchievement (PlayerID, AchievementID, DateEarned)
            VALUES (p_PlayerID, 3, NOW());
            IF ROW_COUNT() > 0 THEN
                INSERT INTO NewAchievements (AchievementID, Name)
                SELECT AchievementID, Name FROM Achievement WHERE AchievementID = 3;
            END IF;
        END IF;
        
        -- Achievement ID 4: "Hardcore" (Win on Hard, 0 fouls)
        -- A combined check
        IF p_DifficultyID = (SELECT DifficultyID FROM Achievement WHERE AchievementID = 4) AND p_Fouls = 0 THEN
            INSERT IGNORE INTO PlayerAchievement (PlayerID, AchievementID, DateEarned)
            VALUES (p_PlayerID, 4, NOW());
            IF ROW_COUNT() > 0 THEN
                INSERT INTO NewAchievements (AchievementID, Name)
                SELECT AchievementID, Name FROM Achievement WHERE AchievementID = 4;
            END IF;
        END IF;
        -- --- END OF NEW LOGIC ---
        
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
        
    END IF; -- End of win-only checks


    -- --- 3. Check "Any Game" Achievements (Win or Lose) ---
    
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
    

    -- --- 4. Return all newly granted achievements ---
    SELECT * FROM NewAchievements;

END$$

-- Set the delimiter back to normal
DELIMITER ;





select * from achievement;
