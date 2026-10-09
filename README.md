# Shop4U - Django E-commerce Mini Project

A complete online store: product browsing, search/filter/sort, cart, registration & login,
checkout (Cash on Delivery), safe order processing with stock control, order history and Django Admin.

**Stack:** Python, Django, SQLite, HTML/CSS/JavaScript (no Bootstrap/React/Tailwind). No internet needed.

## Quick start (the database already contains 16 sample products)

You need Python 3.10+ installed. Open a terminal **inside this folder** (the one with `manage.py`).

### Windows (PowerShell / Command Prompt)
```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py load_sample_data
python manage.py createsuperuser
python manage.py runserver
```

### macOS / Linux
```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py load_sample_data
python manage.py createsuperuser
python manage.py runserver
```

Then open **http://127.0.0.1:8000/** (shop) and **http://127.0.0.1:8000/admin/** (admin panel).

What each command does:
1. `venv` - creates an isolated Python environment for this project.
2. `pip install` - installs Django and Pillow (needed for product images).
3. `migrate` - creates/updates the database tables (safe to run again).
4. `load_sample_data` - adds 4 categories + 16 products with pictures (safe to run again).
5. `createsuperuser` - makes your admin login (choose any username/password).
6. `runserver` - starts the website.

## Try it
1. Click **Register**, create a customer account.
2. Browse **Shop**, search, filter, sort, open a product, **Add to Cart**.
3. Open the cart, change quantities, then **Proceed to Checkout** and place the order (COD).
4. See it under **My Orders**. Stock goes down automatically.
5. In `/admin/` change the order status (Pending -> Processing -> Shipped -> Delivered / Cancelled).

Admin can also add/edit/delete products & categories, upload images, set price and stock, and view customers (Users) and orders.

## Run the tests
```
python manage.py test
```
31 tests cover registration, login, listing, details, cart, checkout validation, order placement,
stock handling, cart clearing, order privacy and admin restrictions.

## Folder guide
```
manage.py            start point for all commands
shop4u/              project settings and main urls
store/               the app: models, views, forms, cart logic, admin, tests
  management/commands/load_sample_data.py   sample products
templates/           HTML pages (all extend base.html)
static/css, static/js   styling and small JavaScript helpers
media/products/      product images (uploads from admin go here too)
db.sqlite3           the database file
```

## Good to know
- The cart is stored in the browser session; prices and totals are always recalculated on the server.
- Orders are created inside a database transaction, so a failed stock check never leaves half an order.
- The contact form prints emails in the terminal (no mail server needed).
- Before any real deployment: change `SECRET_KEY`, set `DEBUG = False`, set `ALLOWED_HOSTS`.
- To reset everything: delete `db.sqlite3`, then run `migrate` and `load_sample_data` again.
