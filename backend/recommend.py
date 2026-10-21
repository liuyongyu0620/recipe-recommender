# backend/recommend.py
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy import func
from datetime import date
from db.db import db
from model import Recipe, RecipeIngredient, UserFridge, UserAvoid
from sqlalchemy.orm import joinedload
from datetime import date as _date

def _expiry_level(expiry_date):
    """把 expiry_date 轉成等級：0(過期)/3/5/7/999(>7天)/None(未設定)"""
    if not expiry_date:
        return None
    days_left = (expiry_date - _date.today()).days
    if days_left < 0:
        return 0
    if days_left <= 3:
        return 3
    if days_left <= 5:
        return 5
    if days_left <= 7:
        return 7
    return 999

def _get_user_expiry_level_map(user_id: Optional[int]) -> Dict[int, Optional[int]]:
    """ingredient_id -> expiry_level"""
    if user_id is None:
        return {}
    rows = UserFridge.query.filter_by(user_id=user_id).all()
    return {r.ingredient_id: _expiry_level(r.expiry_date) for r in rows}

# 權重：你可以自行調整（越大越偏向即期）
_EXPIRY_WEIGHT = {
    0: -2.0,   # 已過期：稍微扣分（你也可以改成 0 不扣分）
    3:  3.0,   # 3 日內：最高加分
    5:  2.0,   # 5 日內：中加分
    7:  1.0,   # 7 日內：小加分
    999: 0.0,  # >7 天：不加分
    None: 0.0  # 未設定：不加分
}

def _get_user_sets(user_id: Optional[int]) -> Tuple[set[int], set[int]]:
    """
    回傳：
    - fridge_ids: 使用者冰箱裡所有 ingredient_id
    - avoid_ids: 使用者避免食材的 ingredient_id
    """
    fridge_ids: set[int] = set()
    avoid_ids: set[int] = set()

    if user_id is None:
        return fridge_ids, avoid_ids

    fridge_items = UserFridge.query.filter_by(user_id=user_id).all()
    fridge_ids = {item.ingredient_id for item in fridge_items}

    avoid_rows = UserAvoid.query.filter_by(user_id=user_id).all()
    avoid_ids = {row.ingredient_id for row in avoid_rows}

    return fridge_ids, avoid_ids


def _build_match_query(ingredient_ids: List[int], avoid_ids: set[int]):
    """
    建立共同的查詢：
    - 只挑出「至少包含一個指定 ingredient_ids」的食譜
    - 會計算:
        matched_count: 食譜中有多少個食材在 ingredient_ids 裡
        total_ingredients: 食譜一共有多少個食材
        match_ratio: matched_count / total_ingredients
    """
    if not ingredient_ids:
        return None

    ri = RecipeIngredient
    ids = list(set(ingredient_ids))  # 去重

    # 1) 計算 matched_count
    matching = (
        db.session.query(
            ri.recipe_id.label("recipe_id"),
            func.count(func.distinct(ri.ingredient_id)).label("matched_count"),
        )
        .filter(ri.ingredient_id.in_(ids))
        .group_by(ri.recipe_id)
        .subquery()
    )

    # 2) 計算每個 recipe 的 total_ingredients
    total = (
        db.session.query(
            ri.recipe_id.label("recipe_id"),
            func.count(func.distinct(ri.ingredient_id)).label("total_ingredients"),
        )
        .group_by(ri.recipe_id)
        .subquery()
    )

    # 3) 主查詢：Recipe + matched_count + total_ingredients + match_ratio
    query = (
        db.session.query(
            Recipe,
            matching.c.matched_count,
            total.c.total_ingredients,
            (matching.c.matched_count / func.nullif(total.c.total_ingredients, 0)).label(
                "match_ratio"
            ),
        )
        .join(matching, Recipe.recipe_id == matching.c.recipe_id)
        .join(total, Recipe.recipe_id == total.c.recipe_id)
    )

    # 若有避免食材，排除含有避免食材的食譜
    if avoid_ids:
        avoid_sub = (
            db.session.query(ri.recipe_id)
            .filter(ri.ingredient_id.in_(list(avoid_ids)))
            .subquery()
        )
        query = query.filter(~Recipe.recipe_id.in_(avoid_sub))

    return query


def _chunk(seq, size: int):
    for i in range(0, len(seq), size):
        yield seq[i:i+size]


