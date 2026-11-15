"""
Synthetic Emirates ID Dataset Generator
Compliant with UAE PDPL Federal Decree-Law No. 45/2021:
Contains ZERO real personal data. All names, numbers, and dates are 100% synthetically generated.
Generates pure raster images with NO embedded SVG chunks, zero XML, and zero metadata.
"""

import os
import sys
import io
import json
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.pipeline.emirates_id_parser import calculate_emirates_id_check_digit

DATASET_DIR = os.path.join(os.path.dirname(__file__), "dataset")
os.makedirs(DATASET_DIR, exist_ok=True)

# 100 Fictitious Synthetic Identities (Arabic + Transliterated English + Sex + Nationality)
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
    ("حمدان سعيد خليفة المنصوري", "HAMDAN SAEED KHALIFA ALMANSOORI", "M", "United Arab Emirates"),
    ("عفراء راشد حميد المهيري", "AFRA RASHED HUMAID ALMHEIRI", "F", "United Arab Emirates"),
    ("بطي سالم ناصر الفلاسي", "BUTTI SALEM NASSER ALFLASI", "M", "United Arab Emirates"),
    ("سلامة خالد سلطان المزروعي", "SALAMA KHALID SULTAN ALMAZROUEI", "F", "United Arab Emirates"),
    ("غانم محمد جمعة القبيسي", "GHANEM MOHAMMED JUMA ALQUBAISI", "M", "United Arab Emirates"),
    ("روضة علي سالم الشحي", "ROWDA ALI SALEM ALSHEHHI", "F", "United Arab Emirates"),
    ("سهيل عبدالله عبيد الكتبي", "SUHAIL ABDULLAH OBAID ALKETBI", "M", "United Arab Emirates"),
    ("علياء حمدان خليفة الكعبي", "ALYAA HAMDAN KHALIFA ALKAABI", "F", "United Arab Emirates"),
    ("مطر خلفان راشد النيادي", "MATAR KHALFAN RASHED ALNEYADI", "M", "United Arab Emirates"),
    ("حصة منصور سيف الهاجري", "HESSA MANSOOR SAIF ALHAJERI", "F", "United Arab Emirates"),
    ("عادل كريم محمود الخوري", "ADEL KARIM MAHMOUD ALKHOORI", "M", "United Arab Emirates"),
    ("شمسة ناصر إبراهيم المعمري", "SHAMSA NASSER IBRAHIM ALMAAMARI", "F", "United Arab Emirates"),
    ("عيسى جمعة مطر الدرمكي", "ISSA JUMA MATAR ALDARMAKI", "M", "United Arab Emirates"),
    ("موزة خميس سعيد الكندي", "MOUZA KHAMIS SAEED ALKINDI", "F", "United Arab Emirates"),
    ("حميد خليفة حمد الشامسي", "HUMAID KHALIFA HAMAD ALSHAMSI", "M", "United Arab Emirates"),
    ("أميرة حسن كمال عبدربه", "AMIRA HASSAN KAMAL ABDELRABBO", "F", "Egypt"),
    ("باسم فؤاد وجدي الباز", "BASSEM FOUAD WAGDY ELBAZ", "M", "Egypt"),
    ("رانية حسام الدين العطار", "RANIA HOSSAM ELDIN ALATTAR", "F", "Syrian Arab Republic"),
    ("جهاد غسان توفيق النجار", "JIHAD GHASSAN TAWFIQ ALNAJJAR", "M", "Jordan"),
    ("دانة طلال عبدالمحسن التميمي", "DANA TALAL ABDELMOHSEN ALTAMIMI", "F", "Saudi Arabia"),
    ("وليد خالد إبراهيم المطيري", "WALEED KHALID IBRAHIM ALMUTAIRI", "M", "Kuwait"),
    ("أريج بدر ناصر العجمي", "AREEJ BADER NASSER ALAJMI", "F", "Kuwait"),
    ("ماجد سليمان خلفان الحارثي", "MAJID SULAIMAN KHALFAN ALHARTHI", "M", "Oman"),
    ("بشرى خليفة سالم الرواس", "BOUSHRA KHALIFA SALEM ALRAWAS", "F", "Oman"),
    ("سنان عمار يحيى الجبوري", "SINAN AMMAR YAHYA ALJABOURI", "M", "Iraq"),
    ("مها كاظم حسن الشمري", "MAHA KADHIM HASSAN ALSHAMMARI", "F", "Iraq"),
    ("أرون كاليان سوبرامانيان", "ARUN KALYAN SUBRAMANIAN", "M", "India"),
    ("ديبا سوريش مينون", "DEEPA SURESH MENON", "F", "India"),
    ("فيكرام براكاش باتيل", "VIKRAM PRAKASH PATEL", "M", "India"),
    ("نيها سومان شارما", "NEHA SUMAN SHARMA", "F", "India"),
    ("طارق محمود إقبال شودري", "TARIQ MAHMOOD IQBAL CHAUDHRY", "M", "Pakistan"),
    ("عائشة جاويد مالك", "AYESHA JAVED MALIK", "F", "Pakistan"),
    ("كارلو مانويل رييس", "CARLO MANUEL REYES", "M", "Philippines"),
    ("جاسمين روز نافارو", "JASMINE ROSE NAVARRO", "F", "Philippines"),
    ("جيمس أنتوني كلارك", "JAMES ANTHONY CLARK", "M", "United Kingdom"),
    ("شارلوت إليزابيث ديفيز", "CHARLOTTE ELIZABETH DAVIES", "F", "United Kingdom"),
    ("ويليام باتريك أوبراين", "WILLIAM PATRICK OBRIEN", "M", "Ireland"),
    ("إيزابيلا غريس إيفانز", "ISABELLA GRACE EVANS", "F", "New Zealand"),
    ("هانز كريستيان فيشر", "HANS CHRISTIAN FISCHER", "M", "Germany"),
    ("كلارا ماري شولز", "KLARA MARIE SCHULZ", "F", "Germany"),
    ("سيباستيان لوك لوفيفر", "SEBASTIEN LUC LEFEVRE", "M", "France"),
    ("كلوي مانون برنارد", "CHLOE MANON BERNARD", "F", "France"),
    ("ليوناردو ماتيو دي لوكا", "LEONARDO MATTEO DE LUCA", "M", "Italy"),
    ("فالنتينا جوليا موريتي", "VALENTINA GIULIA MORETTI", "F", "Italy"),
    ("هوانغ شياو مينغ", "HUANG XIAO MING", "M", "China"),
    ("لين شياو يانغ", "LIN XIAO YANG", "F", "China"),
    ("كينجي هيروشي تاناكا", "KENJI HIROSHI TANAKA", "M", "Japan"),
    ("يومي ناوكو واتانابي", "YUMI NAOKO WATANABE", "F", "Japan"),
    ("كارلوس إدواردو سيلفا", "CARLOS EDUARDO SILVA", "M", "Brazil"),
    ("غابرييلا لويزا سانتوس", "GABRIELA LUISA SANTOS", "F", "Brazil"),
]

