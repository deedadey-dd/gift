import random

from flask import Flask, render_template, request, redirect, url_for, flash, Blueprint
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import os
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
from PIL import Image
from app import app, db
from flask_migrate import Migrate

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gifting_platform.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ['SECRET_KEY']
app.config['SECURITY_PASSWORD_SALT'] = os.environ['SECRET_KEY']
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAIL_SERVER'] = os.environ['EMAIL_HOST']
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = os.environ['EMAIL_USER']
app.config['MAIL_PASSWORD'] = os.environ['EMAIL_PASS']
app.config['MAIL_DEFAULT_SENDER'] = os.environ['EMAIL_USER']
db = SQLAlchemy(app)
migrate = Migrate(app, db)
mail = Mail(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

bp = Blueprint('main', __name__)


class User(db.Model, UserMixin):
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(150), nullable=False)
    name = db.Column(db.String(150))
    phone = db.Column(db.String(20))
    profile_picture = db.Column(db.String(150), nullable=True)
    cash_on_hand = db.Column(db.Float, default=0.00)  # New attribute
    wishlists = db.relationship('Wishlist', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return self.user_id


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
    item_image_url = db.Column(db.String(240), nullable=True)
    status = db.Column(db.String(20), default='Pending')
    amount_paid = db.Column(db.Float, default=0.0)
    contributions = db.relationship('Contribution', backref='wishlist_item', lazy=True)


class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(200), nullable=False)
    added_to_wishlist_count = db.Column(db.Integer, default=0)  # Track how many times the item is added


class Contribution(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('wishlist_item.id'), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), nullable=True)
    phone = db.Column(db.String(20), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    message = db.Column(db.String(500), nullable=True)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def generate_reset_token(email):
    s = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    return s.dumps(email, salt=app.config['SECURITY_PASSWORD_SALT'])


def verify_reset_token(token, expiration=3600):
    s = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    try:
        email = s.loads(token, salt=app.config['SECURITY_PASSWORD_SALT'], max_age=expiration)
    except:
        return None
    return email


def send_email(to, subject, template):
    msg = Message(subject, recipients=[to], html=template, sender=app.config['MAIL_USERNAME'])
    mail.send(msg)


# A function to resize images
def resize_image(image_path, output_size):
    with Image.open(image_path) as img:
        img.thumbnail(output_size)
        img.save(image_path)


def handle_contribution(item, amount, name, email, phone, message):
    if amount < item.item_price:
        return False, "Contribution must be equal to or greater than the item price!"

    item.amount_paid += amount
    if item.amount_paid >= item.item_price:
        item.status = 'Filled'
    else:
        item.status = 'Partially Filled'

    db.session.flush()

    contribution = Contribution(
        item_id=item.id,
        name=name,
        email=email,
        phone=phone,
        amount=amount,
        message=message
    )
    db.session.add(contribution)

    extra_amount = amount - item.item_price
    if extra_amount > 0:
        item.wishlist.user.cash_on_hand += extra_amount

    db.session.commit()

    return True, "Contribution successful!"


all_colors = ['009FBD', '3FA2F6', 'FF4191', '36BA98', '597445', 'E0A75E', 'FF6969', '06D001',
              '83B4FF', 'C738BD', 'A1DD70', 'D2649A', '40A578', 'FF76CE', 'AF8260', '41B06E', '5755FE', ]


def card_color():
    return random.choice(all_colors)


# @app.route('/')
# def home():
#     items = Item.query.order_by(Item.added_to_wishlist_count.desc()).all()
#     wishlists = []
#     if current_user.is_authenticated:
#         wishlists = Wishlist.query.filter_by(user_id=current_user.user_id).all()
#     return render_template('index.html', items=items, wishlists=wishlists, card_color=card_color())


@app.route('/')
def home():
    items = Item.query.order_by(Item.added_to_wishlist_count.desc()).all()
    wishlists = []
    if current_user.is_authenticated:
        wishlists = Wishlist.query.filter_by(user_id=current_user.user_id).all()

    # Assign a random color to each item
    items_with_colors = [(item, card_color()) for item in items]

    return render_template('index.html', items_with_colors=items_with_colors, wishlists=wishlists)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        name = request.form['name']
        phone = request.form['phone']
        profile_picture = request.files['profile_picture']

        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('register'))

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('User with this email already exists.', 'danger')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        if profile_picture and profile_picture.filename != '':
            filename = secure_filename(profile_picture.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            profile_picture.save(file_path)

            # Resize the image
            resize_image(file_path, (150, 150))

            profile_picture_url = 'uploads/' + filename  # Updated path to match static directory structure
        else:
            profile_picture_url = 'images/profiles/default.jpg'  # Provide a default image

        new_user = User(username=username, email=email, password_hash=hashed_password,
                        name=name, phone=phone, profile_picture=profile_picture_url)
        db.session.add(new_user)
        db.session.commit()
        flash('User registered successfully!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form['identifier']
        password = request.form['password']
        remember = 'remember' in request.form

        user = User.query.filter((User.email == identifier) | (User.username == identifier)).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user, remember=remember)
            return redirect(url_for('home'))
        else:
            flash('Invalid username/email or password', 'danger')
            return render_template('login.html', error='Invalid username/email or password')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('login'))


