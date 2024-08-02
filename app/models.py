# app/models.py
from datetime import datetime
from app import db
from flask_login import UserMixin


class User(db.Model, UserMixin):
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(150), nullable=False)
    name = db.Column(db.String(150))
    phone = db.Column(db.String(20))
    profile_picture = db.Column(db.String(150), nullable=True)
    cash_on_hand = db.Column(db.Float, default=0.0)
    wishlists = db.relationship('Wishlist', backref='user', lazy=True)


class Vendor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    items = db.relationship('Item', backref='vendor', lazy=True)


class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(240))
    price = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(120))
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendor.id'), nullable=False)
    added_to_wishlist_count = db.Column(db.Integer, default=0)
    images = db.relationship('ItemImage', backref='item', lazy=True)


class ItemImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    image_url = db.Column(db.String(240), nullable=False)


class Wishlist(db.Model):
    wishlist_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(240))
    expiry_date = db.Column(db.Date, nullable=False)
    items = db.relationship('WishlistItem', backref='wishlist', lazy=True)


class WishlistItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    wishlist_id = db.Column(db.Integer, db.ForeignKey('wishlist.wishlist_id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=True)
    item_name = db.Column(db.String(120), nullable=False)
    item_description = db.Column(db.String(240))
    item_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='Pending')
    amount_paid = db.Column(db.Float, default=0.0)
    contributions = db.relationship('Contribution', backref='wishlist_item', lazy=True)


class Contribution(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('wishlist_item.id'), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    message = db.Column(db.String(500))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