# 25 Synthetic UAE Companies for Trade Licenses
SYNTHETIC_COMPANIES = [
    ("AL HILAL LOGISTICS SERVICES L.L.C", "الهلال لخدمات الدعم اللوجستي ذ.م.م", "Department of Economy and Tourism Dubai"),
    ("EMIRATES APEX CONSULTING LLC", "قمة الإمارات للاستشارات ذ.م.م", "Abu Dhabi Department of Economic Development"),
    ("GULF HORIZON TECHNOLOGIES FZ-LLC", "تقنيات أفق الخليج ش.ذ.م.م", "Dubai Silicon Oasis Authority"),
    ("BARAKAH GENERAL TRADING L.L.C", "البركة للتجارة العامة ذ.م.م", "Sharjah Economic Development Department"),
    ("DUBAI PEARL REAL ESTATE LLC", "لؤلؤة دبي للعقارات ذ.م.م", "Department of Economy and Tourism Dubai"),
    ("AL MANSOOR LEGAL ADVOCACY", "المنصور للمحاماة والاستشارات القانونية", "Abu Dhabi Department of Economic Development"),
    ("CRESCENT HEALTHCARE SOLUTIONS LLC", "حلول الهلال للرعاية الصحية ذ.م.م", "Department of Economy and Tourism Dubai"),
    ("OASIS MARITIME SERVICES LLC", "خدمات الواحة البحرية ذ.م.م", "Ras Al Khaimah Economic Zone"),
    ("FALCON ENGINEERING CONSULTANCY", "فالكون للاستشارات الهندسية", "Department of Economy and Tourism Dubai"),
    ("ZAYED SOLAR ENERGY SYSTEMS LLC", "أنظمة زايد للطاقة الشمسية ذ.م.م", "Abu Dhabi Department of Economic Development"),
    ("AL BARSHA FOOD INDUSTRIES LLC", "البرشاء للصناعات الغذائية ذ.م.م", "Department of Economy and Tourism Dubai"),
    ("PALM JUMEIRAH HOSPITALITY GROUP", "مجموعة نخلة جميرا للضيافة", "Department of Economy and Tourism Dubai"),
    ("AL DHAFRA AGRICULTURAL CORP", "مؤسسة الظفرة الزراعية", "Abu Dhabi Department of Economic Development"),
    ("RAK CERAMICS DISTRIBUTION LLC", "توزيع رأس الخيمة للسيراميك ذ.م.م", "Ras Al Khaimah Economic Zone"),
    ("AL AIN WATER BOTTLING & SUPPLY", "العين لتعبئة وتوريد المياه", "Abu Dhabi Department of Economic Development"),
    ("INFINITY FINANCIAL TECHNOLOGIES LLC", "إنفينيتي للتكنولوجيا المالية ذ.م.م", "Dubai International Financial Centre"),
    ("ARABIAN GULF CONTRACTING CO LLC", "شركة الخليج العربي للمقاولات ذ.م.م", "Department of Economy and Tourism Dubai"),
    ("ETIHAD AVIATION SUPPORT SERVICES", "الاتحاد لخدمات دعم الطيران", "Abu Dhabi Department of Economic Development"),
    ("DEIRA TRADING & IMPORT EXPORT LLC", "ديرة للتجارة والاستيراد والتصدير ذ.م.م", "Department of Economy and Tourism Dubai"),
    ("AL MAJID MOTORS & SPARE PARTS LLC", "الماجد للسيارات وقطع الغيار ذ.م.م", "Sharjah Economic Development Department"),
    ("FUTURE SMART SOLUTIONS LLC", "حلول المستقبل الذكية ذ.م.م", "Department of Economy and Tourism Dubai"),
    ("GOLDEN DUNES TOURISM LLC", "الكثبان الذهبية للسياحة ذ.م.م", "Department of Economy and Tourism Dubai"),
    ("BLUE OCEAN LOGISTICS FZE", "بلو أوشن للخدمات اللوجستية ش.ح", "Jebel Ali Free Zone Authority"),
    ("AL WASL PHARMACEUTICAL DISTRIBUTORS", "الوصل لتوزيع الأدوية", "Department of Economy and Tourism Dubai"),
    ("DUBAI SILICON VENTURES LLC", "دبي سيليكون للاستثمار ذ.م.م", "Dubai Silicon Oasis Authority"),
]