@app.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()
        if user:
            token = generate_reset_token(user.email)
            reset_url = url_for('reset_password', token=token, _external=True)
            subject = "Password Reset Requested"
            html = render_template('reset_password_email.html', reset_url=reset_url)
            send_email(user.email, subject, html)
            flash('A password reset link has been sent to your email.', 'success')
        else:
            flash('No account with that email exists.', 'danger')
    return render_template('reset_password_request.html')


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    email = verify_reset_token(token)
    if not email:
        flash('The password reset link is invalid or has expired.', 'danger')
        return redirect(url_for('reset_password_request'))

    if request.method == 'POST':
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('reset_password', token=token))

        user = User.query.filter_by(email=email).first()
        if user:
            user.password_hash = generate_password_hash(password, method='pbkdf2:sha256')
            db.session.commit()
            flash('Your password has been updated!', 'success')
            return redirect(url_for('login'))

    return render_template('reset_password.html', token=token)


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_user.name = request.form['name']
        current_user.phone = request.form['phone']
        if 'profile_picture' in request.files:
            profile_picture = request.files['profile_picture']
            if profile_picture.filename != '':
                filename = secure_filename(profile_picture.filename)
                profile_picture.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                current_user.profile_picture = filename
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))
    return render_template('profile.html')


@app.route('/create_wishlist', methods=['GET', 'POST'])
@login_required
def create_wishlist():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        expiry_date = request.form['expiry_date']
        user_id = current_user.user_id

        new_wishlist = Wishlist(title=title, description=description,
                                expiry_date=datetime.strptime(expiry_date, '%Y-%m-%d'), user_id=user_id)
        db.session.add(new_wishlist)
        db.session.commit()
        flash('Wishlist created successfully!', 'success')
        return redirect(url_for('wishlists'))
    return render_template('create_wishlist.html')


@app.route('/edit_wishlist/<int:wishlist_id>', methods=['GET', 'POST'])
@login_required
def edit_wishlist(wishlist_id):
    wishlist = Wishlist.query.get_or_404(wishlist_id)
    if request.method == 'POST':
        wishlist.expiry_date = datetime.strptime(request.form['expiry_date'], '%Y-%m-%d')
        db.session.commit()
        flash('Wishlist expiry date updated successfully!', 'success')
        return redirect(url_for('wishlists'))
    return render_template('edit_wishlist.html', wishlist=wishlist)


@app.route('/wishlists')
@login_required
def wishlists():
    user_id = current_user.user_id
    user_wishlists = Wishlist.query.filter_by(user_id=user_id).all()

    # Fetch items and calculate financial details for each wishlist
    for wishlist in user_wishlists:
        items = WishlistItem.query.filter_by(wishlist_id=wishlist.wishlist_id).all()
        wishlist.items_summary = items[:5]  # First 5 items for summary
        wishlist.total_price = sum(item.item_price for item in items)
        wishlist.total_contributed = sum(item.amount_paid for item in items)
        wishlist.remaining_amount = wishlist.total_price - wishlist.total_contributed

    # Assign a random color to each wishlist
    wishlists_with_colors = [(wishlist, card_color()) for wishlist in user_wishlists]

    return render_template('wishlists.html', wishlists_with_colors=wishlists_with_colors)


