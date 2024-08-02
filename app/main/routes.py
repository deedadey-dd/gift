# app/main/routes.py
from flask import jsonify, Blueprint, render_template
from flask_jwt_extended import jwt_required

bp = Blueprint('main', __name__)


@bp.route('/')
def index():
    print('home')
    return jsonify({"msg": "Welcome to the API!"}), 200
    # return render_template('index.html')


@bp.route('/protected', methods=['GET'])
@jwt_required()
def protected():
    return jsonify({"msg": "You have accessed a protected endpoint"}), 200
