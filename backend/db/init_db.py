# init_db.py
# 資料庫初始化腳本，用於創建表、插入示例數據和導入食譜
#pip install -r requirements.txt
# 可選：在 PowerShell 設置 Groq 金鑰後啟動應用
# $env:GROQ_API_KEY = "your_groq_api_key"; & "C:\\Users\\user\\AppData\\Local\\Programs\\Python\\Python314\\python.exe" app.py

from app import app, db
from model import User, Ingredient, Recipe, RecipeIngredient, UserFridge, UserAvoid
from werkzeug.security import generate_password_hash

def init_database():
    """初始化數據庫，創建所有表"""
    with app.app_context():
        # 刪除所有現有表（僅用於開發，生產環境不推薦）
        db.drop_all()
        
        # 創建所有表
        db.create_all()
        print("✓ 已創建所有數據表")

def insert_sample_data():
    """插入示例數據"""
    with app.app_context():
        # 創建預設用戶
        user1 = User(username='john_doe', password_hash=generate_password_hash('password123'))
        user2 = User(username='jane_smith', password_hash=generate_password_hash('password456'))
        db.session.add_all([user1, user2])
        db.session.commit()
        print("✓ 已創建用戶")

def import_recipes_from_csv():
    """導入食譜 (可選)"""
    try:
        from import_recipes import main as import_main
        print("\n開始導入食譜...")
        import_main()
        print("✓ 食譜導入完成！")
    except ImportError:
        print("⚠ 找不到 import_recipes 模組")
    except Exception as e:
        print(f"⚠ 導入食譜失敗: {e}")
        

if __name__ == '__main__':
    print("初始化database...")
    init_database()
    print("\n插入預設data...")
    insert_sample_data()
    
    print("\n導入食譜資料...")
    import_recipes_from_csv()
    
    print("\n✓ 初始化完成！")
    print("\n預設用戶帳號密碼：")
    print("  用戶1: john_doe / password123")
    print("  用戶2: jane_smith / password456")