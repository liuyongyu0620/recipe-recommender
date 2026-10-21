# logic.py
from werkzeug.security import generate_password_hash, check_password_hash
from model import User, Ingredient, Recipe, RecipeIngredient, UserFridge, UserAvoid
from recommend import recommend_by_names, recommend_by_ids, recommend_weighted
from db.db import db
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import os


#Groq API Key，請自行設定環境變數或在此處填入。
#其實不能放出來


os.environ['GROQ_API_KEY'] = '(yourlink)'
import json
import re
from datetime import datetime


# Groq (OpenAI-compatible) 客戶端
try:
    from groq import Groq
except Exception:
    Groq = None


# ===== Pydantic 模型定義 =====
class IngredientItem(BaseModel):
    name: str
    amount: str


class AIRecipe(BaseModel):
    title: str
    description: str
    ingredients: List[IngredientItem]
    steps: List[str]
    missing_ingredients: List[str]
    cooking_time: str
    difficulty: str


# ===== AI 客戶端初始化（Lazy） =====
_ai_client = None
_ai_provider = None


def _get_ai_client_and_provider():
    """惰性初始化（Groq-only），僅在需要生成食譜時才建立 AI 連線。"""
    global _ai_client, _ai_provider
    if _ai_client is not None:
        return _ai_client, _ai_provider


    groq_key = os.getenv("GROQ_API_KEY")
   
    # 使用 Groq
    if groq_key and groq_key.strip() and Groq is not None:
        try:
            _ai_client = Groq(api_key=groq_key)
            _ai_provider = "groq"
            print("已準備 Groq API（僅在生成食譜時調用）")
            return _ai_client, _ai_provider
        except Exception as e:
            print(f"Groq 初始化失敗: {e}")
            _ai_client = None
   
    print("未設置 GROQ_API_KEY，將使用模擬模式")
    return None, None


def register_user(username, password):
    """註冊新使用者"""
    if User.query.filter_by(username=username).first():
        return None  # 使用者已存在
   
    hashed_password = generate_password_hash(password)
    new_user = User(username=username, password_hash=hashed_password)
    db.session.add(new_user)
    db.session.commit()
    return new_user


def login_user(username, password):
    """驗證使用者登入"""
    user = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.password_hash, password):
        return user
    return None


def change_user_password(user_id, current_password, new_password):
    """修改使用者密碼"""
    user = db.session.get(User, user_id)
    if not user:
        return False  # 使用者不存在
   
    # 驗證目前密碼
    if not check_password_hash(user.password_hash, current_password):
        return False  # 目前密碼不正確
   
    # 更新密碼
    user.password_hash = generate_password_hash(new_password)
    db.session.commit()
    return True


def get_all_ingredients():
    """獲取所有食材"""
    return Ingredient.query.all()


def get_recipe_by_id(recipe_id):
    """根據食譜ID獲取食譜"""
    return db.session.get(Recipe, recipe_id)


def recommend_recipes(user_id, ingredient_ids):
    """
    根據食材 ID 推薦食譜（給「搜尋現有食譜」用）
    回傳：僅包含 Recipe 物件的列表
    """
    items = recommend_by_names(user_id, ingredient_ids)  # list[dict]
    # 只拿 Recipe 出來給 app.py 用
    return [item["recipe"] for item in items]




def recommend_recipes_by_ids(user_id, ingredient_ids):
    """根據食材ID推薦食譜（委派到 recommend 模組）"""
    return recommend_by_ids(user_id, ingredient_ids)