# 25 Synthetic Suppliers for Commercial Invoices
SYNTHETIC_SUPPLIERS = [
    ("BARAKAH SUPPLIES & EQUIPMENT FZE", "100345678900003", 14500.00),
    ("AL KHALEEJ BUILDING MATERIALS LLC", "100456789000003", 82500.00),
    ("EMIRATES TECH HARDWARE SOLUTIONS", "100567890100003", 31200.00),
    ("GULF OFFICE AUTOMATION FZCO", "100678901200003", 9400.00),
    ("AL WAHDA CATERING & SERVICES LLC", "100789012300003", 18750.00),
    ("DUBAI INDUSTRIAL TOOLS CO LLC", "100890123400003", 45600.00),
    ("ARABIAN PAPER & PRINTING PRODUCTS", "100901234500003", 6300.00),
    ("MIDDLE EAST CHEMICAL TRADING LLC", "100012345600003", 112000.00),
    ("AL NOOR ELECTRICAL WHOLESALE LLC", "100123456700003", 27400.00),
    ("SOVEREIGN CLOUD INFRASTRUCTURE FZE", "100234567800003", 95000.00),
    ("AL SHAMAL FLEET MANAGEMENT LLC", "100345678900003", 53800.00),
    ("CRESCENT MEDICAL LAB SUPPLIES", "100456789000003", 39100.00),
    ("PEARL MARITIME SPARE PARTS LLC", "100567890100003", 67200.00),
    ("AL AIN PACKAGING FACTORY LLC", "100678901200003", 15900.00),
    ("DUBAI FIBER OPTIC SYSTEMS LLC", "100789012300003", 88400.00),
    ("GLOBAL SAFETY WEAR & UNIFORMS FZE", "100890123400003", 12600.00),
    ("AL ZAHRA SANITARY WARE TRADING", "100901234500003", 34500.00),
    ("ATLAS HEAVY MACHINERY RENTALS LLC", "100012345600003", 142000.00),
    ("HORIZON AIR CONDITIONING SPARES", "100123456700003", 22100.00),
    ("AL FALAH SECURITY SYSTEMS LLC", "100234567800003", 41800.00),
    ("PRIME STEEL & METALS TRADING FZE", "100345678900003", 198000.00),
    ("AL REEM DIGITAL MEDIA AGENCIES", "100456789000003", 17500.00),
    ("ELITE VEHICLE FLEET LEASING LLC", "100567890100003", 76300.00),
    ("OASIS COLD STORAGE LOGISTICS", "100678901200003", 61000.00),
    ("DUBAI SMART POWER SYSTEMS LLC", "100789012300003", 105000.00),
]

