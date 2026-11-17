"""Starting data: categories, scoring rules, ingredients and 8 sample products.

The products are fictional (same ones as the app's sample data).
Scoring rules come from PRD v3.0 Appendix A. The PRD warns that the WHO SEARO
numbers must be checked against the original 2017 WHO document: see README.
"""

FSSAI = "FSSAI Food Products Standards & Food Additives Regulations, 2011"
CODEX = "Codex GSFA / INS list (CAC/GL 36-1989)"
ICMR = "ICMR-NIN Dietary Guidelines for Indians, 2024"
WHO_SUGAR = "WHO Guideline: Sugars intake for adults and children, 2015"

# ---------------------------------------------------------------- categories
# (code, name, SEARO code, format)
CATEGORIES = [
    ("C1", "Biscuits, cookies, cakes, rusk", "2", "solid"),
    ("C2", "Bread & bakery", "3", "solid"),
    ("C3", "Breakfast cereals, oats, muesli", "4", "solid"),
    ("C4", "Savoury snacks (namkeen, chips, bhujia, puffs)", "5A", "solid"),
    ("C5", "Processed nuts & seeds", "5B", "solid"),
    ("C6", "Chocolates, confectionery, mithai, jams", "1", "solid"),
    ("C7", "Instant noodles, pasta, vermicelli", "12", "solid"),
    ("C8", "Ready meals, RTE/RTC, soups, frozen snacks", "10", "solid"),
    ("C9", "Curd, yoghurt, dahi, shrikhand", "8", "solid"),
    ("C10", "Paneer, cheese & analogues", "9", "solid"),
    ("C11", "Ice cream & frozen desserts", "7", "solid"),
    ("C12", "Carbonated, flavoured & energy drinks", "6C", "beverage"),
    ("C13", "Fruit juices & nectars", "6A", "beverage"),
    ("C14", "Dairy drinks (flavoured milk, lassi, chaas, shakes)", "6B", "beverage"),
    ("C15", "Tea/coffee premixes & ready-to-drink", "6D", "beverage"),
    ("C16", "Cereal/malt/nut drinks & beverage powders", "6E", "beverage"),
    ("C17", "Sauces, ketchup, chutneys, dips, spreads", "18", "solid"),
    ("C18", "Pickles & processed fruit/veg", "16", "solid"),
    ("C19", "Fats, oils, ghee, butter, margarine", "11", "solid"),
    ("C20", "Processed meat & fish", "14A/14B", "solid"),
    ("G-S", "General solid (fallback)", None, "solid"),
    ("G-B", "General beverage (fallback)", None, "beverage"),
]


# ------------------------------------------------------- category scoring rules
# (factor, kind, T, C, H, weight). Penalty weights add up to 80 per category.
def P(factor, t, c, w):
    return (factor, "penalty", t, c, None, w)


def B(factor, h, v):
    return (factor, "bonus", None, None, h, v)


def NSS(w):
    return ("nss", "binary", None, None, None, w)


def WG(v):
    return ("wg", "binary", None, None, None, v)


# Only the P1 categories (Appendix A). Other categories fall back to the Overall score.
PARAMETERS = {
    "C1": [P("fat", 8, 28, 20), P("total_sugar", 6, 35, 25), P("sodium", 250, 700, 15),
           P("energy", 230, 520, 10), NSS(10), B("fibre", 6, 10), B("protein", 10, 5), WG(5)],
    "C3": [P("fat", 12, 25, 15), P("total_sugar", 9, 35, 35), P("sodium", 350, 800, 20),
           NSS(10), B("fibre", 6, 10), B("protein", 10, 5), WG(5)],
    "C4": [P("fat", 8, 38, 25), P("added_sugar", 0.5, 10, 10), P("sodium", 50, 1200, 25),
           P("energy", 230, 580, 10), NSS(10), B("protein", 10, 10), B("fibre", 6, 10)],
    "C5": [P("added_sugar", 0.5, 20, 30), P("sodium", 50, 800, 40), NSS(10),
           B("protein", 10, 10), B("fibre", 6, 10)],
    "C6": [P("fat", 8, 35, 20), P("total_sugar", 6, 60, 35), P("energy", 230, 560, 15),
           NSS(10), B("protein", 10, 10), B("fibre", 6, 10)],
    "C7": [P("fat", 3, 20, 25), P("sodium", 250, 1400, 45), NSS(10),
           B("fibre", 6, 10), B("protein", 10, 5), WG(5)],
    "C9": [P("fat", 7, 15, 15), P("total_sugar", 6, 20, 35), P("sodium", 100, 400, 10),
           P("energy", 230, 350, 10), NSS(10), B("protein", 10, 20)],
    "C12": [P("total_sugar", 2, 13, 50), P("sodium", 300, 600, 10), NSS(20)],
    "C13": [P("total_sugar", 6, 14, 40), P("added_sugar", 0.5, 10, 30), NSS(10), B("fibre", 3, 10)],
}

