# main.py
from app import create_app, db
from app.models import User, Wishlist, WishlistItem, Contribution, Item, Vendor

app = create_app()


@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Wishlist': Wishlist, 'WishlistItem': WishlistItem,
            'Contribution': Contribution, 'Item': Item, 'Vendor': Vendor}


if __name__ == "__main__":
    app.run(debug=True)
