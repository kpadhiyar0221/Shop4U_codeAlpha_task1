"""Create sample categories and products (with generated images).

Usage:  python manage.py load_sample_data
Safe to run many times - it updates existing products instead of duplicating them.
"""
import textwrap
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand
from PIL import Image, ImageDraw, ImageFont

CATEGORIES = {
    "Electronics": ("Gadgets, audio and everyday smart devices.", ((18, 38, 92), (59, 99, 201))),
    "Fashion": ("Clothing and footwear for every day.", ((136, 40, 74), (240, 120, 100))),
    "Home & Living": ("Make your space warm and comfortable.", ((20, 94, 86), (86, 190, 150))),
    "Accessories": ("Bags, watches and little extras.", ((120, 70, 12), (255, 160, 40))),
}

PRODUCTS = [
    ("Electronics", "Wireless Bluetooth Headphones", "Over-ear headphones with deep bass, soft ear cushions and up to 30 hours of battery life. Includes a USB-C charging cable and a carry pouch.", "2499.00", 25),
    ("Electronics", "Smart Fitness Band", "Track steps, heart rate and sleep with a bright colour display. Water resistant, with a 10-day battery and call notifications.", "1799.00", 40),
    ("Electronics", "Portable Power Bank 20000mAh", "Slim fast-charging power bank with two USB ports and one USB-C port. Charges a phone about five times on a single charge.", "1299.00", 60),
    ("Electronics", "Mini Bluetooth Speaker", "Pocket-sized waterproof speaker with clear sound, 12 hours of playtime and a built-in microphone for calls.", "999.00", 3),
    ("Fashion", "Classic Cotton T-Shirt", "Soft 100% combed cotton crew-neck tee in a relaxed everyday fit. Pre-washed so it keeps its shape and colour.", "499.00", 120),
    ("Fashion", "Slim Fit Denim Jeans", "Stretch denim jeans with a comfortable mid-rise waist and a clean dark-wash finish. Easy to dress up or down.", "1499.00", 45),
    ("Fashion", "Lightweight Running Shoes", "Breathable mesh running shoes with cushioned soles and a grippy outsole for roads and tracks.", "2199.00", 30),
    ("Fashion", "Hooded Winter Jacket", "Warm padded jacket with a detachable hood, zip pockets and a wind-resistant outer shell.", "2999.00", 0),
    ("Home & Living", "Ceramic Coffee Mug Set", "Set of four 300 ml glazed ceramic mugs. Microwave and dishwasher safe, in calm neutral colours.", "699.00", 50),
    ("Home & Living", "Cozy Throw Blanket", "Ultra-soft woven throw blanket, 130 x 170 cm. Perfect for the sofa, bed or an evening on the balcony.", "1199.00", 35),
    ("Home & Living", "LED Desk Lamp", "Adjustable desk lamp with three colour temperatures, five brightness levels and a USB charging port.", "1099.00", 28),
    ("Home & Living", "Indoor Plant Pot Set", "Three matte ceramic planters with bamboo trays and drainage holes. Plants not included.", "849.00", 4),
    ("Accessories", "Leather Wallet", "Slim genuine-leather wallet with six card slots, a coin pocket and RFID protection.", "899.00", 70),
    ("Accessories", "Minimalist Analog Watch", "Stainless steel watch with a clean dial, sapphire-style glass and a comfortable adjustable strap.", "3499.00", 15),
    ("Accessories", "Canvas Backpack", "Durable 22-litre backpack with a padded laptop sleeve, water-resistant lining and a hidden anti-theft pocket.", "1599.00", 38),
    ("Accessories", "UV Protection Sunglasses", "Lightweight polarised sunglasses with UV400 lenses and a flexible, scratch-resistant frame.", "749.00", 55),
]


def get_font(size):
    for name in ("DejaVuSans-Bold.ttf", "arialbd.ttf", "Arial Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # very old Pillow
        return ImageFont.load_default()


def make_image(path, title, colors):
    """Draw a simple gradient product picture (no internet needed)."""
    w, h = 800, 600
    (r1, g1, b1), (r2, g2, b2) = colors
    img = Image.new("RGB", (w, h))
    px = ImageDraw.Draw(img)
    for y in range(h):
        t = y / (h - 1)
        px.line([(0, y), (w, y)], fill=(int(r1 + (r2 - r1) * t), int(g1 + (g2 - g1) * t), int(b1 + (b2 - b1) * t)))
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    d.ellipse((470, -120, 900, 310), fill=(255, 255, 255, 38))
    d.ellipse((-140, 330, 300, 770), fill=(255, 255, 255, 28))
    d.rounded_rectangle((90, 170, 710, 430), radius=36, fill=(255, 255, 255, 235))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    d = ImageDraw.Draw(img)
    font = get_font(44)
    lines = textwrap.wrap(title, width=20)[:3]
    line_h = 58
    y = 300 - (len(lines) * line_h) // 2
    for line in lines:
        width = d.textlength(line, font=font)
        d.text(((w - width) / 2, y), line, font=font, fill=(15, 27, 61))
        y += line_h
    d.rounded_rectangle((330, 470, 470, 482), radius=6, fill=(255, 107, 26))
    img.save(path, "JPEG", quality=88)


class Command(BaseCommand):
    help = "Loads sample categories and products for Shop4U."

    def handle(self, *args, **options):
        from store.models import Category, Product

        media_dir = settings.MEDIA_ROOT / "products"
        media_dir.mkdir(parents=True, exist_ok=True)

        cats = {}
        for name, (desc, _) in CATEGORIES.items():
            cats[name], _c = Category.objects.update_or_create(name=name, defaults={"description": desc})

        created = 0
        for cat_name, name, desc, price, stock in PRODUCTS:
            filename = "".join(c if c.isalnum() else "_" for c in name.lower()) + ".jpg"
            file_path = media_dir / filename
            if not file_path.exists():
                make_image(file_path, name, CATEGORIES[cat_name][1])
            _p, was_created = Product.objects.update_or_create(
                name=name,
                defaults={
                    "category": cats[cat_name],
                    "description": desc,
                    "price": Decimal(price),
                    "stock_quantity": stock,
                    "image": f"products/{filename}",
                    "is_active": True,
                },
            )
            created += was_created
        self.stdout.write(self.style.SUCCESS(
            f"Done! {created} new products added, {len(PRODUCTS) - created} updated. Categories: {len(CATEGORIES)}."
        ))
