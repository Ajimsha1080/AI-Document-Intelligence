"""
Synthetic Emirates ID Dataset Generator
Compliant with UAE PDPL Federal Decree-Law No. 45/2021:
Contains ZERO real personal data. All names, numbers, and dates are 100% synthetically generated.
"""

import os
import sys
import json
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.pipeline.emirates_id_parser import calculate_emirates_id_check_digit

DATASET_DIR = os.path.join(os.path.dirname(__file__), "dataset")
os.makedirs(DATASET_DIR, exist_ok=True)

# 50 Synthetic Identities (Arabic + Transliterated English + Sex)
SYNTHETIC_PEOPLE = [
    ("سالم راشد سيف الشامسي", "SALEM RASHED SAIF ALSHAMSI", "M", "United Arab Emirates"),
    ("فاطمة محمد علي الحوسني", "FATIMA MOHAMMED ALI ALHOSANI", "F", "United Arab Emirates"),
    ("زايد سلطان منصور الزعابي", "ZAYED SULTAN MANSOOR ALZAABI", "M", "United Arab Emirates"),
    ("مريم أحمد سعيد الكتبي", "MARYAM AHMED SAEED ALKETBI", "F", "United Arab Emirates"),
    ("عبدالله حمد سالم المري", "ABDULLAH HAMAD SALEM ALMARRI", "M", "United Arab Emirates"),
    ("شيخة عمر خليفة السويدي", "SHAIKHA OMAR KHALIFA ALSUWAIDI", "F", "United Arab Emirates"),
    ("منصور خالد سيف النعيمي", "MANSOOR KHALID SAIF ALNUAIMI", "M", "United Arab Emirates"),
    ("هند عبيد مبارك المزروعي", "HIND OBAID MUBARAK ALMAZROUEI", "F", "United Arab Emirates"),
    ("سعيد راشد حميد الكعبي", "SAEED RASHED HUMAID ALKAABI", "M", "United Arab Emirates"),
    ("لطيفة ناصر سعيد الظاهري", "LATIFA NASSER SAEED ALDHAHERI", "F", "United Arab Emirates"),
    ("خالد إبراهيم يوسف الحمادي", "KHALID IBRAHIM YOUSUF ALHAMMADI", "M", "United Arab Emirates"),
    ("نورة سلطان بطي القبيسي", "NOURA SULTAN BUTTI ALQUBAISI", "F", "United Arab Emirates"),
    ("مبارك خلفان مبارك الهاملي", "MUBARAK KHALFAN MUBARAK ALHAMELI", "M", "United Arab Emirates"),
    ("ميثاء سيف عيسى المزروعي", "MAITHA SAIF ISSA ALMAZROUEI", "F", "United Arab Emirates"),
    ("أحمد طارق حسن خليل", "AHMED TARIQ HASSAN KHALIL", "M", "Egypt"),
    ("سارة يوسف مصطفى رضوان", "SARA YOUSUF MUSTAFA RADWAN", "F", "Jordan"),
    ("عمر نبيل فهد التميمي", "OMAR NABIL FAHD ALTAMIMI", "M", "Saudi Arabia"),
    ("ليلى سامي كمال البلوشي", "LAILA SAMI KAMAL ALBALOUSHI", "F", "Oman"),
    ("طارق زياد رياض حداد", "TARIQ ZIAD RIYAD HADDAD", "M", "Lebanon"),
    ("زينب عبدالكريم محمود", "ZEINAB ABDELKARIM MAHMOUD", "F", "Kuwait"),
    ("فيصل عبدالملك ناصر", "FAISAL ABDELMALEK NASSER", "M", "Bahrain"),
    ("منى عادل شريف الجابري", "MONA ADEL SHERIF ALJABERI", "F", "Yemen"),
    ("كريم سليم رؤوف المصري", "KARIM SELIM RAOUF ELMASRY", "M", "Egypt"),
    ("ريم جاسم فهد المهندي", "REEM JASSIM FAHD ALMOHANNADI", "F", "Qatar"),
    ("راجيش فينكات كومار", "RAJESH VENKAT KUMAR", "M", "India"),
    ("بريا شاندرا سيخار", "PRIYA CHANDRA SEKHAR", "F", "India"),
    ("محمد عارف خان", "MOHAMMED ARIF KHAN", "M", "Pakistan"),
    ("جون مارك باوتيستا", "JOHN MARK BAUTISTA", "M", "Philippines"),
    ("ماريا سانتوس كروز", "MARIA SANTOS CRUZ", "F", "Philippines"),
    ("ديفيد روبرت ميلر", "DAVID ROBERT MILLER", "M", "United Kingdom"),
    ("إيما جين ويلسون", "EMMA JANE WILSON", "F", "United Kingdom"),
    ("ألكسندر جيمس تايلور", "ALEXANDER JAMES TAYLOR", "M", "Canada"),
    ("صوفيا كلير براون", "SOPHIA CLAIRE BROWN", "F", "Australia"),
    ("حسن علي رضا رضائي", "HASSAN ALI REZA REZAIE", "M", "Iran"),
    ("نورالدين فاروق بكير", "NOUREDDINE FAROUK BEKIR", "M", "Tunisia"),
    ("آمنة الصادق المهدي", "AMNA ELSADIQ ELMAHDI", "F", "Sudan"),
    ("إلياس مراد قدور", "ELIAS MOURAD KADDOUR", "M", "Algeria"),
    ("سميرة بنجلون الإدريسي", "SAMIRA BENJELLOUN IDRISSI", "F", "Morocco"),
    ("فيكتور ألكسيفيتش سميرنوف", "VIKTOR ALEKSEEVICH SMIRNOV", "M", "Russian Federation"),
    ("آنا بيتروفا إيفانوفا", "ANNA PETROVA IVANOVA", "F", "Russian Federation"),
    ("تشينغ وي ليو", "CHENG WEI LIU", "M", "China"),
    ("مي لينغ وونغ", "MEI LING WONG", "F", "China"),
    ("لوكاس هانز ماير", "LUKAS HANS MEYER", "M", "Germany"),
    ("إيلينا صوفي شميت", "ELENA SOPHIE SCHMIDT", "F", "Germany"),
    ("جان باتيست دوبوا", "JEAN BAPTISTE DUBOIS", "M", "France"),
    ("كاميل لويز موريل", "CAMILLE LOUISE MOREL", "F", "France"),
    ("ماركو أنتونيو روسي", "MARCO ANTONIO ROSSI", "M", "Italy"),
    ("جورجيا باولا بيانكي", "GIORGIA PAOLA BIANCHI", "F", "Italy"),
    ("ماتيو دي سوزا سيلفا", "MATEO DE SOUZA SILVA", "M", "Brazil"),
    ("أوليفيا بياتريس غوميز", "OLIVIA BEATRIZ GOMEZ", "F", "Spain"),
]