def load_font(font_name: str, size: int) -> ImageFont.ImageFont:
    """Tries loading a system font by name or falls back gracefully."""
    font_paths = [
        os.path.join(r"C:\Windows\Fonts", font_name),
        os.path.join(r"/usr/share/fonts/truetype", font_name),
        font_name,
    ]
    for p in font_paths:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()

def add_noise(image: Image.Image, factor: float = 0.02) -> Image.Image:
    """Adds realistic salt-and-pepper grain noise to the image."""
    noisy = image.copy()
    draw = ImageDraw.Draw(noisy)
    width, height = image.size
    num_dots = int(width * height * factor)
    for _ in range(num_dots):
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        val = random.randint(40, 215)
        draw.point((x, y), fill=(val, val, val))
    return noisy

def add_uneven_lighting(image: Image.Image) -> Image.Image:
    """Applies a subtle lighting gradient across the document (simulate shadows/glare)."""
    width, height = image.size
    gradient = Image.new("L", (width, height))
    draw_g = ImageDraw.Draw(gradient)
    for x in range(width):
        factor = int(255 - (x / width) * 60)
        draw_g.line([(x, 0), (x, height)], fill=factor)
    
    r, g, b = image.split()
    zero = Image.new("L", (width, height), 0)
    r = Image.composite(r, zero, gradient)
    g = Image.composite(g, zero, gradient)
    b = Image.composite(b, zero, gradient)
    return Image.merge("RGB", (r, g, b))

def add_jpeg_compression(image: Image.Image, quality: int) -> Image.Image:
    """Simulates real-world phone camera/upload JPEG compression artifacts."""
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=quality)
    buf.seek(0)
    return Image.open(buf).convert("RGB")

def add_low_resolution(image: Image.Image, scale: float) -> Image.Image:
    """Simulates low-resolution scanner or thumbnail downscaling."""
    w, h = image.size
    down = image.resize((int(w * scale), int(h * scale)), Image.BILINEAR)
    return down.resize((w, h), Image.BILINEAR)

def apply_degradations(img: Image.Image, index: int, degradations: list) -> Image.Image:
    """Applies realistic optical degradations strictly within +/- 8 deg rotation."""
    rot_angles = [-8.0, -6.0, -4.5, -3.0, -1.5, 1.5, 3.0, 4.5, 6.0, 8.0]
    rot = rot_angles[index % len(rot_angles)]
    img = img.rotate(rot, resample=Image.BICUBIC, expand=True, fillcolor=(255, 255, 255))
    degradations.append(f"rotation_{rot:.1f}deg")

    if index % 3 == 0:
        radius = round(random.uniform(0.7, 1.3), 2)
        img = img.filter(ImageFilter.GaussianBlur(radius=radius))
        degradations.append(f"gaussian_blur_{radius}px")

    if index % 4 == 0:
        img = add_noise(img, factor=0.015)
        degradations.append("noise_grain")

    if index % 5 == 0:
        img = add_uneven_lighting(img)
        degradations.append("uneven_lighting_shadow")

    if index % 6 == 0:
        img = add_low_resolution(img, scale=0.65)
        degradations.append("low_resolution_downscale")

    if index % 2 == 0:
        q = random.randint(45, 75)
        img = add_jpeg_compression(img, quality=q)
        degradations.append(f"jpeg_q{q}")

    return img

