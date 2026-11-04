import re
import difflib

# Keyboard layout maps (QWERTY <-> ЙЦУКЕН)
EN_LAYOUT = "`qwertyuiop[]asdfghjkl;'zxcvbnm,./~QWERTYUIOP{}ASDFGHJKL:\"ZXCVBNM<>?"
RU_LAYOUT = "ёйцукенгшщзхъфывапролджэячсмитьбю.ЁЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭЯЧСМИТЬБЮ,"

EN_TO_RU = str.maketrans(EN_LAYOUT, RU_LAYOUT)
RU_TO_EN = str.maketrans(RU_LAYOUT, EN_LAYOUT)

# Common Russian dictionary for supplements, tech, and electronics -> Finnish/International terms
RU_TO_SEARCH_TERMS = {
    # Sports Nutrition & Health
    "креатин": "kreatiini",
    "креатина": "kreatiini",
    "креатином": "kreatiini",
    "креатинчик": "kreatiini",
    "криатин": "kreatiini",
    "креатен": "kreatiini",
    "криотин": "kreatiini",
    "креатин моногидрат": "kreatiinimonohydraatti",
    "моногидрат": "monohydraatti",
    "протеин": "proteiinijauhe",
    "протеина": "proteiinijauhe",
    "протен": "proteiinijauhe",
    "прот": "proteiinijauhe",
    "протыч": "proteiinijauhe",
    "протеинчик": "proteiinijauhe",
    "пратеин": "proteiinijauhe",
    "протиин": "proteiinijauhe",
    "протеины": "proteiinijauhe",
    "протеинов": "proteiinijauhe",
    "протеиновый": "proteiinijauhe",
    "протеновый": "proteiinijauhe",
    "протеиновые": "proteiinijauhe",
    "протеновые": "proteiinijauhe",
    "протеиновый порошок": "proteiinijauhe",
    "протеновый порошок": "proteiinijauhe",
    "протеиновый коктейль": "proteiinijauhe",
    "соевый протеин": "soijaproteiini",
    "соевый порошок": "soijaproteiini",
    "соевый": "soijaproteiini",
    "соя": "soija",
    "растительный протеин": "kasviproteiini",
    "растительный": "kasviproteiini",
    "веганский протеин": "kasviproteiini",
    "веганский": "vegaaninen",
    "гороховый протеин": "herneproteiini",
    "сывороточный протеин": "heraproteiini whey",
    "сывороточный": "heraproteiini whey",
    "сыворотка": "heraproteiini whey",
    "изолят": "isolate",
    "гидролизат": "hydrolysate",
    "казеин": "casein",
    "гейнер": "gainer",
    "гейнера": "gainer",
    "масс гейнер": "mass gainer",
    "коллаген": "kollageeni",
    "коллагена": "kollageeni",
    "бцаа": "bcaa",
    "всаа": "bcaa",
    "предтрен": "pre workout",
    "предтренировочный": "pre workout",
    "предтреник": "pre workout",
    "витамин": "vitamiini",
    "витамины": "vitamiinit",
    "мультивитамины": "monivitamiini",
    "омега": "omega",
    "омега 3": "omega 3",
    "омега-3": "omega 3",
    "рыбий жир": "kalaöljy omega 3",
    "магний": "magnesium",
    "цинк": "sinkki",
    "железо": "rauta",
    "кальций": "kalsium",
    "глютамин": "glutamiini",
    "глутамин": "glutamiini",
    "аминокислоты": "aminohapot",
    "блины": "pannukakkujauhe",
    "панкейки": "pannukakkujauhe",
    "протеиновые блины": "proteiinipannukakkujauhe",
    "протеиновый батончик": "proteiinipatukka",
    "протеиновые батончики": "proteiinipatukka",
    "батончик": "proteiinipatukka",
    "батончики": "proteiinipatukka",
    "жиросжигатель": "rasvanpolttaja",
    "мелатонин": "melatoniini",
    "электролиты": "elektrolyytit",
    "креапур": "creapure",
    "шоколад": "suklaa",
    "ваниль": "vanilja",
    "клубника": "mansikka",
    "банан": "banaani",
    "порошок": "jauhe",

    # Electronics & Consumer Tech
    "айфон": "iPhone",
    "айфончик": "iPhone",
    "айфона": "iPhone",
    "айпада": "iPad",
    "айпад": "iPad",
    "макбук": "MacBook",
    "эпл": "Apple",
    "эппл": "Apple",
    "самсунг": "Samsung",
    "сяоми": "Xiaomi",
    "ксяоми": "Xiaomi",
    "наушники": "kuulokkeet",
    "уши": "kuulokkeet",
    "беспроводные": "langattomat",
    "колонка": "kaiutin",
    "колонки": "kaiuttimet",
    "мышь": "hiiri",
    "мышка": "hiiri",
    "клавиатура": "näppäimistö",
    "клава": "näppäimistö",
    "монитор": "näyttö",
    "ноутбук": "kannettava",
    "ноут": "kannettava",
    "компьютер": "tietokone",
    "комп": "tietokone",
    "компик": "tietokone",
    "пк": "tietokone",
    "видеокарта": "näytönohjain",
    "видюха": "näytönohjain",
    "видюхи": "näytönohjain",
    "процессор": "prosessori",
    "проц": "prosessori",
    "процик": "prosessori",
    "материнка": "emolevy",
    "материнская плата": "emolevy",
    "оперативка": "ram muisti",
    "блок питания": "virtalähde",
    "корпус": "kotelo",
    "кулер": "tuuletin",
    "пылесос": "imuri",
    "робот пылесос": "robotti-imuri",
    "вайфай": "wifi",
    "вай-фай": "wifi",
    "блютуз": "bluetooth",
    "блютус": "bluetooth",
    "часы": "kello",
    "смарт часы": "älykello",
    "телевизор": "televisio",
    "телек": "televisio",
    "сони": "Sony",
    "плойка": "PlayStation",
    "плейстейшн": "PlayStation",
    "сонька": "PlayStation",
    "иксбокс": "Xbox",
    "планшет": "tabletti",
    "чехол": "kotelo",
    "стекло": "panssarilasi",
    "зарядка": "laturi",
    "кабель": "kaapeli",
    "павербанк": "varavirtalähde powerbank",

    # Coffee Machines & Appliances
    "кофемашина": "kahvikone",
    "кофемашины": "kahvikone",
    "кофемашин": "kahvikone",
    "кофемашину": "kahvikone",
    "кофеварка": "kahvinkeitin",
    "кофеварки": "kahvinkeitin",
    "кофеварку": "kahvinkeitin",
    "кофеварок": "kahvinkeitin",
    "капсульная кофемашина": "kapselikahvikone",
    "капсульная кофеварка": "kapselikahvikone",
    "рожковая кофеварка": "espressokeitin",
    "рожковая кофемашина": "espressokeitin",
    "рожковая": "espressokeitin",
    "гейзерная кофеварка": "mutteripannu",
    "гейзерная": "mutteripannu",
    "капельная кофеварка": "kahvinkeitin",
    "автоматическая кофемашина": "kahvikone automaattinen",
    "эспрессо": "espressokeitin",
    "эспрессо машина": "espressokeitin",
    "эспрессо кофемашина": "espressokeitin",
    "капучинатор": "maidonvaahdotin",
    "вспениватель молока": "maidonvaahdotin",
    "кофемолка": "kahvimylly",
    "кофе": "kahvi",
    "кофе в зернах": "kahvipavut",
    "зерновой кофе": "kahvipavut",
    "мокамастер": "Moccamaster",
    "моккамастер": "Moccamaster",
    "делонги": "DeLonghi",
    "делонжи": "DeLonghi",
    "филипс": "Philips",
    "мелитта": "Melitta",
    "крупс": "Krups",
    "юра": "Jura",
    "сейдж": "Sage",
    "вилфа": "Wilfa",
    "неспрессо": "Nespresso",
    "дольче густо": "Dolce Gusto"
}

