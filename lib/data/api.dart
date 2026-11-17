import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import 'models.dart';

/// Where the backend lives: the deployed server (Render + Supabase) by default.
/// To use a server on your own PC instead, without editing code:
///   adb reverse tcp:8000 tcp:8000
///   flutter run --dart-define=API_URL=http://127.0.0.1:8000
const apiUrl = String.fromEnvironment('API_URL', defaultValue: 'https://savore-api.onrender.com');

/// Something went wrong talking to the server. [message] is safe to show to the user.
class ApiException implements Exception {
  final String message;
  final List<String> errors; // rule failures from the server (submission form)
  const ApiException(this.message, [this.errors = const []]);
  @override
  String toString() => message;
}

class Api {
  static final _client = http.Client();

  static Future<dynamic> _send(Future<http.Response> Function() call, {Set<int> ok = const {200}}) async {
    final http.Response r;
    try {
      // Long enough for a free hosting server that has to wake up first (about 30-50 s).
      r = await call().timeout(const Duration(seconds: 60));
    } on TimeoutException {
      throw const ApiException('The server took too long to answer. Please try again.');
    } catch (_) {
      throw const ApiException(
          'Can’t reach the Savoré server. Check that it is running and your phone can reach it.');
    }
    if (ok.contains(r.statusCode)) return r.body.isEmpty ? null : jsonDecode(utf8.decode(r.bodyBytes));
    if (r.statusCode == 404) throw const ApiException('Not found', ['404']);
    String message = 'Something went wrong (${r.statusCode}).';
    List<String> errors = const [];
    try {
      final detail = jsonDecode(utf8.decode(r.bodyBytes))['detail'];
      if (detail is String) message = detail;
      if (detail is Map && detail['errors'] is List) errors = List<String>.from(detail['errors']);
      if (detail is List) {
        // FastAPI field errors, e.g. "nutrition.energy_kcal: Input should be a valid number"
        errors = [for (final d in detail) '${(d['loc'] as List).skip(1).join('.')}: ${d['msg']}'];
      }
    } catch (_) {}
    throw ApiException(message, errors);
  }

  static Uri _u(String path, [Map<String, String>? query]) =>
      Uri.parse(apiUrl).replace(path: path, queryParameters: query);

  /// Product by barcode, or null if we don't have it yet.
  static Future<ProductDetail?> byBarcode(String code) async {
    try {
      final j = await _send(() => _client.get(_u('/products/by-barcode/${code.trim()}')));
      return ProductDetail.fromJson(j);
    } on ApiException catch (e) {
      if (e.errors.contains('404')) return null;
      rethrow;
    }
  }

  static Future<ProductDetail> product(int id) async =>
      ProductDetail.fromJson(await _send(() => _client.get(_u('/products/$id'))));

  static Future<ScoreDetail> score(int id) async {
    final j = await _send(() => _client.get(_u('/products/$id/score')));
    return ScoreDetail.fromJson(j);
  }

  static Future<List<ProductSummary>> search(String q) async {
    final j = await _send(() => _client.get(_u('/products/search', {'q': q})));
    return [for (final p in j) ProductSummary.fromJson(p)];
  }

  static Future<IngredientInfo> ingredient(int id) async =>
      IngredientInfo.fromJson(await _send(() => _client.get(_u('/ingredients/$id'))));

  static Future<CompareResult> compare(int a, int b) async {
    final j = await _send(() => _client.post(_u('/compare'),
        headers: {'Content-Type': 'application/json'}, body: jsonEncode({'a': a, 'b': b})));
    return CompareResult.fromJson(j);
  }

  static Future<List<CategoryOption>> categories() async {
    final j = await _send(() => _client.get(_u('/categories')));
    return [for (final c in j) CategoryOption(c['code'], c['name'])];
  }

  /// Sends a new product for review. Throws [ApiException] with the rule errors if it is refused.
  static Future<void> submit(Map<String, dynamic> body) async {
    await _send(
        () => _client.post(_u('/submissions'),
            headers: {'Content-Type': 'application/json'}, body: jsonEncode(body)),
        ok: {201});
  }
}

/// Recently opened products (kept in memory only: the app collects no personal data).
final recentScans = ValueNotifier<List<ProductSummary>>([]);

void addRecent(ProductSummary p) {
  recentScans.value = [p, ...recentScans.value.where((x) => x.id != p.id)].take(10).toList();
}