def generate_emirates_id_sample(index: int):
    random.seed(5000 + index)
    person = SYNTHETIC_PEOPLE[(index - 1) % len(SYNTHETIC_PEOPLE)]
    name_ar, name_en, sex, nationality = person

    birth_year = random.randint(1970, 2004)
    birth_month = random.randint(1, 12)
    birth_day = random.randint(1, 28)
    dob_str = f"{birth_day:02d}/{birth_month:02d}/{birth_year}"

    expiry_year = random.randint(2027, 2035)
    expiry_month = random.randint(1, 12)
    expiry_day = random.randint(1, 28)
    expiry_str = f"{expiry_day:02d}/{expiry_month:02d}/{expiry_year}"

    seq_num = random.randint(1000000, 9999999)
    first_14 = f"784{birth_year}{seq_num}"
    check_digit = calculate_emirates_id_check_digit(first_14)
    id_number = f"784-{birth_year}-{seq_num}-{check_digit}"

    is_clean = (index <= 30)
    subset = "clean" if is_clean else "degraded"
    degradations = []

    ground_truth = {
        "document_type": "emirates_id",
        "id_number": id_number,
        "name_ar": name_ar,
        "name_en": name_en,
        "nationality": nationality,
        "date_of_birth": dob_str,
        "expiry_date": expiry_str,
        "sex": sex,
        "subset": subset,
        "degradations": degradations,
    }

    width, height = 1000, 630
    img = Image.new("RGB", (width, height), color=(245, 247, 250))
    draw = ImageDraw.Draw(img)

    draw.rectangle([10, 10, width - 10, height - 10], outline=(200, 210, 220), width=3)
    draw.rectangle([10, 10, width - 10, 95], fill=(232, 242, 248))
    draw.line([10, 95, width - 10, 95], fill=(0, 110, 65), width=4)

    draw.rectangle([60, 160, 180, 260], fill=(215, 185, 115), outline=(175, 145, 75), width=2)
    draw.rectangle([60, 320, 240, 560], fill=(225, 230, 235), outline=(180, 190, 200), width=2)
    draw.text((85, 430), "PHOTO", fill=(150, 160, 170))

    font_header = load_font("arialbd.ttf", 22)
    font_body = load_font("arial.ttf", 20)
    font_bold = load_font("arialbd.ttf", 24)
    font_id = load_font("cour.ttf", 28)

    draw.text((220, 25), "UNITED ARAB EMIRATES FEDERAL AUTHORITY FOR IDENTITY", fill=(20, 40, 60), font=font_header)
    draw.text((220, 58), "بطاقة الهوية الإماراتية Identity Card", fill=(0, 100, 60), font=font_header)

    draw.text((280, 130), f"Identity Number / رقم الهوية: {id_number}", fill=(180, 20, 30), font=font_id)
    draw.text((280, 190), f"الاسم: {name_ar}", fill=(15, 25, 35), font=font_bold)
    draw.text((280, 235), f"Name: {name_en}", fill=(30, 45, 60), font=font_bold)
    draw.text((280, 300), f"Nationality / الجنسية: {nationality}", fill=(40, 50, 60), font=font_body)
    draw.text((280, 360), f"Date of Birth / تاريخ الميلاد: {dob_str}", fill=(40, 50, 60), font=font_body)
    draw.text((280, 420), f"Expiry Date / تاريخ الانتهاء: {expiry_str}", fill=(0, 100, 60), font=font_body)
    draw.text((280, 480), f"Sex / الجنس: {sex}", fill=(40, 50, 60), font=font_body)

    draw.rectangle([10, 575, width - 10, 620], fill=(225, 235, 240))
    draw.text((30, 590), "CARD CHIP SECURE • COMPLIANT WITH UAE PDPL NO. 45/2021 • SOVEREIGN PIPELINE", fill=(100, 120, 140))

    if not is_clean:
        img = apply_degradations(img, index, degradations)

    return _save_and_verify_sample(index, img, ground_truth)