# ----------------------------------------------------------------- allergens
ALLERGENS = ["Gluten", "Milk", "Soy", "Peanut", "Egg", "Fish", "Tree nuts", "Crustaceans", "Sulphite"]


# --------------------------------------------------------------- ingredients
def ing(name, what, why, source, ins=None, cls=None, wg=False, nss=False):
    return dict(name=name, what=what, why=why, source=source, ins=ins, cls=cls, wg=wg, nss=nss)


INGREDIENTS = {
    "maida": ing("Refined wheat flour (maida)", "Wheat flour with the bran and germ removed.",
                 "Gives a soft, smooth texture and long shelf life.", ICMR),
    "wholewheat": ing("Whole wheat flour (atta)", "Flour made from the whole wheat grain.",
                      "Main base; keeps fibre and minerals of the grain.", ICMR, wg=True),
    "oats": ing("Rolled oats", "Whole oat grains that are steamed and flattened.",
                "The product itself; a whole grain rich in fibre.", ICMR, wg=True),
    "palmoil": ing("Palm oil", "Vegetable oil from the fruit of the oil palm, high in saturated fat.",
                   "Cheap, stable for frying, and solid at room temperature.", ICMR),
    "sugar": ing("Sugar", "Refined cane sugar (sucrose).", "Sweetness, browning and bulk.", WHO_SUGAR),
    "invert": ing("Invert sugar syrup", "Sugar split into glucose and fructose in liquid form.",
                  "Keeps baked goods moist and adds sweetness.", WHO_SUGAR),
    "salt": ing("Iodised salt", "Common salt with added iodine.", "Flavour; iodine prevents deficiency.", FSSAI),
    "spices": ing("Spices & condiments", "Mix of ground spices such as chilli, turmeric, coriander.",
                  "Flavour and colour.", FSSAI),
    "cocoa": ing("Cocoa solids", "Powder made from roasted cocoa beans.", "Chocolate flavour and colour.", FSSAI),
    "milk": ing("Milk solids", "Dried milk with the water removed.", "Creaminess and flavour. Allergen: milk.", FSSAI),
    "peanuts": ing("Peanuts", "Roasted groundnuts.", "The product itself. Allergen: peanut.", FSSAI),
    "chicken": ing("Dehydrated chicken", "Dried chicken pieces or powder.",
                   "Flavour and protein. Makes the product non-vegetarian.", FSSAI),
    "water": ing("Carbonated water", "Water with dissolved carbon dioxide.",
                 "Base of the drink; gives fizz.", FSSAI),
    "ins621": ing("Monosodium glutamate", "Sodium salt of glutamic acid, a flavour enhancer.",
                  "Adds a savoury (umami) taste. Adds to sodium intake.", CODEX, "INS 621", "Flavour enhancer"),
    "ins627": ing("Disodium guanylate", "Flavour enhancer usually used with MSG.",
                  "Boosts savoury taste.", CODEX, "INS 627", "Flavour enhancer"),
    "ins631": ing("Disodium inosinate", "Flavour enhancer usually used with MSG.",
                  "Boosts savoury taste.", CODEX, "INS 631", "Flavour enhancer"),
    "ins501": ing("Potassium carbonate", "An acidity regulator.",
                  "Gives noodles their springy texture.", CODEX, "INS 501(i)", "Acidity regulator"),
    "ins500": ing("Sodium bicarbonate", "Baking soda, a raising agent.",
                  "Makes biscuits light and crisp.", CODEX, "INS 500(ii)", "Raising agent"),
    "ins330": ing("Citric acid", "An acid found naturally in citrus fruit.",
                  "Sour taste and acts as a preservative.", CODEX, "INS 330", "Acidity regulator"),
    "ins322": ing("Lecithin", "An emulsifier, usually from soy.",
                  "Helps fat and water mix smoothly. Allergen: soy.", CODEX, "INS 322", "Emulsifier"),
    "ins471": ing("Mono- and diglycerides of fatty acids", "An emulsifier made from fats.",
                  "Improves texture and shelf life.", CODEX, "INS 471", "Emulsifier"),
    "ins476": ing("Polyglycerol polyricinoleate", "An emulsifier made from castor oil.",
                  "Lets chocolate flow thinly, reducing cocoa butter needed.", CODEX, "INS 476", "Emulsifier"),
    "ins150d": ing("Sulphite ammonia caramel", "A brown colouring made by heating sugar with ammonia/sulphite.",
                   "Gives a darker colour.", CODEX, "INS 150d", "Colour"),
    "ins211": ing("Sodium benzoate", "A preservative.",
                  "Stops mould and yeast growing in acidic drinks.", CODEX, "INS 211", "Preservative"),
    "ins102": ing("Tartrazine", "A synthetic yellow food colour.",
                  "Bright colour. Must carry a warning in some countries.", FSSAI, "INS 102", "Colour"),
}


