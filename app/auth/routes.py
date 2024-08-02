# app/auth/routes.py
from flask import jsonify, request, Blueprint
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token
from app import db
from app.models import User
from werkzeug.security import generate_password_hash, check_password_hash
from app.auth.utils import generate_tokens

bp = Blueprint('auth', __name__)


@bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(email=data.get('email')).first()

    if user and check_password_hash(user.password_hash, data.get('password')):
        access_token, refresh_token = generate_tokens(user.user_id)
        return jsonify(access_token=access_token, refresh_token=refresh_token), 200

    return jsonify({"msg": "Bad username or password"}), 401


@bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    existing_user = User.query.filter_by(email=data.get('email')).first()

    if existing_user:
        return jsonify({"msg": "User already exists"}), 409

    hashed_password = generate_password_hash(data.get('password'), method='pbkdf2:sha256')
    new_user = User(
        username=data.get('username'),
        email=data.get('email'),
        password_hash=hashed_password,
        name=data.get('name'),
        phone=data.get('phone'),
        profile_picture='images/profiles/default.jpg'  # or handle file upload as needed
    )
    db.session.add(new_user)
    db.session.commit()

    access_token, refresh_token = generate_tokens(new_user.user_id)
    return jsonify(access_token=access_token, refresh_token=refresh_token), 201


@bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    current_user = get_jwt_identity()
    access_token = create_access_token(identity=current_user)
    return jsonify(access_token=access_token), 200


@bp.route('/logout', methods=['DELETE'])
@jwt_required()
def logout():
    # Implement token revocation here if necessary
    return jsonify({"msg": "Successfully logged out"}), 200