# Known English / Latin product and brand keywords that might be accidentally typed in Cyrillic
KNOWN_LATIN_KEYWORDS = {
    "creatine", "kreatiini", "protein", "proteiini", "whey", "bcaa", "mass", "gainer",
    "kahvikone", "kahvinkeitin", "espressokeitin", "moccamaster", "delonghi", "melitta",
    "krups", "nespresso", "wilfa", "jura", "philips",
    "iphone", "ipad", "macbook", "apple", "samsung", "sony", "playstation", "xbox",
    "logitech", "dyson", "nintendo", "asus", "lenovo", "xiaomi", "airpods", "puls",
    "optimum", "mutant", "scitec", "star", "nutrition", "superlight", "razer", "steelseries",
    "hyperx", "corsair", "kingston", "sandisk", "garmin", "polar", "suunto", "bose", "jbl",
    "sennheiser", "marshall", "canon", "nikon", "gopro", "philips", "braun", "oral-b", "bosch"
}

TRANSLIT_TABLE = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya"
}

def transliterate_ru_to_en(text: str) -> str:
    """Simple phonetic transliteration."""
    res = []
    for ch in text.lower():
        res.append(TRANSLIT_TABLE.get(ch, ch))
    return "".join(res)

def is_cyrillic(text: str) -> bool:
    return bool(re.search(r"[\u0400-\u04FF]", text))

