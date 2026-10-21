import ast
import pandas as pd
import mysql.connector

# ======== 0. MySQL 連線設定 ========
DB_CONFIG = {
    "host": "localhost",
    "user": "root",          # 改成你的帳號
    "password": "(yourpassword)",   # 改成你的密碼
    "database": "dbProject",
    "charset": "utf8mb4",
}

# 想匯入的食譜數量（例如 210000 筆）
TARGET_RECIPES = 210000

# RecipeNLG CSV 檔路徑
CSV_PATH = "C:/Users/User/database_project/backend/RecipeNLG_dataset.csv"  # 依實際路徑調整


def get_connection():
    return mysql.connector.connect(**DB_CONFIG)


def main():
    conn = get_connection()
    cursor = conn.cursor()

    # 用來避免一直查 DB：記錄已經看過的食材
    ingredient_cache = {}  # key: 食材名稱(lower) → ingredient_id

    def get_or_create_ingredient(name: str):
        """回傳 ingredients.ingredient_id，如果沒有就新增一筆"""
        key = name.strip().lower()
        if not key:
            return None

        if key in ingredient_cache:
            return ingredient_cache[key]

        cursor.execute(
            "SELECT ingredient_id FROM ingredients WHERE name = %s",
            (key,),
        )
        row = cursor.fetchone()
        if row:
            ingredient_id = row[0]
        else:
            cursor.execute(
                "INSERT INTO ingredients (name) VALUES (%s)",
                (key,),
            )
            ingredient_id = cursor.lastrowid

        ingredient_cache[key] = ingredient_id
        return ingredient_id

    imported_count = 0
    chunksize = 5000  # 一次讀 5000 列

    # 只讀會用到的欄位：title / directions / NER / ingredients
    usecols = ["title", "directions", "NER", "ingredients"]

    for chunk in pd.read_csv(CSV_PATH, usecols=usecols, chunksize=chunksize):
        for idx, row in chunk.iterrows():
            if imported_count >= TARGET_RECIPES:
                break

            # ---------- 1) 組 recipes ----------
            title = row.get("title")
            if pd.isna(title) or not str(title).strip():
                title = "Untitled"

            # directions: ["step1", "step2"] → "step1\nstep2"
            directions_raw = row.get("directions")
            steps_text = ""
            if isinstance(directions_raw, str):
                try:
                    dir_list = ast.literal_eval(directions_raw)
                    if isinstance(dir_list, list):
                        steps_text = "\n".join(str(s) for s in dir_list)
                    else:
                        steps_text = str(directions_raw)
                except Exception:
                    steps_text = str(directions_raw)

            # ingredients: CSV 中的食材欄位
            ingredients_raw = row.get("ingredients", "")
            ingredients_text = str(ingredients_raw) if not pd.isna(ingredients_raw) else ""

            external_id = str(imported_count)  # 或用 idx 也可以

            # **插入 recipes 表**
            cursor.execute(
                """
                INSERT INTO recipes (title, steps, ingredients, external_id)
                VALUES (%s, %s, %s, %s)
                """,
                (title, steps_text, ingredients_text, external_id),
            )
            recipe_id = cursor.lastrowid

            # ---------- 2) 組 recipe_ingredients + ingredients ----------
            ner_raw = row.get("NER")
            ing_list = []

            if isinstance(ner_raw, str):
                try:
                    ing_list = ast.literal_eval(ner_raw)  # "['milk','egg']" → ['milk','egg']
                except Exception:
                    ing_list = []

            for ing_name in ing_list:
                ing_name = str(ing_name)
                ingredient_id = get_or_create_ingredient(ing_name)
                if not ingredient_id:
                    continue

                cursor.execute(
                    """
                    INSERT IGNORE INTO recipe_ingredients (recipe_id, ingredient_id)
                    VALUES (%s, %s)
                    """,
                    (recipe_id, ingredient_id),
                )

            imported_count += 1

            if imported_count % 1000 == 0:
                conn.commit()
                print(f"已匯入 {imported_count} 筆食譜")

        if imported_count >= TARGET_RECIPES:
            break

    conn.commit()
    cursor.close()
    conn.close()
    print(f"匯入完成 總筆數：{imported_count}")


if __name__ == "__main__":
    main()