def _build_result_items(rows, fridge_ids: set[int]) -> List[Dict[str, Any]]:
    """
    批次版：避免對每個 recipe 再查一次 RecipeIngredient（N+1）
    """
    results: List[Dict[str, Any]] = []
    if not rows:
        return results

    recipe_ids = [recipe.recipe_id for recipe, _, _, _ in rows]

    # 1) 一次把所有 RecipeIngredient + Ingredient 取回來（joinedload 避免 ingredient.name 再觸發查詢）
    by_recipe: Dict[int, List[RecipeIngredient]] = {rid: [] for rid in recipe_ids}

    # IN 太大時分批（MySQL/SQLAlchemy 通常 500~1000 較穩）
    for chunk_ids in _chunk(recipe_ids, 800):
        ris = (
            RecipeIngredient.query
            .options(joinedload(RecipeIngredient.ingredient))
            .filter(RecipeIngredient.recipe_id.in_(chunk_ids))
            .all()
        )
        for ri in ris:
            by_recipe.setdefault(ri.recipe_id, []).append(ri)

    # 2) 組裝結果（不再打 DB）
    for recipe, matched_count, total_ingredients, match_ratio in rows:
        ris = by_recipe.get(recipe.recipe_id, [])
        recipe_ing_ids = {ri.ingredient_id for ri in ris}

        if fridge_ids:
            available_ids = recipe_ing_ids & fridge_ids
            missing_ids = recipe_ing_ids - fridge_ids
        else:
            available_ids = set()
            missing_ids = recipe_ing_ids

        available_names = [
            ri.ingredient.name for ri in ris if ri.ingredient_id in available_ids and ri.ingredient
        ]
        missing_names = [
            ri.ingredient.name for ri in ris if ri.ingredient_id in missing_ids and ri.ingredient
        ]

        results.append({
            "recipe": recipe,
            "matched_count": int(matched_count or 0),
            "total_ingredients": int(total_ingredients or 0),
            "match_ratio": float(match_ratio or 0.0),
            "available_ingredients": available_names,
            "missing_ingredients": missing_names,
            "available_ingredient_ids": sorted(list(available_ids)),
            "missing_ingredient_ids": sorted(list(missing_ids)),
        })

    return results


# === 即期分級 ===
def _expiry_level(expiry_date):
    """0=過期, 3/5/7=即期等級, 999=>7天, None=未設定"""
    if not expiry_date:
        return None
    days_left = (expiry_date - date.today()).days
    if days_left < 0:
        return 0
    if days_left <= 3:
        return 3
    if days_left <= 5:
        return 5
    if days_left <= 7:
        return 7
    return 999

# === A：即期優先很強的權重 ===
_EXPIRY_WEIGHT = {
    0:  -2.0,  # 過期：強扣分（避免被推上去）
    3:   3.0,  # 3日內：最高加分
    5:   2.0,
    7:   1.0,
    999: 0.0,
    None: 0.0
}

def _get_user_expiry_level_map(user_id: Optional[int]) -> Dict[int, Optional[int]]:
    """ingredient_id -> expiry_level（同食材多筆時取最早到期日）"""
    if user_id is None:
        return {}

    rows = UserFridge.query.filter_by(user_id=user_id).all()

    earliest: Dict[int, Optional[date]] = {}
    for r in rows:
        ing = int(r.ingredient_id)
        dt = r.expiry_date
        if ing not in earliest:
            earliest[ing] = dt
        else:
            # None 視為沒有日期；有日期則取更早的
            if earliest[ing] is None:
                earliest[ing] = dt
            elif dt is not None and dt < earliest[ing]:
                earliest[ing] = dt

    return {ing: _expiry_level(dt) for ing, dt in earliest.items()}

def _attach_expiry_metrics(items: List[Dict[str, Any]], expiry_level_map: Dict[int, Optional[int]]) -> None:
    """在每個 item 上加上 expiry_bonus / expiring_count，供排序使用"""
    for item in items:
        available_ids = item.get("available_ingredient_ids", [])
        bonus = 0.0
        expiring_count = 0

        for ing_id in available_ids:
            lvl = expiry_level_map.get(int(ing_id), None)
            bonus += _EXPIRY_WEIGHT.get(lvl, 0.0)
            if lvl in (0, 3, 5, 7):
                expiring_count += 1

        item["expiry_bonus"] = bonus
        item["expiring_count"] = expiring_count

def recommend_by_ids(
    user_id: Optional[int], ingredient_ids: List[int], limit: int = 50
) -> List[Dict[str, Any]]:
    """
    匹配率優先（match）：
    1) 先以 match_ratio 為主
    2) match_ratio 相同時，用 expiry_bonus / expiring_count 當 tie-breaker
    """
    if not ingredient_ids:
        return []

    fridge_ids, avoid_ids = _get_user_sets(user_id)
    query = _build_match_query(ingredient_ids, avoid_ids)
    if query is None:
        return []

    # 重要：先撈比較多候選，避免 SQL 先 limit 讓 tie-breaker 沒機會發揮
    prelimit = max(limit * 20, 500)

    rows = (
        query.order_by(
            db.text("match_ratio DESC"),
            db.text("matched_count DESC"),
            Recipe.recipe_id.asc(),
        )
        .limit(prelimit)
        .all()
    )

    items = _build_result_items(rows, fridge_ids)

    expiry_level_map = _get_user_expiry_level_map(user_id)
    _attach_expiry_metrics(items, expiry_level_map)

    #  match_ratio 第一順位；同 match_ratio 時，expiry_bonus / expiring_count 越高越前
    items.sort(
        key=lambda x: (
            -float(x.get("match_ratio", 0.0)),
            -int(x.get("expiring_count", 0)),      # ✅ match_ratio 相同時，先看快過期數量
            -float(x.get("expiry_bonus", 0.0)),    # ✅ 再用加權分數作更細的 tie-breaker（可保留）
            -int(x.get("matched_count", 0)),
            int(x["recipe"].recipe_id),
        )
    )


    return items[:limit]



