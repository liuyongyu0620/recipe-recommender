from sqlalchemy import Column, Integer, String, Text, Date, ForeignKey
from sqlalchemy.orm import relationship
from db.db import db

class User(db.Model):
    """使用者表"""
    __tablename__ = 'users'
    
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(80), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    preferences = Column(Text, nullable=True)  # 儲存素食、過敏食材等偏好
    
    # 關聯
    fridge = relationship('UserFridge', back_populates='user', cascade='all, delete-orphan')
    avoid = relationship('UserAvoid', back_populates='user', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<User(user_id={self.user_id})>"


class Ingredient(db.Model):
    """食材表"""
    __tablename__ = 'ingredients'
    
    ingredient_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    
    # 關聯
    recipe_ingredients = relationship('RecipeIngredient', back_populates='ingredient')
    user_fridges = relationship('UserFridge', back_populates='ingredient')
    user_avoids = relationship('UserAvoid', back_populates='ingredient')
    
    def __repr__(self):
        return f"<Ingredient(ingredient_id={self.ingredient_id}, name='{self.name}')>"


class Recipe(db.Model):
    """食譜表"""
    __tablename__ = 'recipes'
    
    recipe_id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    steps = Column(Text, nullable=False)  # 做法步驟
    
    # 關聯
    recipe_ingredients = relationship('RecipeIngredient', back_populates='recipe', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<Recipe(recipe_id={self.recipe_id}, title='{self.title}')>"


class RecipeIngredient(db.Model):
    """食譜食材關聯表"""
    __tablename__ = 'recipe_ingredients'
    
    recipe_id = Column(Integer, ForeignKey('recipes.recipe_id'), primary_key=True)
    ingredient_id = Column(Integer, ForeignKey('ingredients.ingredient_id'), primary_key=True)
    
    # 關聯
    recipe = relationship('Recipe', back_populates='recipe_ingredients')
    ingredient = relationship('Ingredient', back_populates='recipe_ingredients')
    
    def __repr__(self):
        return f"<RecipeIngredient(recipe_id={self.recipe_id}, ingredient_id={self.ingredient_id})>"


class UserFridge(db.Model):
    """使用者冰箱表"""
    __tablename__ = 'user_fridge'
    
    user_id = Column(Integer, ForeignKey('users.user_id'), primary_key=True)
    ingredient_id = Column(Integer, ForeignKey('ingredients.ingredient_id'), primary_key=True)
    
    # 關聯
    user = relationship('User', back_populates='fridge')
    ingredient = relationship('Ingredient', back_populates='user_fridges')
    
    def __repr__(self):
        return f"<UserFridge(user_id={self.user_id}, ingredient_id={self.ingredient_id})>"


class UserAvoid(db.Model):
    """使用者忌口表"""
    __tablename__ = 'user_avoid'
    
    user_id = Column(Integer, ForeignKey('users.user_id'), primary_key=True)
    ingredient_id = Column(Integer, ForeignKey('ingredients.ingredient_id'), primary_key=True)
    
    # 關聯
    user = relationship('User', back_populates='avoid')
    ingredient = relationship('Ingredient', back_populates='user_avoids')
    
    def __repr__(self):
        return f"<UserAvoid(user_id={self.user_id}, ingredient_id={self.ingredient_id})>"
