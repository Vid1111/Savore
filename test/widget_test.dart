import 'package:flutter_test/flutter_test.dart';
import 'package:savore/data/models.dart';
import 'package:savore/main.dart';

// Shape of the JSON the backend sends for GET /products/by-barcode/{code} (shortened).
const _sample = {
  'id': 1,
  'barcode': '8901000000011',
  'name': 'Masala Instant Noodles',
  'brand': 'QuickBowl',
  'category': {'code': 'C7', 'name': 'Instant noodles, pasta, vermicelli'},
  'veg_status': 'veg',
  'verified': true,
  'score': 50,
  'band': 'Moderate',
  'format': 'solid',
  'serve_size': 70.0,
  'serve_unit': 'g',
  'nutrition': {
    'basis': 'per 100 g',
    'per_100': {'energy_kcal': 450.0, 'added_sugar_g': null, 'sodium_mg': 1200.0},
    'per_serve': {'energy_kcal': 315.0, 'added_sugar_g': null, 'sodium_mg': 840.0},
    'rda_percent': {'energy_kcal': 16, 'added_sugar_g': null, 'sodium_mg': 42},
  },
  'labels': {'added_sugar': 'Low', 'sat_fat': 'High', 'sodium': 'High'},
  'high_in': ['Saturated fat', 'Sodium'],
  'allergens': ['Gluten'],
  'ingredients': [
    {'position': 1, 'id': 1, 'name': 'Refined wheat flour (maida)', 'ins_code': null},
    {'position': 2, 'id': null, 'name': 'Mystery powder', 'ins_code': null},
  ],
  'score_detail': {
    'version': 'v1',
    'blend_w': 0.5,
    'score': 50,
    'score_exact': 50.0,
    'band': 'Moderate',
    'overall': {
      'score': 53.47,
      'start': 80,
      'factors': [
        {'factor': 'Sodium', 'points': -20.0, 'source': 'FSSAI', 'note': null},
      ],
    },
    'category': null,
    'category_confirmed': false,
    'note': 'Category rules not available.',
  },
  'disclaimer': 'Informational only.',
};

void main() {
  testWidgets('Home screen shows scan and search', (tester) async {
    await tester.pumpWidget(const SavoreApp());
    expect(find.text('Scan barcode'), findsOneWidget);
    expect(find.text('Type barcode'), findsOneWidget);
  });

  test('App reads the server product JSON correctly', () {
    final d = ProductDetail.fromJson(_sample);
    expect(d.summary.name, 'Masala Instant Noodles');
    expect(d.summary.isVeg, isTrue);
    expect(d.score.band, 'Moderate');
    expect(d.score.category, isNull); // category rules not available: handled, not a crash
    expect(d.per100['added_sugar_g'], isNull); // "not declared" stays null
    expect(d.rdaPercent['sodium_mg'], 42);
    expect(d.labels['sodium'], Level.high);
    expect(d.ingredients[1].id, isNull); // not in the reference list: shown, not tappable
  });
}
