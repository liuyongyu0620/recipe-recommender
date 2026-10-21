from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey, BigInteger, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from db.db import db

class User(db.Model):
    """使用者表"""
    __tablename__ = 'users'
    
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(80), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    
    fridge = relationship('UserFridge', back_populates='user', cascade='all, delete-orphan')
    avoid = relationship('UserAvoid', back_populates='user', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<User(user_id={self.user_id})>"


class Ingredient(db.Model):
    """食材表"""
    __tablename__ = 'ingredients'
    
    ingredient_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)
    
    recipe_ingredients = relationship('RecipeIngredient', back_populates='ingredient')
    user_fridges = relationship('UserFridge', back_populates='ingredient')
    user_avoids = relationship('UserAvoid', back_populates='ingredient')
    
    def __repr__(self):
        return f"<Ingredient(ingredient_id={self.ingredient_id}, name='{self.name}')>"


class Recipe(db.Model):
    """食譜表"""
    __tablename__ = 'recipes'
    
    recipe_id = Column(Integer, primary_key=True, autoincrement=True)
    external_id = Column(String(255), nullable=True)
    title = Column(String(200), nullable=False)
    ingredients = Column(Text, nullable=False)
    steps = Column(Text, nullable=False)
    
    recipe_ingredients = relationship('RecipeIngredient', back_populates='recipe', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<Recipe(recipe_id={self.recipe_id}, title='{self.title}')>"


class RecipeIngredient(db.Model):
    """食譜食材關聯表"""
    __tablename__ = 'recipe_ingredients'
    
    recipe_id = Column(Integer, ForeignKey('recipes.recipe_id'), primary_key=True)
    ingredient_id = Column(Integer, ForeignKey('ingredients.ingredient_id'), primary_key=True)
    
    recipe = relationship('Recipe', back_populates='recipe_ingredients')
    ingredient = relationship('Ingredient', back_populates='recipe_ingredients')
    
    def __repr__(self):
        return f"<RecipeIngredient(recipe_id={self.recipe_id}, ingredient_id={self.ingredient_id})>"


class UserFridge(db.Model):
    """使用者冰箱表"""
    __tablename__ = 'user_fridge'

    fridge_item_id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey('users.user_id'), nullable=False)
    ingredient_id = Column(BigInteger, ForeignKey('ingredients.ingredient_id'), nullable=False)

    # 你資料庫已經有這個欄位
    expiry_date = Column(Date, nullable=True)

    created_at = Column(DateTime, server_default=func.current_timestamp())

    # 建議：避免同一使用者同一食材重複出現多筆
    __table_args__ = (
        UniqueConstraint('user_id', 'ingredient_id', name='uq_user_fridge_user_ing'),
    )

    user = relationship('User', back_populates='fridge')
    ingredient = relationship('Ingredient', back_populates='user_fridges')

    def __repr__(self):
        return f"<UserFridge(fridge_item_id={self.fridge_item_id}, user_id={self.user_id}, ingredient_id={self.ingredient_id}, expiry_date={self.expiry_date})>"


class UserAvoid(db.Model):
    """使用者忌口表"""
    __tablename__ = 'user_avoid'
    
    user_id = Column(Integer, ForeignKey('users.user_id'), primary_key=True)
    ingredient_id = Column(Integer, ForeignKey('ingredients.ingredient_id'), primary_key=True)
    
    user = relationship('User', back_populates='avoid')
    ingredient = relationship('Ingredient', back_populates='user_avoids')
    
    def __repr__(self):
        return f"<UserAvoid(user_id={self.user_id}, ingredient_id={self.ingredient_id})>"
