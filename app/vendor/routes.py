# app/vendor/routes.py
from flask import jsonify, request, Blueprint
from app import db
from app.models import Vendor, Item, ItemImage

bp = Blueprint('vendor', __name__)


@bp.route('/vendors', methods=['GET'])
def get_vendors():
    vendors = Vendor.query.all()
    return jsonify([vendor.name for vendor in vendors])


@bp.route('/vendor/register', methods=['POST'])
def register_vendor():
    data = request.get_json()
    existing_vendor = Vendor.query.filter_by(email=data.get('email')).first()

    if existing_vendor:
        return jsonify({"msg": "Vendor already exists"}), 409

    new_vendor = Vendor(
        name=data.get('name'),
        email=data.get('email'),
        phone=data.get('phone')
    )
    db.session.add(new_vendor)
    db.session.commit()

    return jsonify({"msg": "Vendor registered successfully"}), 201


@bp.route('/vendor/<int:vendor_id>/items', methods=['POST'])
def add_item(vendor_id):
    vendor = Vendor.query.get_or_404(vendor_id)
    data = request.get_json()

    new_item = Item(
        name=data.get('name'),
        description=data.get('description'),
        price=data.get('price'),
        category=data.get('category'),
        vendor_id=vendor.id
    )
    db.session.add(new_item)
    db.session.commit()

    images = data.get('images', [])
    if len(images) < 1 or len(images) > 7:
        return jsonify({"msg": "An item must have between 1 and 7 images"}), 400

    for image_url in images:
        item_image = ItemImage(item_id=new_item.id, image_url=image_url)
        db.session.add(item_image)

    db.session.commit()

    return jsonify({"msg": "Item added successfully"}), 201