@app.route('/wishlist/<int:wishlist_id>/update_expiry_date', methods=['POST'])
@login_required
def update_expiry_date(wishlist_id):
    wishlist = Wishlist.query.get_or_404(wishlist_id)
    if current_user.user_id == wishlist.user_id:
        new_expiry_date = request.form['expiry_date']
        wishlist.expiry_date = datetime.strptime(new_expiry_date, '%Y-%m-%d').date()
        db.session.commit()
        flash('Expiry date updated successfully!', 'success')
    else:
        flash('You are not authorized to update this wishlist.', 'danger')
    return redirect(url_for('view_wishlist', wishlist_id=wishlist_id))


@app.route('/wishlist/<int:wishlist_id>/view')
def view_wishlist(wishlist_id):
    wishlist = Wishlist.query.get_or_404(wishlist_id)
    wishlist_items = WishlistItem.query.filter_by(wishlist_id=wishlist_id).all()

    today = datetime.today().date()
    wishlist.days_left = (wishlist.expiry_date - today).days

    for item in wishlist_items:
        item.contributions = Contribution.query.filter_by(item_id=item.id).all()

    return render_template('view_wishlist.html', wishlist=wishlist, wishlist_items=wishlist_items, shared=False)


# @app.route('/wishlist/<int:wishlist_id>/add_item', methods=['GET', 'POST'])
# @login_required
# def add_item_to_wishlist(wishlist_id):
#     wishlist = Wishlist.query.get_or_404(wishlist_id)
#     wishlists = Wishlist.query.filter_by(user_id=current_user.user_id).all()
#     search_query = request.args.get('search', '')
#
#     if search_query:
#         items = Item.query.filter(Item.name.ilike(f'%{search_query}%')).all()
#     else:
#         items = Item.query.all()
#
#     if request.method == 'POST':
#         item_id = request.args.get('item_id')  # Get item_id from the URL parameters
#         custom_name = request.form.get('custom_name')
#         custom_price = request.form.get('custom_price')
#         custom_url = request.form.get('custom_url')
#         custom_description = request.form.get('custom_description')
#         custom_image = request.files.get('custom_image')
#
#         if item_id:
#             item = Item.query.get_or_404(item_id)
#             item.added_to_wishlist_count += 1  # Increment the popularity counter
#             wishlist_item = WishlistItem(
#                 wishlist_id=wishlist_id,
#                 item_id=item.id,
#                 item_name=item.name,
#                 item_description=item.description,
#                 item_price=item.price,
#                 item_image_url=item.image_url,
#                 status='Pending'
#             )
#             db.session.add(item)
#         else:
#             # Check that all custom item fields are provided
#             if not custom_name or not custom_price or not custom_description:
#                 flash('Custom item details are incomplete!', 'danger')
#                 return redirect(url_for('add_item_to_wishlist', wishlist_id=wishlist_id))
#
#             if custom_image and custom_image.filename != '':
#                 filename = secure_filename(custom_image.filename)
#                 file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
#                 custom_image.save(file_path)
#
#                 # Resize the image
#                 resize_image(file_path, (300, 300))
#
#                 item_image_url = 'uploads/' + filename  # Updated path to match static directory structure
#             else:
#                 item_image_url = 'images/items/default.jpg'  # Provide a default image
#
#             wishlist_item = WishlistItem(
#                 wishlist_id=wishlist_id,
#                 item_id=None,
#                 item_name=custom_name,
#                 item_description=custom_description,
#                 item_price=custom_price,
#                 item_image_url=item_image_url,
#                 status='Pending'
#             )
#
#         db.session.add(wishlist_item)
#         db.session.commit()
#         flash('Item added to wishlist!', 'success')
#         return redirect(url_for('view_wishlist', wishlist_id=wishlist_id))
#
#     return render_template('add_item_to_wishlist.html', wishlist=wishlist, items=items, wishlists=wishlists)