def recommend_recipes_by_algorithm(user_id, ingredient_ids, algorithm='match'):
    """
    根據選擇的演算法推薦食譜
   
    參數:
    - user_id: 使用者 ID
    - ingredient_ids: 食材 ID 列表
    - algorithm: 演算法類型 ('match', 'weighted', 'broad')
   
    回傳:
    - 推薦食譜列表
    """
    if algorithm == 'weighted':
        # 加權評分：需要冰箱所有食材
        fridge_items = get_user_fridge(user_id)
        fridge_ingredient_ids = [item.ingredient_id for item in fridge_items]
        return recommend_weighted(user_id, ingredient_ids, fridge_ingredient_ids)
    elif algorithm == 'broad':
        # 廣泛搜尋：只要包含任一食材
        return recommend_by_names(user_id, ingredient_ids)
    else:
        # 預設：匹配率優先
        return recommend_by_ids(user_id, ingredient_ids)




def recommend_recipes_weighted(user_id, checked_ingredient_ids):
    """
    使用加權演算法推薦食譜。


    委派到 recommend.recommend_weighted，並預先準備好所需的冰箱食材列表。
    """
    # 獲取使用者冰箱中的所有食材 ID
    fridge_items = get_user_fridge(user_id)
    fridge_ingredient_ids = [item.ingredient_id for item in fridge_items]
   
    # 呼叫加權推薦函式
    return recommend_weighted(user_id, checked_ingredient_ids, fridge_ingredient_ids)


def add_ingredient_to_fridge(user_id, ingredient_id, expiry_date=None):
    """將食材添加到使用者冰箱（可選 expiry_date）"""
    user = db.session.get(User, user_id)
    if not user:
        return None

    existing = UserFridge.query.filter_by(user_id=user_id, ingredient_id=ingredient_id).first()
    if existing:
        # 如果有傳 expiry_date，就更新（讓使用者可透過「再新增一次」來修改日期）
        if expiry_date is not None:
            existing.expiry_date = expiry_date
            db.session.commit()
        return existing

    fridge_item = UserFridge(user_id=user_id, ingredient_id=ingredient_id, expiry_date=expiry_date)
    db.session.add(fridge_item)
    db.session.commit()
    return fridge_item


def get_user_fridge(user_id):
    """獲取使用者冰箱中的所有食材"""
    fridge_items = UserFridge.query.filter_by(user_id=user_id).all()
    return fridge_items


def delete_fridge_item(user_id, ingredient_id):
    """從使用者冰箱刪除食材"""
    fridge_item = UserFridge.query.filter_by(user_id=user_id, ingredient_id=ingredient_id).first()
    if fridge_item:
        db.session.delete(fridge_item)
        db.session.commit()
        return True
    return False




# 忌口管理函數
def add_ingredient_to_avoid(user_id, ingredient_id):
    """將食材添加到使用者的忌口列表"""
    # 檢查使用者是否存在
    user = db.session.get(User, user_id)
    if not user:
        return None  # 使用者不存在
   
    # 檢查食材是否已在忌口列表中
    existing = UserAvoid.query.filter_by(user_id=user_id, ingredient_id=ingredient_id).first()
    if existing:
        return existing
   
    avoid_item = UserAvoid(user_id=user_id, ingredient_id=ingredient_id)
    db.session.add(avoid_item)
    db.session.commit()
    return avoid_item




def get_user_avoid(user_id):
    """獲取使用者的忌口列表中的所有食材"""
    avoid_items = UserAvoid.query.filter_by(user_id=user_id).all()
    return avoid_items




def delete_avoid_item(user_id, ingredient_id):
    """從使用者的忌口列表刪除食材"""
    avoid_item = UserAvoid.query.filter_by(user_id=user_id, ingredient_id=ingredient_id).first()
    if avoid_item:
        db.session.delete(avoid_item)
        db.session.commit()
        return True
    return False