def recommend_by_names(
    user_id: Optional[int], ingredient_ids: List[int], limit: int = 50
) -> List[Dict[str, Any]]:
    """
    「廣泛搜尋」版本（對應 algorithm = 'broad'）：

    - 同樣只挑出至少包含一個指定 ingredient_ids 的食譜
    - 排序較偏向 matched_count 多的在前，其次 match_ratio
    - 回傳格式同 recommend_by_ids
    """
    if not ingredient_ids:
        return []

    fridge_ids, avoid_ids = _get_user_sets(user_id)
    query = _build_match_query(ingredient_ids, avoid_ids)
    if query is None:
        return []

    rows = (
        query.order_by(
            db.text("matched_count DESC"),
            db.text("match_ratio DESC"),
            Recipe.recipe_id.asc(),
        )
        .limit(limit)
        .all()
    )

    return _build_result_items(rows, fridge_ids)
def _expiry_level(expiry_date):
    """把 expiry_date 轉成等級：0(過期)/3/5/7/999(>7天)/None(未設定)"""
    if not expiry_date:
        return None
    days_left = (expiry_date - date.today()).days
    if days_left < 0:
        return 0
    if days_left <= 3:
        return 3
    if days_left <= 5:
        return 5
    if days_left <= 7:
        return 7
    return 999


def _get_user_expiry_level_map(user_id: Optional[int]) -> Dict[int, Optional[int]]:
    """ingredient_id -> expiry_level（若同食材多筆，取最早到期日）"""
    if user_id is None:
        return {}

    rows = UserFridge.query.filter_by(user_id=user_id).all()
    best: Dict[int, Any] = {}  # ingredient_id -> earliest expiry_date

    for r in rows:
        if r.expiry_date is None:
            # 沒設定日期就先跳過，等全部掃完再補 None
            best.setdefault(r.ingredient_id, None)
        else:
            if (best.get(r.ingredient_id) is None) or (r.expiry_date < best[r.ingredient_id]):
                best[r.ingredient_id] = r.expiry_date

    return {ing_id: _expiry_level(dt) for ing_id, dt in best.items()}


# === A：即期優先很強的權重（你可以再調）===
_EXPIRY_WEIGHT = {
    0:  -2.0,  # 已過期：強扣分（避免推薦）
    3:   3.0,  # 3 日內：超高加分
    5:   2.0,  # 5 日內：高加分
    7:   1.0,  # 7 日內：中加分
    999: 0.0,  # >7 天：不加分
    None: 0.0  # 未設定：不加分
}

def recommend_weighted(
    user_id: Optional[int],
    ingredient_ids: List[int],
    fridge_ingredient_ids: List[int],
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """
    加權評分（weighted，A：即期優先很強）：
    1) 先看 expiry_bonus / expiring_count（即期多、越急迫越前）
    2) 再看 match_ratio / matched_count
    """
    if not ingredient_ids:
        return []

    fridge_ids, avoid_ids = _get_user_sets(user_id)
    query = _build_match_query(ingredient_ids, avoid_ids)
    if query is None:
        return []

    # weighted 模式要更大候選集，否則容易看起來「沒變」
    prelimit = max(limit * 80, 5000)

    rows = (
        query.order_by(
            db.text("matched_count DESC"),
            db.text("match_ratio DESC"),
            Recipe.recipe_id.asc(),
        )
        .limit(prelimit)
        .all()
    )

    items = _build_result_items(rows, fridge_ids)

    expiry_level_map = _get_user_expiry_level_map(user_id)
    _attach_expiry_metrics(items, expiry_level_map)

    # 即期優先很強：先 expiry_bonus，再 expiring_count，再 match_ratio
    items.sort(
        key=lambda x: (
            -float(x.get("expiry_bonus", 0.0)),
            -int(x.get("expiring_count", 0)),
            -float(x.get("match_ratio", 0.0)),
            -int(x.get("matched_count", 0)),
            int(x["recipe"].recipe_id),
        )
    )

    return items[:limit]