def is_latin(text: str) -> bool:
    return bool(re.search(r"[a-zA-Z]", text))

# Known acronyms & suffixes that must NOT be converted by layout fixer
KNOWN_ACRONYMS = {
    "rtx", "gtx", "rx", "cpu", "gpu", "ram", "ssd", "hdd", "usb", "ps5", "ps4",
    "oled", "qled", "led", "ips", "hdr", "bcaa", "pwo", "pro", "max", "mini",
    "plus", "ultra", "se", "fe", "ti", "xt", "xl", "xs", "xr", "wh", "wf",
    "g", "kg", "ml", "l", "w", "v", "hz", "dpi", "bt", "wi-fi", "wifi", "lte", "5g", "4g"
}

def fix_token_layout(token: str) -> tuple[str, bool]:
    """
    Check if a single token was typed in the wrong keyboard layout.
    Returns (fixed_token, was_changed).
    """
    clean = re.sub(r"[^\w]", "", token.lower())
    if not clean or clean in KNOWN_ACRONYMS:
        return token, False
        
    # 1. If token is Latin (e.g. 'rhtfnby', 'ghjntby', 'fqajy')
    if is_latin(token) and not is_cyrillic(token):
        cand_ru = token.translate(EN_TO_RU)
        cand_clean = re.sub(r"[^\w]", "", cand_ru.lower())
        # Check if cand_clean matches or starts with any Russian dictionary term
        for k in RU_TO_SEARCH_TERMS:
            if cand_clean == k or (len(cand_clean) >= 4 and k.startswith(cand_clean)):
                return cand_ru, True
                
        # If it has 0 vowels in English or very strange consonant clusters (e.g. 'rhtfnby', 'fqajy', 'ytnhj')
        vowels_en = sum(1 for c in clean if c in "aeiouy")
        if vowels_en == 0 and len(clean) >= 3:
            vowels_ru = sum(1 for c in cand_clean if c in "аеёиоуыэюя")
            if vowels_ru > 0:
                return cand_ru, True
                
    # 2. If token is Cyrillic (e.g. 'скуфешту' -> 'creatine', 'дщпшеуср' -> 'logitech', 'шзрщту' -> 'iphone')
    if is_cyrillic(token):
        cand_en = token.translate(RU_TO_EN)
        cand_clean = re.sub(r"[^\w]", "", cand_en.lower())
        for w in KNOWN_LATIN_KEYWORDS:
            if cand_clean == w or (len(cand_clean) >= 4 and (w.startswith(cand_clean) or cand_clean.startswith(w))):
                return cand_en, True
                
        # Also check if token is NOT a valid Russian word, but in English it has vowels
        if clean not in RU_TO_SEARCH_TERMS:
            vowels_ru = sum(1 for c in clean if c in "аеёиоуыэюя")
            vowels_en = sum(1 for c in cand_clean if c in "aeiouy")
            # If Latin version has reasonable vowels and Russian has very few or odd structure
            if vowels_en >= 2 and len(clean) >= 4:
                # E.g. 'скуфешту' -> 'creatine'
                if cand_clean in ("creatine", "creatin", "protein", "iphone", "ipad", "sony", "logitech", "samsung", "whey"):
                    return cand_en, True
                    
    return token, False

