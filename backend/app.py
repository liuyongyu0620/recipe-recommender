# app.py
from dotenv import load_dotenv
from datetime import date, datetime
import os

load_dotenv() 

from flask import Flask, request, jsonify, render_template, redirect, url_for
from db.db import db
import logic
from model import *
from flask import send_from_directory, make_response


app = Flask(__name__)


# 資料庫設定
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:(yourpassword)@localhost/dbProject?charset=utf8mb4'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_recycle': 3600,
    'pool_pre_ping': True,
}

@app.get("/service-worker.js")
def service_worker():
    resp = make_response(send_from_directory("static", "service-worker.js"))
    resp.headers["Content-Type"] = "application/javascript"
    return resp

# 初始化資料庫
db.init_app(app)


# # 建立或更新資料表
# with app.app_context():
#     db.create_all()


@app.route("/")
def home():
    return render_template("index.html")


@app.route('/register-page', methods=['GET', 'POST'])
def register_page():
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''

        if not username or not password:
            return render_template('register.html', error="Please enter username and password."), 400

        user = logic.register_user(username, password)
        if user:
            # 註冊成功 -> 導到登入頁
            return redirect(url_for('login_page'))
        else:
            return render_template('register.html', error="Username already exists."), 409

    return render_template('register.html')


@app.route('/login-page', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''

        if not username or not password:
            return render_template('login.html', error="Please enter username and password."), 400

        user = logic.login_user(username, password)
        if user:
            # 登入成功 -> 導到 dashboard
            return redirect(url_for('dashboard', user_id=user.user_id))
        else:
            return render_template('login.html', error="Invalid username or password."), 401

    return render_template('login.html')


@app.route('/dashboard/<int:user_id>')
def dashboard(user_id):
    """登入後的功能選擇頁"""
    return render_template('dashboard.html', user_id=user_id)

@app.route('/fridge/<int:user_id>')
def fridge_page(user_id):
    """
    顯示冰箱頁面
    """
    return render_template('fridge.html', user_id=user_id)


@app.route('/avoid/<int:user_id>')
def avoid_page(user_id):
    """
    顯示忌口管理頁面
    """
    return render_template('avoid.html', user_id=user_id)


@app.route('/settings/<int:user_id>', methods=['GET', 'POST'])
def settings_page(user_id):
    """
    Account settings page (change password)
    """
    error = None
    success = None

    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        # basic validation
        if not current_password or not new_password or not confirm_password:
            error = "Please fill in all fields."
        elif len(new_password) < 6:
            error = "New password must be at least 6 characters."
        elif new_password != confirm_password:
            error = "New password and confirmation do not match."
        else:
            ok = logic.change_user_password(user_id, current_password, new_password)
            if ok:
                success = "Password updated successfully."
            else:
                error = "Current password is incorrect."

    return render_template('settings.html', user_id=user_id, error=error, success=success)



@app.route('/recipe/<int:user_id>')
def recipe_page(user_id):
    """
    顯示食譜生成頁面
    """
    return render_template('recipe.html', user_id=user_id)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return redirect(url_for('login_page'))

    # 支援 JSON 或 form
    if request.is_json:
        data = request.get_json(silent=True) or {}
        username = (data.get('username') or '').strip()
        password = data.get('password') or ''
    else:
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''

    if not username or not password:
        if request.is_json:
            return jsonify({"error": "Missing username or password"}), 400
        return render_template('login.html', error="Please enter username and password."), 400

    user = logic.login_user(username, password)

    if user:
        if request.is_json:
            return jsonify({"message": "Login successful", "user_id": user.user_id, "username": user.username}), 200
        return redirect(url_for('dashboard', user_id=user.user_id))
    else:
        if request.is_json:
            return jsonify({"error": "Invalid username or password"}), 401
        return render_template('login.html', error="Invalid username or password."), 401



@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return redirect(url_for('register_page'))

    # 支援 JSON 或 form
    if request.is_json:
        data = request.get_json(silent=True) or {}
        username = (data.get('username') or '').strip()
        password = data.get('password') or ''
    else:
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''

    if not username or not password:
        if request.is_json:
            return jsonify({"error": "Missing username or password"}), 400
        return render_template('register.html', error="Please enter username and password."), 400

    user = logic.register_user(username, password)

    if user:
        if request.is_json:
            return jsonify({"message": "User created successfully", "user_id": user.user_id}), 201
        return redirect(url_for('login_page'))
    else:
        if request.is_json:
            return jsonify({"error": "Username already exists"}), 409
        return render_template('register.html', error="Username already exists."), 409

# --- User Settings ---
@app.route('/api/user/<int:user_id>/change-password', methods=['POST'])
def change_password(user_id):
    """
    修改使用者密碼
    接收 JSON: { "current_password": "...", "new_password": "..." }
    """
    # 驗證使用者是否存在
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
   
    data = request.get_json()
    if not data or 'current_password' not in data or 'new_password' not in data:
        return jsonify({"error": "Missing current_password or new_password"}), 400
   
    current_password = data['current_password']
    new_password = data['new_password']
   
    if len(new_password) < 6:
        return jsonify({"error": "New password must be at least 6 characters"}), 400
   
    success = logic.change_user_password(user_id, current_password, new_password)
   
    if success:
        return jsonify({"message": "Password changed successfully"}), 200
    else:
        return jsonify({"error": "Current password is incorrect"}), 401

def compute_expiry_meta(expiry_date):
    """回傳 (days_left, expiry_level)"""
    if not expiry_date:
        return None, None

    days_left = (expiry_date - date.today()).days

    if days_left < 0:
        level = 0
    elif days_left <= 3:
        level = 3
    elif days_left <= 5:
        level = 5
    elif days_left <= 7:
        level = 7
    else:
        level = 999

    return days_left, level

# --- Fridge Management ---
@app.route('/api/fridge/<int:user_id>', methods=['GET'])
def get_fridge(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    fridge_items = logic.get_user_fridge(user_id)
    if not fridge_items:
        return jsonify({"message": "Fridge is empty", "items": []}), 200

    items_data = []
    for item in fridge_items:
        days_left, expiry_level = compute_expiry_meta(item.expiry_date)
        items_data.append({
            "ingredient_id": item.ingredient.ingredient_id,
            "name": item.ingredient.name,
            "expiry_date": item.expiry_date.isoformat() if item.expiry_date else None,
            "days_left": days_left,
            "expiry_level": expiry_level
        })

    return jsonify({"user_id": user_id, "items": items_data}), 200


@app.route('/api/fridge/<int:user_id>', methods=['POST'])
def add_to_fridge(user_id):
    """
    將食材添加到使用者冰箱
    接收 JSON: { "name": "番茄" } 或 { "ingredient_id": 1 }
    """
    # 驗證使用者是否存在
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
   
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing data"}), 400

    expiry_date_raw = data.get("expiry_date")
    expiry_date = None
    if expiry_date_raw:
        try:
            expiry_date = datetime.strptime(expiry_date_raw, "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"error": "expiry_date format must be YYYY-MM-DD"}), 400

    # 支持通過名稱添加食材（新增功能）
    if 'name' in data:
        ingredient_name = data['name'].strip()
        if not ingredient_name:
            return jsonify({"error": "Ingredient name cannot be empty"}), 400
       
        # 查找或創建食材
        ingredient = Ingredient.query.filter_by(name=ingredient_name).first()
        if not ingredient:
            # 創建新食材
            ingredient = Ingredient(name=ingredient_name)
            db.session.add(ingredient)
            db.session.commit()
       
        ingredient_id = ingredient.ingredient_id
    elif 'ingredient_id' in data:
        # 原有的通過 ID 添加功能
        ingredient_id = data['ingredient_id']
       
        # 檢查食材是否存在
        ingredient = db.session.get(Ingredient, ingredient_id)
        if not ingredient:
            return jsonify({"error": "Ingredient not found"}), 404
    else:
        return jsonify({"error": "Missing ingredient_id or name"}), 400
   
    fridge_item = logic.add_ingredient_to_fridge(user_id, ingredient_id, expiry_date=expiry_date)

   
    if fridge_item:
        days_left, expiry_level = compute_expiry_meta(fridge_item.expiry_date)
        return jsonify({
            "message": "Ingredient added to fridge",
            "ingredient_id": ingredient_id,
            "name": ingredient.name,
            "expiry_date": fridge_item.expiry_date.isoformat() if fridge_item.expiry_date else None,
            "days_left": days_left,
            "expiry_level": expiry_level
        }), 201



@app.route('/api/fridge/<int:user_id>/<int:ingredient_id>', methods=['DELETE'])
def delete_fridge_item(user_id, ingredient_id):
    """
    從冰箱刪除食材
    """
    # 驗證使用者是否存在
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
   
    success = logic.delete_fridge_item(user_id, ingredient_id)
   
    if success:
        return jsonify({"message": "Ingredient removed from fridge"}), 200
    else:
        return jsonify({"error": "Item not found in fridge"}), 404






# --- Recipe Recommendation ---
@app.route('/api/recipes/recommend/<int:user_id>', methods=['GET'])
def recommend_recipes_endpoint(user_id):
    """
    根據使用者冰箱中的食材推薦食譜
    """
    # 驗證使用者是否存在
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
   
    # 獲取使用者冰箱中的食材
    fridge_items = logic.get_user_fridge(user_id)
    if not fridge_items:
        return jsonify({"message": "User fridge is empty", "recipes": []}), 200


    # 用 ingredient_id，比較穩定且效率較好
    ingredient_ids = [item.ingredient_id for item in fridge_items]


    # 推薦食譜（廣泛搜尋）
    recommended = logic.recommend_recipes(user_id, ingredient_ids)


   
    recipes_data = []
    for recipe in recommended:
        recipes_data.append({
            "recipe_id": recipe.recipe_id,
            "title": recipe.title
        })
   
    return jsonify({"user_id": user_id, "recipes": recipes_data}), 200


@app.route('/api/recipes/generate/<int:user_id>', methods=['POST'])
def generate_recipes_from_selection(user_id):
    """
    根據使用者在前端勾選的食材ID生成食譜（不入庫）
    接收 JSON: { "ingredient_ids": [1,2,3], "algorithm": "match" }
    """
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404


    data = request.get_json() or {}
    ingredient_ids = data.get('ingredient_ids')
    algorithm = data.get('algorithm', 'match')  # 預設使用匹配率優先
   
    if not isinstance(ingredient_ids, list) or not ingredient_ids:
        return jsonify({"error": "ingredient_ids must be a non-empty list"}), 400


    recommended = logic.recommend_recipes_by_algorithm(user_id, ingredient_ids, algorithm)


    recipes_data = []
    for item in recommended:
        recipes_data.append({
            "recipe_id": item['recipe'].recipe_id,
            "title": item['recipe'].title,
            "matched_count": item['matched_count'],
            "total_ingredients": item['total_ingredients'],
            "match_ratio": item['match_ratio'],
            "missing_ingredients": item.get('missing_ingredients', []),
            "available_ingredients": item.get('available_ingredients', []),

            "available_ingredient_ids": item.get("available_ingredient_ids", []),
            "missing_ingredient_ids": item.get("missing_ingredient_ids", []),
            "expiry_bonus_norm": item.get("expiry_bonus_norm", 0.0),
            "expiring_count": item.get("expiring_count", 0),
    })



    return jsonify({"user_id": user_id, "recipes": recipes_data}), 200


@app.route('/api/recipes/<int:recipe_id>', methods=['GET'])
def get_recipe_detail(recipe_id):
    """
    獲取食譜的完整詳情
    """
    user_id = request.args.get('user_id', type=int)
    recipe = db.session.get(Recipe, recipe_id)
    if not recipe:
        return jsonify({"error": "Recipe not found"}), 404
   
    # 獲取食譜的食材列表
    recipe_ingredients = RecipeIngredient.query.filter_by(recipe_id=recipe_id).all()
    ingredient_names = [ri.ingredient.name for ri in recipe_ingredients]


    missing_ingredients = []
    if user_id:
        fridge_items = logic.get_user_fridge(user_id)
        fridge_ids = {item.ingredient_id for item in fridge_items}
        recipe_ing_ids = {ri.ingredient_id for ri in recipe_ingredients}
        missing_ids = recipe_ing_ids - fridge_ids
        missing_ingredients = [ri.ingredient.name for ri in recipe_ingredients if ri.ingredient_id in missing_ids]
   
    return jsonify({
        "recipe_id": recipe.recipe_id,
        "title": recipe.title,
        "ingredients": recipe.ingredients,
        "ingredient_list": ingredient_names,
        "steps": recipe.steps,
        "missing_ingredients": missing_ingredients
    }), 200


# --- Avoid Management ---
@app.route('/api/avoid/<int:user_id>', methods=['GET'])
def get_avoid(user_id):
    """
    獲取使用者的忌口列表中的所有食材
    """
    # 驗證使用者是否存在
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
   
    avoid_items = logic.get_user_avoid(user_id)
    if not avoid_items:
        return jsonify({"message": "Avoid list is empty", "items": []}), 200
   
    items_data = []
    for item in avoid_items:
        items_data.append({
            "ingredient_id": item.ingredient.ingredient_id,
            "name": item.ingredient.name
        })
   
    return jsonify({"user_id": user_id, "items": items_data}), 200


@app.route('/api/avoid/<int:user_id>', methods=['POST'])
def add_to_avoid(user_id):
    """
    將食材添加到使用者的忌口列表
    接收 JSON: { "name": "番茄" } 或 { "ingredient_id": 1 }
    """
    # 驗證使用者是否存在
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
   
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing data"}), 400
   
    # 支持通過名稱添加食材
    if 'name' in data:
        ingredient_name = data['name'].strip()
        if not ingredient_name:
            return jsonify({"error": "Ingredient name cannot be empty"}), 400
       
        # 查找或創建食材
        ingredient = Ingredient.query.filter_by(name=ingredient_name).first()
        if not ingredient:
            # 創建新食材
            ingredient = Ingredient(name=ingredient_name)
            db.session.add(ingredient)
            db.session.commit()
       
        ingredient_id = ingredient.ingredient_id
    elif 'ingredient_id' in data:
        # 通過 ID 添加
        ingredient_id = data['ingredient_id']
       
        # 檢查食材是否存在
        ingredient = db.session.get(Ingredient, ingredient_id)
        if not ingredient:
            return jsonify({"error": "Ingredient not found"}), 404
    else:
        return jsonify({"error": "Missing ingredient_id or name"}), 400
   
    avoid_item = logic.add_ingredient_to_avoid(user_id, ingredient_id)
   
    if avoid_item:
        return jsonify({
            "message": "Ingredient added to avoid list",
            "ingredient_id": ingredient_id,
            "name": ingredient.name
        }), 201
    else:
        return jsonify({"error": "Failed to add ingredient"}), 500


@app.route('/api/avoid/<int:user_id>/<int:ingredient_id>', methods=['DELETE'])
def delete_avoid_item(user_id, ingredient_id):
    """
    從忌口列表刪除食材
    """
    # 驗證使用者是否存在
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
   
    success = logic.delete_avoid_item(user_id, ingredient_id)
   
    if success:
        return jsonify({"message": "Ingredient removed from avoid list"}), 200
    else:
        return jsonify({"error": "Item not found in avoid list"}), 404


# --- AI Recipe Generation ---
@app.route('/api/recipes/generate_ai/<int:user_id>', methods=['POST'])
def generate_ai_recipe_endpoint(user_id):
    """
    使用 AI 生成創意食譜的端點
   
    接收 JSON:
    - { "ingredient_ids": [1, 2, 3] }  ← 選擇特定食材
    - { }  ← 使用冰箱全部食材（空物件）
   
    回傳: 生成的食譜詳細資訊（JSON）
    """
    # 驗證使用者是否存在
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
   
    data = request.get_json() or {}
    selected_ingredient_ids = data.get('ingredient_ids', None)
   
    # 呼叫 logic 中的 AI 生成函式
    result = logic.generate_ai_recipe_for_user(user_id, selected_ingredient_ids)
   
    if isinstance(result, dict) and "error" in result:
        return jsonify(result), 400
   
    # 因為 result 是 Pydantic 物件，需要轉成 dict 才能 jsonify
    recipe_dict = result.model_dump() if hasattr(result, 'model_dump') else result.__dict__
   
    return jsonify({
        "success": True,
        "user_id": user_id,
        "recipe": recipe_dict
    }), 200


if __name__ == '__main__':
    # 注意：在 Windows 上，werkzeug 的重載器可能會導致 db.create_all() 執行兩次。
    # 這在開發中通常是無害的，但在生產中應使用 Flask-Migrate 等工具管理資料庫架構。
    app.run(host="0.0.0.0", port=5000, debug=True)
