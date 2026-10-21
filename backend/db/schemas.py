from pydantic import BaseModel
from typing import List, Optional

class IngredientItem(BaseModel):
    name: str
    amount: str  # 例如 "2顆", "100g"

class AIRecipe(BaseModel):
    title: str
    description: str
    ingredients: List[IngredientItem] # AI 建議的完整食材清單
    steps: List[str]
    missing_ingredients: List[str] # AI 分析使用者缺少的食材
    cooking_time: str # 例如 "15分鐘"
    difficulty: str # 例如 "簡單"