def generate_ai_recipe_for_user(user_id, selected_ingredient_ids=None):
    """
    使用 Groq AI 生成創意食譜
   
    Args:
        user_id: 用戶 ID
        selected_ingredient_ids: 選定的食材 ID 列表（如果為 None，則使用冰箱全部食材）
   
    Returns:
        AIRecipe 物件或 error dict
    """
    # 1. 獲取食材清單
    if selected_ingredient_ids is None:
        fridge_items = get_user_fridge(user_id)
        selected_ingredient_ids = [item.ingredient_id for item in fridge_items]
   
    if not selected_ingredient_ids:
        return {"error": "沒有選擇食材，無法生成食譜"}
   
    # 獲取食材名稱
    inventory_list = []
    for ing_id in selected_ingredient_ids:
        ingredient = db.session.get(Ingredient, ing_id)
        if ingredient:
            inventory_list.append(ingredient.name)
   
    if not inventory_list:
        return {"error": "找不到選擇的食材"}


    # 2. 獲取用戶忌口
    avoid_items = get_user_avoid(user_id)
    avoid_list = [item.ingredient.name for item in avoid_items]


    # 3. 構建 Prompt (English)
    system_prompt = """You are a professional nutritionist and chef. Design a delicious, creative recipe based ONLY on the user's available ingredients.
Rules:
1. Use ONLY ingredients from the user's available list - do not suggest any missing ingredients.
2. The recipe must be completable with the provided ingredients only.
3. Must avoid the user's "avoid ingredients" (allergies/dislikes).
4. Please respond in English.
5. Generate a new, creative recipe, not an existing classic dish.
6. The result must be in valid JSON format."""


    user_prompt = f"""I want to cook with these ingredients: {', '.join(inventory_list)}
I cannot eat these ingredients (avoid): {', '.join(avoid_list) if avoid_list else "None"}


Please design a creative dish using ONLY these available ingredients. Do not suggest any missing ingredients.
Respond in the following JSON format:
{{
  "title": "Recipe Name",
  "description": "Brief description (2-3 sentences)",
  "ingredients": [
    {{"name": "ingredient name", "amount": "quantity"}},
    ...
  ],
  "steps": ["Step 1", "Step 2", ...],
  "missing_ingredients": [],
  "cooking_time": "cooking time (e.g., 25 minutes)",
  "difficulty": "difficulty (Easy/Medium/Hard)"
}}


Important: Only respond with the JSON object, no other text. missing_ingredients should always be an empty list."""


    try:
        # 惰性取得 AI 客戶端（僅此函式會觸發）
        client, ai_provider = _get_ai_client_and_provider()


        # 如果沒有 API Client，返回模擬數據
        if not client or ai_provider is None:
            print("⚠️ Using mock AI response (no API Key)")
            return AIRecipe(
                title="Creative Recipe",
                description="A creative dish designed based on your ingredients.",
                ingredients=[IngredientItem(name=ing, amount="appropriate amount") for ing in inventory_list[:3]],
                steps=["Prepare ingredients", "Mix seasonings", "Cook", "Serve"],
                missing_ingredients=[],
                cooking_time="20 minutes",
                difficulty="Easy"
            )


        # 4. 呼叫 Groq
        if ai_provider == "groq":
            # 使用 Llama 3.3 70B（或 Mixtral）
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
            )
            response_text = completion.choices[0].message.content
        else:
            return {"error": "未設置支持的 AI 提供商"}


        # 解析 JSON（容錯提取）
        json_match = re.search(r'\{[\s\S]*\}', response_text or "")
        if not json_match:
            raise ValueError("無法解析 AI 回應的 JSON 格式")


        recipe_data = json.loads(json_match.group())
        recipe_result = AIRecipe(
            title=recipe_data.get("title", "創意料理"),
            description=recipe_data.get("description", ""),
            ingredients=[IngredientItem(name=ing.get("name", ""), amount=ing.get("amount", "適量"))
                        for ing in recipe_data.get("ingredients", [])],
            steps=recipe_data.get("steps", []),
            missing_ingredients=[],  # 強制設置為空，生成的食譜不應有缺失食材
            cooking_time=recipe_data.get("cooking_time", "未知"),
            difficulty=recipe_data.get("difficulty", "未知")
        )
        print(f"成功生成食譜：{recipe_result.title}")
        return recipe_result


    except Exception as e:
        print(f"AI 食譜生成失敗: {e}")
        return {"error": f"AI 生成失敗: {str(e)}"}