def generate_trade_license_sample(index: int):
    random.seed(6000 + index)
    c_idx = index - 101
    comp_en, comp_ar, auth = SYNTHETIC_COMPANIES[c_idx % len(SYNTHETIC_COMPANIES)]

    lic_num = f"CN-{1000000 + (index * 38291) % 9000000}"
    exp_year = random.randint(2027, 2032)
    exp_month = random.randint(1, 12)
    exp_day = random.randint(1, 28)
    exp_str = f"{exp_day:02d}/{exp_month:02d}/{exp_year}"

    is_clean = (index <= 105)  # 5 clean, 20 degraded
    subset = "clean" if is_clean else "degraded"
    degradations = []

    ground_truth = {
        "document_type": "uae_trade_license",
        "license_number": lic_num,
        "company_name_en": comp_en,
        "company_name_ar": comp_ar,
        "issuing_authority": auth,
        "expiry_date": exp_str,
        "subset": subset,
        "degradations": degradations,
    }

    width, height = 1000, 850
    img = Image.new("RGB", (width, height), color=(252, 252, 250))
    draw = ImageDraw.Draw(img)

    # Outer decorative frame
    draw.rectangle([20, 20, width - 20, height - 20], outline=(180, 150, 90), width=4)
    draw.rectangle([28, 28, width - 28, height - 28], outline=(220, 200, 140), width=2)
    draw.rectangle([30, 30, width - 30, 130], fill=(245, 240, 225))

    font_title = load_font("arialbd.ttf", 26)
    font_sub = load_font("arialbd.ttf", 20)
    font_label = load_font("arialbd.ttf", 20)
    font_val = load_font("arial.ttf", 20)

    draw.text((260, 45), "UNITED ARAB EMIRATES • دولة الإمارات العربية المتحدة", fill=(120, 90, 40), font=font_sub)
    draw.text((240, 80), "COMMERCIAL LICENSE • رخصة تجارية", fill=(10, 80, 40), font=font_title)

    draw.line([30, 135, width - 30, 135], fill=(180, 150, 90), width=3)

    # Layout fields
    fields = [
        ("License Number / رقم الرخصة:", lic_num, 170),
        ("Company Name / اسم الشركة:", comp_en, 250),
        ("Trade Name / الاسم التجاري:", comp_ar, 330),
        ("Issuing Authority / سلطة الترخيص:", auth, 410),
        ("Expiry Date / تاريخ الانتهاء:", exp_str, 490),
    ]

    for lbl, val, y_pos in fields:
        draw.text((60, y_pos), lbl, fill=(50, 50, 60), font=font_label)
        draw.text((440, y_pos), val, fill=(10, 30, 70), font=font_val)
        draw.line([60, y_pos + 38, width - 60, y_pos + 38], fill=(230, 230, 230), width=1)

    # Security footer
    draw.rectangle([30, 780, width - 30, 820], fill=(240, 242, 245))
    draw.text((60, 792), f"OFFICIAL ELECTRONIC DOCUMENT • LIC#{lic_num} • UAE SOVEREIGN GOV", fill=(120, 130, 140))

    if not is_clean:
        img = apply_degradations(img, index, degradations)

    return _save_and_verify_sample(index, img, ground_truth)