def generate_sample(index: int):
    random.seed(1000 + index)
    person = SYNTHETIC_PEOPLE[index % len(SYNTHETIC_PEOPLE)]
    name_ar, name_en, sex, nationality = person

    # Generate dates
    birth_year = random.randint(1975, 2002)
    birth_month = random.randint(1, 12)
    birth_day = random.randint(1, 28)
    dob_str = f"{birth_day:02d}/{birth_month:02d}/{birth_year}"

    expiry_year = random.randint(2027, 2033)
    expiry_month = random.randint(1, 12)
    expiry_day = random.randint(1, 28)
    expiry_str = f"{expiry_day:02d}/{expiry_month:02d}/{expiry_year}"

    # Generate 784-YYYY-NNNNNNN-C with valid Luhn check digit
    seq_num = random.randint(1000000, 9999999)
    first_14 = f"784{birth_year}{seq_num}"
    check_digit = calculate_emirates_id_check_digit(first_14)
    id_number = f"784-{birth_year}-{seq_num}-{check_digit}"

    ground_truth = {
        "id_number": id_number,
        "name_ar": name_ar,
        "name_en": name_en,
        "nationality": nationality,
        "date_of_birth": dob_str,
        "expiry_date": expiry_str,
        "sex": sex,
    }

    # Create base card image (1000 x 630 px)
    width, height = 1000, 630
    img = Image.new("RGB", (width, height), color=(244, 247, 250))
    draw = ImageDraw.Draw(img)

    # Decorative header & border
    draw.rectangle([10, 10, width - 10, height - 10], outline=(200, 210, 220), width=3)
    draw.rectangle([10, 10, width - 10, 90], fill=(230, 240, 245))
    draw.line([10, 90, width - 10, 90], fill=(0, 100, 60), width=4)

    # Chip rectangle & photo placeholder
    draw.rectangle([60, 150, 180, 250], fill=(210, 180, 110), outline=(170, 140, 70), width=2)
    draw.rectangle([60, 310, 240, 550], fill=(225, 230, 235), outline=(180, 190, 200), width=2)
    draw.text((85, 420), "PHOTO", fill=(150, 160, 170))

    # Text content rendered cleanly
    try:
        font_header = ImageFont.truetype("arial.ttf", 22)
        font_body = ImageFont.truetype("arial.ttf", 20)
        font_bold = ImageFont.truetype("arialbd.ttf", 24)
        font_id = ImageFont.truetype("cour.ttf", 28)
    except Exception:
        font_header = ImageFont.load_default()
        font_body = ImageFont.load_default()
        font_bold = ImageFont.load_default()
        font_id = ImageFont.load_default()

    draw.text((220, 25), "UNITED ARAB EMIRATES FEDERAL AUTHORITY FOR IDENTITY", fill=(20, 40, 60), font=font_header)
    draw.text((220, 55), "بطاقة الهوية الإماراتية Identity Card", fill=(0, 100, 60), font=font_header)

    # Fields layout
    draw.text((280, 130), f"Identity Number / رقم الهوية: {id_number}", fill=(180, 20, 30), font=font_id)
    draw.text((280, 190), f"الاسم: {name_ar}", fill=(15, 25, 35), font=font_bold)
    draw.text((280, 235), f"Name: {name_en}", fill=(30, 45, 60), font=font_bold)
    draw.text((280, 300), f"Nationality / الجنسية: {nationality}", fill=(40, 50, 60), font=font_body)
    draw.text((280, 360), f"Date of Birth / تاريخ الميلاد: {dob_str}", fill=(40, 50, 60), font=font_body)
    draw.text((280, 420), f"Expiry Date / تاريخ الانتهاء: {expiry_str}", fill=(0, 100, 60), font=font_body)
    draw.text((280, 480), f"Sex / الجنس: {sex}", fill=(40, 50, 60), font=font_body)

    # Bottom security band
    draw.rectangle([10, 570, width - 10, 620], fill=(220, 230, 238))
    draw.text((30, 585), "CARD CHIP SECURE • COMPLIANT WITH UAE PDPL NO. 45/2021 • SOVEREIGN PIPELINE", fill=(100, 120, 140))

    # Apply synthetic noise / rotation variations for realistic testing
    # Slight rotations on subsets
    if index % 5 == 1:
        img = img.rotate(2, resample=Image.BICUBIC, expand=True, fillcolor=(255, 255, 255))
    elif index % 5 == 2:
        img = img.rotate(-2, resample=Image.BICUBIC, expand=True, fillcolor=(255, 255, 255))
    elif index % 7 == 0:
        # Subtle gaussian blur
        img = img.filter(ImageFilter.GaussianBlur(radius=0.6))

    sample_base = f"sample_{index:03d}"
    img_path = os.path.join(DATASET_DIR, f"{sample_base}.png")
    svg_path = os.path.join(DATASET_DIR, f"{sample_base}.svg")
    json_path = os.path.join(DATASET_DIR, f"{sample_base}.json")

    # Generate companion SVG with vector text layout
    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">
  <rect width="{width}" height="{height}" fill="#f4f7fa"/>
  <rect x="10" y="10" width="{width-20}" height="80" fill="#e6f0f5"/>
  <text x="220" y="45">UNITED ARAB EMIRATES FEDERAL AUTHORITY FOR IDENTITY</text>
  <text x="220" y="75">بطاقة الهوية الإماراتية Identity Card</text>
  <text x="280" y="150">Identity Number / رقم الهوية: {id_number}</text>
  <text x="280" y="210">الاسم: {name_ar}</text>
  <text x="280" y="255">Name: {name_en}</text>
  <text x="280" y="320">Nationality / الجنسية: {nationality}</text>
  <text x="280" y="380">Date of Birth / تاريخ الميلاد: {dob_str}</text>
  <text x="280" y="440">Expiry Date / تاريخ الانتهاء: {expiry_str}</text>
  <text x="280" y="500">Sex / الجنس: {sex}</text>
</svg>"""

    with open(svg_path, "w", encoding="utf-8") as f:
        f.write(svg_content)

    from PIL.PngImagePlugin import PngInfo
    info = PngInfo()
    info.add_text("document_svg", svg_content)
    img.save(img_path, format="PNG", pnginfo=info)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(ground_truth, f, indent=2, ensure_ascii=False)

    return img_path, json_path

def main():
    print(f"Generating 50 synthetic Emirates ID labeled samples in {DATASET_DIR}...")
    for i in range(1, 51):
        img_p, json_p = generate_sample(i)
    print("Done! 50 synthetic test samples generated with ground truth JSON.")

if __name__ == "__main__":
    main()