def parse_user_query(raw_query: str) -> tuple[str, str | None, list[str]]:
    """
    Transforms any user query into an optimized search query for Finnish stores.
    Handles:
    - Wrong layout English -> Russian (e.g. 'rhtfnby' -> 'kreatiini')
    - Wrong layout Russian -> English (e.g. 'скуфешту' -> 'creatine')
    - Cyrillic Russian -> Finnish/English (e.g. 'креатин' -> 'kreatiini', 'протеин' -> 'proteiini')
    - Mixed queries (e.g. 'креатин оптимум нутришн 500г' -> 'kreatiini Optimum Nutrition 500g')
    
    Returns:
    - primary_search_query: string to search
    - user_hint: message explanation if converted (e.g. "распознано как «креатин» ➡️ kreatiini")
    - fallback_queries: alternative query variations to try
    """
    q = raw_query.strip()
    
    # 1. Step: Token-level layout fix
    tokens = q.split()
    fixed_tokens = []
    any_layout_fixed = False
    
    for t in tokens:
        fixed_t, changed = fix_token_layout(t)
        if changed:
            any_layout_fixed = True
        fixed_tokens.append(fixed_t)
        
    normalized_input = " ".join(fixed_tokens)
    
    # Also handle weight units like '500г' -> '500g', '1кг' -> '1kg'
    normalized_input = re.sub(r"(\d+)\s*кг\b", r"\1kg", normalized_input, flags=re.IGNORECASE)
    normalized_input = re.sub(r"(\d+)\s*г\b", r"\1g", normalized_input, flags=re.IGNORECASE)
    
    # 2. Step: Translate Russian tokens to Finnish / English search terms
    tokens2 = normalized_input.split()
    translated_tokens = []
    any_translated = False
    
    two_word_keys = [k for k in RU_TO_SEARCH_TERMS if " " in k]
    single_word_keys = [k for k in RU_TO_SEARCH_TERMS if " " not in k]
    
    i = 0
    while i < len(tokens2):
        t_curr = tokens2[i].lower()
        clean_one = re.sub(r"[^\w]", "", t_curr)
        
        # 2A. Two-word check (exact + fuzzy)
        if i + 1 < len(tokens2):
            two_words = f"{tokens2[i]} {tokens2[i+1]}".lower()
            clean_two = re.sub(r"[^\w\s]", "", two_words)
            if clean_two in RU_TO_SEARCH_TERMS:
                translated_tokens.append(RU_TO_SEARCH_TERMS[clean_two])
                any_translated = True
                i += 2
                continue
                
            m2 = difflib.get_close_matches(clean_two, two_word_keys, n=1, cutoff=0.76)
            if m2:
                translated_tokens.append(RU_TO_SEARCH_TERMS[m2[0]])
                any_translated = True
                i += 2
                continue
                
        # 2B. Domain root rules (supplements & tech)
        # Soy / Plant protein
        if re.match(r"^(?:соев|соя)", clean_one):
            any_translated = True
            if i + 1 < len(tokens2) and any(tokens2[i+1].lower().startswith(x) for x in ["прот", "прат", "порошок"]):
                translated_tokens.append("soijaproteiini")
                i += 2
                continue
            else:
                translated_tokens.append("soijaproteiini")
                i += 1
                continue

        # Whey (сывороточный) protein
        if re.match(r"^(?:сыворот)", clean_one):
            any_translated = True
            if i + 1 < len(tokens2) and any(tokens2[i+1].lower().startswith(x) for x in ["прот", "прат"]):
                translated_tokens.append("heraproteiini whey")
                i += 2
                continue
            else:
                translated_tokens.append("heraproteiini")
                i += 1
                continue

        # General Protein roots (прот*, прат*)
        if re.match(r"^(?:прот|прат)", clean_one):
            any_translated = True
            if i + 1 < len(tokens2) and any(tokens2[i+1].lower().startswith(x) for x in ["порошок", "коктейл", "шейк", "дрин"]):
                translated_tokens.append("proteiinijauhe")
                i += 2
                continue
            elif i + 1 < len(tokens2) and any(tokens2[i+1].lower().startswith(x) for x in ["батончик", "батон"]):
                translated_tokens.append("proteiinipatukka")
                i += 2
                continue
            elif i + 1 < len(tokens2) and any(tokens2[i+1].lower().startswith(x) for x in ["блин", "панкейк"]):
                translated_tokens.append("proteiinipannukakkujauhe")
                i += 2
                continue
            else:
                translated_tokens.append("proteiinijauhe")
                i += 1
                continue

        # Coffee machines & makers
        if re.match(r"^кофемаш", clean_one):
            any_translated = True
            translated_tokens.append("kahvikone")
            i += 1
            continue

        if re.match(r"^кофевар", clean_one):
            any_translated = True
            translated_tokens.append("kahvinkeitin")
            i += 1
            continue

        if re.match(r"^эспресс", clean_one):
            any_translated = True
            if i + 1 < len(tokens2) and any(tokens2[i+1].lower().startswith(x) for x in ["маш", "вар"]):
                translated_tokens.append("espressokeitin")
                i += 2
                continue
            else:
                translated_tokens.append("espressokeitin")
                i += 1
                continue

        if re.match(r"^капучинатор", clean_one):
            any_translated = True
            translated_tokens.append("maidonvaahdotin")
            i += 1
            continue

        if re.match(r"^кофемолк", clean_one):
            any_translated = True
            translated_tokens.append("kahvimylly")
            i += 1
            continue
                
        # Creatine roots (креат*, криат*)
        if re.match(r"^(?:креат|криат)", clean_one):
            any_translated = True
            if i + 1 < len(tokens2) and any(tokens2[i+1].lower().startswith(x) for x in ["моно", "monohydrate"]):
                translated_tokens.append("kreatiinimonohydraatti")
                i += 2
                continue
            else:
                translated_tokens.append("kreatiini")
                i += 1
                continue
                
        # 2C. Single-word check (exact + fuzzy)
        if clean_one in RU_TO_SEARCH_TERMS:
            translated_tokens.append(RU_TO_SEARCH_TERMS[clean_one])
            any_translated = True
            i += 1
            continue
            
        m1 = difflib.get_close_matches(clean_one, single_word_keys, n=1, cutoff=0.76)
        if m1:
            translated_tokens.append(RU_TO_SEARCH_TERMS[m1[0]])
            any_translated = True
            i += 1
            continue
            
        # 2D. Cyrillic word fallback
        if is_cyrillic(tokens2[i]):
            translit = transliterate_ru_to_en(tokens2[i])
            if any(translit.startswith(p) for p in ("kreatin", "creatin")):
                translit = "kreatiini"
            elif any(translit.startswith(p) for p in ("protein", "proten", "proteyn")):
                translit = "proteiinijauhe"
            elif any(translit.startswith(p) for p in ("soya", "soija")):
                translit = "soijaproteiini"
            elif any(translit.startswith(p) for p in ("kofemash", "coffeemash")):
                translit = "kahvikone"
            elif any(translit.startswith(p) for p in ("kofevar", "coffeevar")):
                translit = "kahvinkeitin"
            translated_tokens.append(translit)
            any_translated = True
        else:
            translated_tokens.append(tokens2[i])
        i += 1
        
    clean_query = " ".join(translated_tokens)
    # Remove redundant 'jauhe' if proteiinijauhe, soijaproteiini, whey or kreatiini already present
    if any(k in clean_query.lower() for k in ["proteiinijauhe", "soijaproteiini", "whey", "kreatiini"]):
        clean_query = re.sub(r"\bjauhe\b", "", clean_query, flags=re.IGNORECASE)
    primary_query = re.sub(r"\s+", " ", clean_query).strip()
    
    user_hint = None
    if any_layout_fixed:
        user_hint = f"распознана раскладка: <i>{q}</i> ➡️ <b>{primary_query}</b>"
    elif any_translated and primary_query.lower() != q.lower():
        user_hint = f"поиск: <b>{primary_query}</b> (с «<i>{q}</i>»)"
        
    fallback_queries = []
    if primary_query.lower() != q.lower():
        fallback_queries.append(q)
    if normalized_input.lower() != primary_query.lower() and normalized_input.lower() != q.lower():
        fallback_queries.append(normalized_input)
        
    return primary_query, user_hint, fallback_queries