# ------------------------------------------------------------------ products
def prod(barcode, name, brand, cat, veg, serve, n, ings, allergens, unit="g"):
    keys = ["energy_kcal", "protein_g", "carbohydrate_g", "total_sugar_g", "added_sugar_g",
            "total_fat_g", "sat_fat_g", "trans_fat_g", "fibre_g", "sodium_mg"]
    return dict(barcode=barcode, name=name, brand=brand, cat=cat, veg=veg, serve=serve,
                unit=unit, n=dict(zip(keys, n)), ings=ings, allergens=allergens)


#             energy protein carbs sugar added fat  sat trans fibre sodium
PRODUCTS = [
    prod("8901000000011", "Masala Instant Noodles", "QuickBowl", "C7", "veg", 70,
         (450, 9, 62, 2.5, None, 18, 8.5, 0, 2, 1200),
         ["maida", "palmoil", "salt", "spices", "ins621", "ins627", "ins631", "ins501", "ins150d"], ["Gluten"]),
    prod("8901000000028", "Whole Wheat Atta Noodles", "GoodGrain", "C7", "veg", 70,
         (380, 11, 65, 1.5, None, 8, 3.5, 0, 7, 700),
         ["wholewheat", "palmoil", "salt", "spices", "ins501", "ins330"], ["Gluten"]),
    prod("8901000000073", "Chicken Masala Cup Noodles", "QuickBowl", "C7", "non_veg", 60,
         (440, 10, 60, 3, None, 17, 8, 0, 2, 1350),
         ["maida", "palmoil", "salt", "chicken", "spices", "ins621", "ins471"], ["Gluten"]),
    prod("8901000000035", "Chocolate Cream Biscuits", "Crunchy Co", "C1", "veg", 25,
         (490, 5, 70, 35, 30, 21, 10, 0, 1.5, 250),
         ["maida", "sugar", "palmoil", "cocoa", "invert", "milk", "ins322", "ins500", "salt"],
         ["Gluten", "Milk", "Soy"]),
    prod("8901000000042", "Rolled Oats", "GoodGrain", "C3", "veg", 40,
         (380, 13, 66, 1, 0, 7, 1.2, 0, 10, 5), ["oats"], ["Gluten"]),
    prod("8901000000059", "Orange Fizz Drink", "Sparkle", "C12", "veg", 250,
         (48, 0, 12, 12, 12, 0, 0, 0, 0, 15),
         ["water", "sugar", "ins330", "ins211", "ins102"], [], unit="ml"),
    prod("8901000000066", "Salted Peanuts", "Crunchy Co", "C5", "veg", 30,
         (590, 25, 16, 4, 0, 48, 7, 0, 8, 450), ["peanuts", "salt"], ["Peanut"]),
    prod("8901000000080", "Milk Chocolate Bar", "Cocoa Lane", "C6", "veg", 20,
         (540, 7, 58, 52, 50, 31, 18, 0, 2, 90),
         ["sugar", "milk", "cocoa", "ins322", "ins476"], ["Milk", "Soy"]),
]
