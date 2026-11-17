// Data classes that mirror what the backend (FastAPI) sends as JSON.
// No scoring happens in the app: the server computes everything.

enum Level { low, moderate, high }

extension LevelLabel on Level {
  String get label => switch (this) {
        Level.low => 'Low',
        Level.moderate => 'Moderate',
        Level.high => 'High',
      };
}

Level levelFromText(String s) => switch (s) {
      'Low' => Level.low,
      'Moderate' => Level.moderate,
      _ => Level.high,
    };

double? _num(dynamic v) => v == null ? null : (v as num).toDouble();

/// One row of the product list: name, category, score.
class ProductSummary {
  final int id;
  final String barcode;
  final String name;
  final String? brand;
  final String categoryCode;
  final String categoryName;
  final String vegStatus; // veg | non_veg | not_declared
  final bool verified;
  final String source; // seed | user | off (Open Food Facts)
  final int score;
  final String band;

  const ProductSummary({
    required this.id,
    required this.barcode,
    required this.name,
    required this.brand,
    required this.categoryCode,
    required this.categoryName,
    required this.vegStatus,
    required this.verified,
    required this.source,
    required this.score,
    required this.band,
  });

  bool get isVeg => vegStatus == 'veg';
  bool get vegUnknown => vegStatus == 'not_declared';

  factory ProductSummary.fromJson(Map<String, dynamic> j) => ProductSummary(
        id: j['id'],
        barcode: j['barcode'],
        name: j['name'],
        brand: j['brand'],
        categoryCode: j['category']['code'],
        categoryName: j['category']['name'],
        vegStatus: j['veg_status'],
        verified: j['verified'],
        source: j['source'] ?? 'seed',
        score: j['score'],
        band: j['band'],
      );
}

class IngredientRef {
  final int? id; // null = not in our reference list yet
  final String name;
  final String? insCode;
  const IngredientRef({required this.id, required this.name, required this.insCode});
}

/// Everything the product page needs.
class ProductDetail {
  final ProductSummary summary;
  final bool isBeverage;
  final double serveSize;
  final String serveUnit;
  final String basis; // "per 100 g" / "per 100 ml"
  final Map<String, double?> per100;
  final Map<String, double?> perServe;
  final Map<String, int?> rdaPercent;
  final Map<String, Level> labels; // added_sugar, sat_fat, sodium
  final List<String> highIn;
  final List<String> allergens;
  final List<IngredientRef> ingredients;
  final ScoreDetail score;
  final String disclaimer;

  const ProductDetail({
    required this.summary,
    required this.isBeverage,
    required this.serveSize,
    required this.serveUnit,
    required this.basis,
    required this.per100,
    required this.perServe,
    required this.rdaPercent,
    required this.labels,
    required this.highIn,
    required this.allergens,
    required this.ingredients,
    required this.score,
    required this.disclaimer,
  });

  factory ProductDetail.fromJson(Map<String, dynamic> j) {
    final n = j['nutrition'] as Map<String, dynamic>;
    Map<String, double?> nums(Map m) => {for (final e in m.entries) e.key as String: _num(e.value)};
    return ProductDetail(
      summary: ProductSummary.fromJson(j),
      isBeverage: j['format'] == 'beverage',
      serveSize: (j['serve_size'] as num).toDouble(),
      serveUnit: j['serve_unit'],
      basis: n['basis'],
      per100: nums(n['per_100']),
      perServe: nums(n['per_serve']),
      rdaPercent: {
        for (final e in (n['rda_percent'] as Map).entries) e.key as String: (e.value as num?)?.toInt()
      },
      labels: {
        for (final e in (j['labels'] as Map).entries) e.key as String: levelFromText(e.value as String)
      },
      highIn: List<String>.from(j['high_in']),
      allergens: List<String>.from(j['allergens']),
      ingredients: [
        for (final i in j['ingredients'])
          IngredientRef(id: i['id'], name: i['name'], insCode: i['ins_code'])
      ],
      score: ScoreDetail.fromJson(j['score_detail']),
      disclaimer: j['disclaimer'],
    );
  }
}

/// One line of the "How was this calculated?" screen.
class ScoreFactor {
  final String label;
  final double points;
  final String source;
  final String? note;
  const ScoreFactor(this.label, this.points, this.source, this.note);

  factory ScoreFactor.fromJson(Map<String, dynamic> j) =>
      ScoreFactor(j['factor'], (j['points'] as num).toDouble(), j['source'], j['note']);
}

class ScoreHalf {
  final double score;
  final int start;
  final List<ScoreFactor> factors;
  const ScoreHalf(this.score, this.start, this.factors);

  factory ScoreHalf.fromJson(Map<String, dynamic> j) => ScoreHalf(
        (j['score'] as num).toDouble(),
        j['start'],
        [for (final f in j['factors']) ScoreFactor.fromJson(f)],
      );
}

class ScoreDetail {
  final int score;
  final double scoreExact;
  final String band;
  final String version;
  final double blendW;
  final ScoreHalf overall;
  final ScoreHalf? category; // null when the category has no rules yet
  final bool categoryConfirmed;
  final String? note;

  const ScoreDetail({
    required this.score,
    required this.scoreExact,
    required this.band,
    required this.version,
    required this.blendW,
    required this.overall,
    required this.category,
    required this.categoryConfirmed,
    required this.note,
  });

  factory ScoreDetail.fromJson(Map<String, dynamic> j) => ScoreDetail(
        score: j['score'],
        scoreExact: (j['score_exact'] as num).toDouble(),
        band: j['band'],
        version: j['version'],
        blendW: (j['blend_w'] as num).toDouble(),
        overall: ScoreHalf.fromJson(j['overall']),
        category: j['category'] == null ? null : ScoreHalf.fromJson(j['category']),
        categoryConfirmed: j['category_confirmed'],
        note: j['note'],
      );
}

class IngredientInfo {
  final String name;
  final String? insCode;
  final String? functionalClass;
  final String whatItIs;
  final String whyUsed;
  final String source;
  const IngredientInfo(this.name, this.insCode, this.functionalClass, this.whatItIs, this.whyUsed, this.source);

  factory IngredientInfo.fromJson(Map<String, dynamic> j) => IngredientInfo(
        j['name'], j['ins_code'], j['functional_class'], j['what_it_is'], j['why_used'], j['source']);
}

class CompareRow {
  final String nutrient;
  final String unit;
  final double a;
  final double b;
  final String verdict; // less | more | similar  (A compared with B)
  final String? statement;
  const CompareRow(this.nutrient, this.unit, this.a, this.b, this.verdict, this.statement);

  factory CompareRow.fromJson(Map<String, dynamic> j) => CompareRow(j['nutrient'], j['unit'],
      (j['a'] as num).toDouble(), (j['b'] as num).toDouble(), j['verdict'], j['statement']);
}

class CompareResult {
  final ProductSummary a;
  final ProductSummary b;
  final bool sameCategory;
  final String? warning;
  final List<CompareRow> rows;
  final List<String> highInA;
  final List<String> highInB;
  const CompareResult(this.a, this.b, this.sameCategory, this.warning, this.rows, this.highInA, this.highInB);

  factory CompareResult.fromJson(Map<String, dynamic> j) => CompareResult(
        ProductSummary.fromJson(j['a']),
        ProductSummary.fromJson(j['b']),
        j['same_category'],
        j['warning'],
        [for (final r in j['rows']) CompareRow.fromJson(r)],
        List<String>.from(j['high_in']['a']),
        List<String>.from(j['high_in']['b']),
      );
}

class CategoryOption {
  final String code;
  final String name;
  const CategoryOption(this.code, this.name);
}