@app.route('/wishlist/<int:wishlist_id>/add_item', methods=['GET', 'POST'])
@login_required
def add_item_to_wishlist(wishlist_id):
    wishlist = Wishlist.query.get_or_404(wishlist_id)
    wishlists = Wishlist.query.filter_by(user_id=current_user.user_id).all()
    search_query = request.args.get('search', '')

    if search_query:
        items = Item.query.filter(Item.name.ilike(f'%{search_query}%')).all()
    else:
        items = Item.query.all()

    if request.method == 'POST':
        item_id = request.form.get('item_id')  # Get item_id from the form data
        custom_name = request.form.get('custom_name')
        custom_price = request.form.get('custom_price')
        custom_url = request.form.get('custom_url')
        custom_description = request.form.get('custom_description')
        custom_image = request.files.get('custom_image')

        if item_id:
            item = Item.query.get_or_404(item_id)
            item.added_to_wishlist_count += 1  # Increment the popularity counter
            wishlist_item = WishlistItem(
                wishlist_id=wishlist_id,
                item_id=item.id,
                item_name=item.name,
                item_description=item.description,
                item_price=item.price,
                item_image_url=item.image_url,
                status='Pending'
            )
            db.session.add(item)
        else:
            # Check that all custom item fields are provided
            if not custom_name or not custom_price or not custom_description:
                flash('Custom item details are incomplete!', 'danger')
                return redirect(url_for('add_item_to_wishlist', wishlist_id=wishlist_id))

            if custom_image and custom_image.filename != '':
                filename = secure_filename(custom_image.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                custom_image.save(file_path)

                # Resize the image
                resize_image(file_path, (300, 300))

                item_image_url = 'uploads/' + filename  # Updated path to match static directory structure
            else:
                item_image_url = 'images/items/default.jpg'  # Provide a default image

            wishlist_item = WishlistItem(
                wishlist_id=wishlist_id,
                item_id=None,
                item_name=custom_name,
                item_description=custom_description,
                item_price=custom_price,
                item_image_url=item_image_url,
                status='Pending'
            )

        db.session.add(wishlist_item)
        db.session.commit()
        flash('Item added to wishlist!', 'success')
        return redirect(url_for('view_wishlist', wishlist_id=wishlist_id))

    return render_template('add_item_to_wishlist.html', wishlist=wishlist, items=items, wishlists=wishlists)


@app.route('/remove_item_from_wishlist/<int:item_id>', methods=['POST'])
@login_required
def remove_item_from_wishlist(item_id):
    item = WishlistItem.query.get_or_404(item_id)
    wishlist = Wishlist.query.get_or_404(item.wishlist_id)
    if current_user.user_id == wishlist.user_id:
        db.session.delete(item)
        db.session.commit()
        flash('Item removed from wishlist!', 'success')
    else:
        flash('You are not authorized to remove this item.', 'danger')
    return redirect(url_for('view_wishlist', wishlist_id=item.wishlist_id))


# @app.route('/pay_for_item/<int:item_id>', methods=['GET', 'POST'])
# def pay_for_item(item_id):
#     item = WishlistItem.query.get_or_404(item_id)
#     if request.method == 'POST':
#         amount = float(request.form['amount'])
#         name = request.form['name']
#         email = request.form['email']
#         message = request.form['message']
#
#         item.amount_paid += amount
#         if item.amount_paid >= item.item_price:
#             item.status = 'Filled'
#         else:
#             item.status = 'Partially Filled'
#
#         db.session.flush()  # Ensure the item is updated before creating the contribution
#
#         contribution = Contribution(
#             item_id=item.id,
#             name=name,
#             email=email,
#             amount=amount,
#             message=message
#         )
#         db.session.add(contribution)
#         db.session.commit()
#
#         flash('Thank you for your contribution!', 'success')
#         return redirect(url_for('view_shared_wishlist', wishlist_id=item.wishlist_id))
#     return render_template('pay_for_item.html', item=item)

@app.route('/pay_for_item/<int:item_id>', methods=['GET', 'POST'])
def pay_for_item(item_id):
    item = WishlistItem.query.get_or_404(item_id)
    if request.method == 'POST':
        amount = float(request.form['amount'])
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        message = request.form['message']

        item.amount_paid += amount
        if item.amount_paid >= item.item_price:
            item.status = 'Filled'
        else:
            item.status = 'Partially Filled'

        contribution = Contribution(
            item_id=item.id,
            name=name,
            email=email,
            phone=phone,
            amount=amount,
            message=message
        )
        db.session.add(contribution)
        db.session.commit()

        flash('Thank you for your contribution!', 'success')
        return redirect(url_for('view_shared_wishlist', wishlist_id=item.wishlist_id))
    return render_template('pay_for_item.html', item=item)


@app.route('/wishlists/all', methods=['GET'])
def all_wishlists():
    page = request.args.get('page', 1, type=int)
    today = datetime.today().date()
    wishlists = Wishlist.query.filter(Wishlist.expiry_date >= today).paginate(page=page, per_page=10)

    for wishlist in wishlists.items:
        days_left = (wishlist.expiry_date - today).days
        wishlist.days_left = days_left
        items = WishlistItem.query.filter_by(wishlist_id=wishlist.wishlist_id).all()
        wishlist.item_count = len(items)
        wishlist.total_cost = sum(item.item_price for item in items)
        wishlist.total_contributed = sum(item.amount_paid for item in items)
        wishlist.remaining_amount = wishlist.total_cost - wishlist.total_contributed

    # Assign a random color to each wishlist
    wishlists_with_colors = [(wishlist, card_color()) for wishlist in wishlists.items]

    return render_template('all_wishlists.html', wishlists=wishlists_with_colors, pagination=wishlists)


@app.route('/wishlist/share/<int:wishlist_id>')
@login_required
def share_wishlist(wishlist_id):
    wishlist = Wishlist.query.get_or_404(wishlist_id)
    shareable_link = url_for('view_shared_wishlist', wishlist_id=wishlist_id, _external=True)
    return render_template('share_wishlist.html', wishlist=wishlist, shareable_link=shareable_link)


@app.route('/wishlist/shared/<int:wishlist_id>')
def view_shared_wishlist(wishlist_id):
    wishlist = Wishlist.query.get_or_404(wishlist_id)
    wishlist_items = WishlistItem.query.filter_by(wishlist_id=wishlist_id).all()

    today = datetime.today().date()
    wishlist.days_left = (wishlist.expiry_date - today).days

    for item in wishlist_items:
        item.contributions = Contribution.query.filter_by(item_id=item.id).all()

    return render_template('view_wishlist.html', wishlist=wishlist, wishlist_items=wishlist_items, shared=True)


@app.route('/edit_custom_item/<int:item_id>', methods=['GET', 'POST'])
@login_required
def edit_custom_item(item_id):
    item = WishlistItem.query.get_or_404(item_id)
    if current_user.user_id != item.wishlist.user_id:
        flash('You are not authorized to edit this item.', 'danger')
        return redirect(url_for('view_wishlist', wishlist_id=item.wishlist_id))

    if request.method == 'POST':
        item.item_name = request.form['item_name']
        item.item_description = request.form['item_description']
        item.item_price = request.form['item_price']

        # Handle the image upload
        custom_image = request.files.get('custom_image')
        if custom_image and custom_image.filename != '':
            filename = secure_filename(custom_image.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            custom_image.save(file_path)

            # Resize the image
            resize_image(file_path, (300, 300))

            item.item_image_url = 'uploads/' + filename  # Updated path to match static directory structure

        db.session.commit()
        flash('Item updated successfully!', 'success')
        return redirect(url_for('view_wishlist', wishlist_id=item.wishlist_id))

    return render_template('edit_custom_item.html', item=item)


@app.route('/add_store_item', methods=['GET', 'POST'])
@login_required  # Assuming only logged-in users can add items to the store
def add_store_item():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = request.form['price']
        image = request.files['image']

        if image and image.filename != '':
            filename = secure_filename(image.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(file_path)

            # Resize the image
            resize_image(file_path, (300, 300))

            image_url = 'uploads/' + filename  # Updated path to match static directory structure
        else:
            image_url = 'images/items/default.jpg'  # Provide a default image

        new_item = Item(name=name, description=description, price=price, image_url=image_url)
        db.session.add(new_item)
        db.session.commit()
        flash('Item added to the store successfully!', 'success')
        return redirect(url_for('home'))

    return render_template('add_store_item.html')


@app.route('/search_recipient_wishlists', methods=['POST'])
def search_recipient_wishlists():
    username = request.form['recipient_username']
    phone = request.form['recipient_phone']
    item_id = request.form['gift_item_id']

    recipient = User.query.filter_by(username=username, phone=phone).first()
    if not recipient:
        flash('Recipient not found!', 'danger')
        return redirect(url_for('home'))

    wishlists = Wishlist.query.filter_by(user_id=recipient.user_id).all()
    if not wishlists:
        flash('Recipient has no wishlists.', 'info')
        return redirect(url_for('home'))

    item = Item.query.get_or_404(item_id)
    return render_template('recipient_wishlists.html', wishlists=wishlists, item=item)


# @app.route('/gift_item/<int:wishlist_id>/<int:item_id>', methods=['GET', 'POST'])
# def gift_item(wishlist_id, item_id):
#     wishlist = Wishlist.query.get_or_404(wishlist_id)
#     item = Item.query.get_or_404(item_id)
#
#     if request.method == 'POST':
#         contribution_amount = float(request.form['contribution_amount'])
#         giver_name = request.form['giver_name']
#         message = request.form['message']
#
#         if contribution_amount < item.price:
#             flash('Contribution must be equal to or greater than the item price!', 'danger')
#             return redirect(url_for('gift_item', wishlist_id=wishlist_id, item_id=item_id))
#
#         item.added_to_wishlist_count += 1  # Increment the popularity counter
#         wishlist_item = WishlistItem(
#             wishlist_id=wishlist_id,
#             item_id=item.id,
#             item_name=item.name,
#             item_description=item.description,
#             item_price=item.price,
#             item_image_url=item.image_url,
#             status='Pending',
#             amount_paid=contribution_amount  # Mark the item as fully paid
#         )
#
#         db.session.add(wishlist_item)
#         db.session.flush()  # Ensure the wishlist_item is added and item_id is set
#
#         # Add contribution record
#         contribution = Contribution(
#             item_id=wishlist_item.id,
#             name=giver_name,
#             amount=contribution_amount,
#             message=message
#         )
#         db.session.add(contribution)
#
#         # Handle extra contribution as cash-on-hand
#         extra_amount = contribution_amount - item.price
#         if extra_amount > 0:
#             wishlist.user.cash_on_hand += extra_amount
#
#         db.session.commit()
#
#         flash('Item gifted successfully!', 'success')
#         return redirect(url_for('home'))
#
#     return render_template('gift_item.html', wishlist=wishlist, item=item)


@app.route('/gift_item/<int:wishlist_id>/<int:item_id>', methods=['GET', 'POST'])
def gift_item(wishlist_id, item_id):
    wishlist = Wishlist.query.get_or_404(wishlist_id)
    item = Item.query.get_or_404(item_id)

    if request.method == 'POST':
        contribution_amount = float(request.form['contribution_amount'])
        giver_name = request.form['giver_name']
        giver_email = request.form['giver_email']
        giver_phone = request.form['giver_phone']
        message = request.form['message']

        # Check if contribution amount is equal to or greater than the item price
        if contribution_amount < item.price:
            flash('Contribution must be equal to or greater than the item price!', 'danger')
            return redirect(url_for('gift_item', wishlist_id=wishlist_id, item_id=item_id))

        # Add item to wishlist
        wishlist_item = WishlistItem(
            wishlist_id=wishlist_id,
            item_id=item.id,
            item_name=item.name,
            item_description=item.description,
            item_price=item.price,
            item_image_url=item.image_url,
            status='Pending',
            amount_paid=0.0
        )
        db.session.add(wishlist_item)
        db.session.flush()  # Ensure the wishlist_item is added and item_id is set

        # Pass the newly added wishlist item as a parameter into handle_contribution
        success, message = handle_contribution(wishlist_item, contribution_amount, giver_name, giver_email, giver_phone,
                                               message)
        if not success:
            flash(message, 'danger')
            return redirect(url_for('gift_item', wishlist_id=wishlist_id, item_id=item_id))

        flash('Item gifted successfully!', 'success')
        return redirect(url_for('home'))

    return render_template('gift_item.html', wishlist=wishlist, item=item)


@app.route('/wishlist/<int:wishlist_id>/add_store_item/<int:item_id>', methods=['GET'])
@login_required
def add_store_item_to_wishlist(wishlist_id, item_id):
    wishlist = Wishlist.query.get_or_404(wishlist_id)
    item = Item.query.get_or_404(item_id)

    # Check if the item is already in the wishlist
    existing_item = WishlistItem.query.filter_by(wishlist_id=wishlist_id, item_id=item_id).first()
    if existing_item:
        flash('Item is already in the wishlist!', 'info')
        return redirect(url_for('view_wishlist', wishlist_id=wishlist_id))

    # Add item to wishlist
    wishlist_item = WishlistItem(
        wishlist_id=wishlist_id,
        item_id=item.id,
        item_name=item.name,
        item_description=item.description,
        item_price=item.price,
        item_image_url=item.image_url,
        status='Pending'
    )
    item.added_to_wishlist_count += 1  # Increment the popularity counter

    db.session.add(wishlist_item)
    db.session.add(item)
    db.session.commit()

    flash('Item added to wishlist!', 'success')
    return redirect(url_for('view_wishlist', wishlist_id=wishlist_id))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    app.run(debug=True)
