-- 專題用資料庫：dbProject (存在就不要重建)
CREATE DATABASE IF NOT EXISTS dbProject
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE dbProject;
-- =======================================
-- 1. 使用者表 users
CREATE TABLE IF NOT EXISTS users (
    user_id         BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    username        VARCHAR(50) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- 2. 食材表 ingredients
CREATE TABLE IF NOT EXISTS ingredients (
    ingredient_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name          VARCHAR(255) NOT NULL UNIQUE
) ENGINE=InnoDB;

-- CREATE INDEX idx_ingredients_name ON ingredients(name);

-- 3. 食譜表 recipes
CREATE TABLE IF NOT EXISTS recipes (
    recipe_id      BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    external_id    VARCHAR(100) NULL,
    title          VARCHAR(255) NOT NULL,
    ingredients    TEXT NOT NULL,
    steps          TEXT NOT NULL,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- 備註：如需額外的 description 欄位，可添加到上面的表定義中

-- 索引正確寫法
-- CREATE INDEX idx_recipes_title ON recipes(title);

-- 4. 多對多關聯表
-- recipe_ingredients 改成複合主鍵
CREATE TABLE IF NOT EXISTS recipe_ingredients (
    recipe_id      BIGINT UNSIGNED NOT NULL,
    ingredient_id  BIGINT UNSIGNED NOT NULL,
    PRIMARY KEY (recipe_id, ingredient_id),
    CONSTRAINT fk_ri_recipe
      FOREIGN KEY (recipe_id) REFERENCES recipes(recipe_id)
      ON DELETE CASCADE,
    CONSTRAINT fk_ri_ingredient
      FOREIGN KEY (ingredient_id) REFERENCES ingredients(ingredient_id)
      ON DELETE CASCADE
) ENGINE=InnoDB;

-- CREATE INDEX idx_ri_recipe     ON recipe_ingredients(recipe_id);
-- CREATE INDEX idx_ri_ingredient ON recipe_ingredients(ingredient_id);

-- 5. 冰箱表
CREATE TABLE IF NOT EXISTS user_fridge (
    fridge_item_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id        BIGINT UNSIGNED NOT NULL,
    ingredient_id  BIGINT UNSIGNED NOT NULL,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_fridge_user
      FOREIGN KEY (user_id) REFERENCES users(user_id)
      ON DELETE CASCADE,
    CONSTRAINT fk_fridge_ingredient
      FOREIGN KEY (ingredient_id) REFERENCES ingredients(ingredient_id)
      ON DELETE CASCADE
) ENGINE=InnoDB;

-- 新增 user_avoid 表
CREATE TABLE IF NOT EXISTS user_avoid (
    user_id        BIGINT UNSIGNED NOT NULL,
    ingredient_id  BIGINT UNSIGNED NOT NULL,
    PRIMARY KEY (user_id, ingredient_id),
    CONSTRAINT fk_avoid_user
      FOREIGN KEY (user_id) REFERENCES users(user_id)
      ON DELETE CASCADE,
    CONSTRAINT fk_avoid_ingredient
      FOREIGN KEY (ingredient_id) REFERENCES ingredients(ingredient_id)
      ON DELETE CASCADE
) ENGINE=InnoDB;

-- CREATE INDEX idx_avoid_user ON user_avoid(user_id);

-- CREATE INDEX idx_fridge_user   ON user_fridge(user_id);