def generate_commercial_invoice_sample(index: int):
    random.seed(7000 + index)
    s_idx = index - 126
    supp, trn, amt = SYNTHETIC_SUPPLIERS[s_idx % len(SYNTHETIC_SUPPLIERS)]

    inv_num = f"INV-2026-{(index * 7491) % 9000 + 1000}"
    vat_amt = round(amt * 0.05, 2)
    tot_amt = f"{amt:.2f}"
    vat_str = f"{vat_amt:.2f}"
    inv_date = f"{(index % 28) + 1:02d}/{(index % 12) + 1:02d}/2026"

    is_clean = (index <= 130)  # 5 clean, 20 degraded
    subset = "clean" if is_clean else "degraded"
    degradations = []

    ground_truth = {
        "document_type": "commercial_invoice",
        "invoice_number": inv_num,
        "trn": trn,
        "invoice_date": inv_date,
        "supplier_name": supp,
        "total_amount": tot_amt,
        "vat_amount": vat_str,
        "subset": subset,
        "degradations": degradations,
    }

    width, height = 1000, 900
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    font_inv = load_font("arialbd.ttf", 28)
    font_supp = load_font("arialbd.ttf", 22)
    font_lbl = load_font("arialbd.ttf", 20)
    font_val = load_font("arial.ttf", 20)

    # Top banner
    draw.rectangle([30, 30, width - 30, 110], fill=(25, 45, 80))
    draw.text((60, 50), "TAX INVOICE / فاتورة ضريبية", fill=(255, 255, 255), font=font_inv)

    draw.text((60, 130), supp, fill=(20, 30, 50), font=font_supp)
    draw.line([30, 175, width - 30, 175], fill=(200, 210, 220), width=2)

    fields = [
        ("Invoice Number / رقم الفاتورة:", inv_num, 200),
        ("TRN / رقم التسجيل الضريبي:", trn, 260),
        ("Invoice Date / تاريخ الفاتورة:", inv_date, 320),
        ("Supplier Name / اسم المورد:", supp, 380),
        ("Total Amount / المبلغ الإجمالي:", tot_amt, 440),
        ("VAT Amount / ضريبة القيمة المضافة:", vat_str, 500),
    ]

    for lbl, val, y_pos in fields:
        draw.text((60, y_pos), lbl, fill=(70, 80, 90), font=font_lbl)
        draw.text((450, y_pos), val, fill=(15, 25, 40), font=font_val)
        draw.line([60, y_pos + 38, width - 60, y_pos + 38], fill=(240, 240, 240), width=1)

    # Total summary box
    draw.rectangle([60, 600, width - 60, 720], fill=(245, 248, 252), outline=(180, 200, 225), width=2)
    draw.text((90, 620), f"NET TOTAL: AED {tot_amt}", fill=(15, 25, 40), font=font_lbl)
    draw.text((90, 665), f"VAT (5%): AED {vat_str}", fill=(100, 110, 120), font=font_val)

    if not is_clean:
        img = apply_degradations(img, index, degradations)

    return _save_and_verify_sample(index, img, ground_truth)

def _save_and_verify_sample(index: int, img: Image.Image, ground_truth: dict):
    sample_base = f"sample_{index:03d}"
    img_path = os.path.join(DATASET_DIR, f"{sample_base}.png")
    json_path = os.path.join(DATASET_DIR, f"{sample_base}.json")

    # SAVE PURE RASTER PNG - STRIP ALL METADATA (NO pnginfo, NO EXIF, NO SVG)
    img.save(img_path, format="PNG")

    # Verify no SVG or metadata in saved bytes
    with open(img_path, "rb") as f:
        saved_bytes = f.read()
    assert b"<svg" not in saved_bytes.lower(), f"Fatal: SVG content leaked into {img_path}"
    assert b"document_svg" not in saved_bytes, f"Fatal: document_svg chunk leaked into {img_path}"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(ground_truth, f, indent=2, ensure_ascii=False)

    return img_path, json_path

def main():
    print(f"Generating 150 synthetic UAE pure raster samples in {DATASET_DIR}...")
    for f in os.listdir(DATASET_DIR):
        if f.endswith(".svg"):
            try:
                os.remove(os.path.join(DATASET_DIR, f))
            except Exception:
                pass

    clean_count = 0
    degraded_count = 0

    # 1. 100 Emirates IDs (sample_001 to sample_100)
    for i in range(1, 101):
        img_p, json_p = generate_emirates_id_sample(i)
        if i <= 30:
            clean_count += 1
        else:
            degraded_count += 1

    # 2. 25 Trade Licenses (sample_101 to sample_125)
    for i in range(101, 126):
        img_p, json_p = generate_trade_license_sample(i)
        if i <= 105:
            clean_count += 1
        else:
            degraded_count += 1

    # 3. 25 Commercial Invoices (sample_126 to sample_150)
    for i in range(126, 151):
        img_p, json_p = generate_commercial_invoice_sample(i)
        if i <= 130:
            clean_count += 1
        else:
            degraded_count += 1

    total = clean_count + degraded_count
    print(f"Done! Generated {total} pure raster samples ({clean_count} clean, {degraded_count} degraded).")
    print("Breakdown: 100 Emirates IDs, 25 Trade Licenses, 25 Commercial Invoices.")
    print("All metadata stripped; ZERO SVG files; 100% synthetic PDPL-compliant data.")

if __name__ == "__main__":
    main()

