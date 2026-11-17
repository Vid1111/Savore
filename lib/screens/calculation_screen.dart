import 'package:flutter/material.dart';

import '../data/api.dart';
import '../data/models.dart';
import '../widgets.dart';

/// "How was this calculated?": both halves of the score with sources (from the server).
class CalculationScreen extends StatelessWidget {
  final int productId;
  const CalculationScreen({super.key, required this.productId});

  Future<(ProductSummary, ScoreDetail)> _load() async {
    final detail = await Api.product(productId);
    return (detail.summary, detail.score);
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('How was this calculated?')),
        body: AsyncView<(ProductSummary, ScoreDetail)>(
          load: _load,
          builder: (context, data) => _Body(product: data.$1, score: data.$2),
        ),
      );
}

String _signed(double v) => v > 0 ? '+${v.toStringAsFixed(2)}' : v.toStringAsFixed(2);

class _Body extends StatelessWidget {
  final ProductSummary product;
  final ScoreDetail score;
  const _Body({required this.product, required this.score});

  Widget _half(BuildContext context, String title, ScoreHalf half, String? note) {
    final factors = half.factors;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: Text(title, style: Theme.of(context).textTheme.titleMedium)),
            Text('${half.score.toStringAsFixed(1)} / 100',
                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
          ]),
          const SizedBox(height: 8),
          LinearProgressIndicator(
            value: half.score / 100,
            minHeight: 8,
            borderRadius: BorderRadius.circular(4),
            color: bandColor(half.score >= 70 ? 'Better choice' : half.score >= 40 ? 'Moderate' : 'Limit'),
          ),
          ListTile(
            dense: true,
            contentPadding: EdgeInsets.zero,
            title: const Text('Starting points'),
            trailing: Text('${half.start}'),
          ),
          for (final f in factors)
            ListTile(
              dense: true,
              contentPadding: EdgeInsets.zero,
              leading: Icon(f.points < 0 ? Icons.remove_circle : Icons.add_circle,
                  color: f.points < 0 ? Colors.red : (f.points > 0 ? Colors.green : Colors.grey)),
              title: Text(f.label),
              subtitle: Text('${f.note != null ? '${f.note}\n' : ''}Source: ${f.source}'),
              isThreeLine: f.note != null,
              trailing: Text(_signed(f.points),
                  style: TextStyle(
                      fontWeight: FontWeight.bold,
                      color: f.points < 0 ? Colors.red : (f.points > 0 ? Colors.green : Colors.grey))),
            ),
          const Divider(),
          Text(note ?? 'Each half is limited to between 0 and 100.',
              style: const TextStyle(fontSize: 12, color: Colors.black54)),
        ]),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final overall = _half(context, 'Overall half (same for every food)', score.overall, null);
    final category = score.category == null
        ? Card(
            child: ListTile(
              leading: const Icon(Icons.info_outline),
              title: const Text('Category half not available'),
              subtitle: Text(score.note ?? 'Category rules are not available for this product yet.'),
            ),
          )
        : _half(context, 'Category half (compared with ${product.categoryName})', score.category!, null);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: PageBody(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Card(
            child: ListTile(
              leading: ScoreBadge(score: score.score, band: score.band),
              title: Text(product.name),
              subtitle: Text(
                  '${score.blendW} × Overall ${score.overall.score.toStringAsFixed(1)} + '
                  '${1 - score.blendW} × Category ${(score.category?.score ?? score.overall.score).toStringAsFixed(1)} '
                  '= ${score.scoreExact} → ${score.score} · ${score.band}\nScoring version ${score.version}'),
              isThreeLine: true,
            ),
          ),
          const SizedBox(height: 8),
          if (isWide(context))
            Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Expanded(child: overall),
              const SizedBox(width: 16),
              Expanded(child: category),
            ])
          else ...[
            overall,
            category,
          ],
          const SectionTitle('Bands'),
          const Text('0–39 Limit · 40–69 Moderate · 70–100 Better choice. '
              'The 50/50 blend is a team design choice, not an official FSSAI formula.'),
          const SectionTitle('Sources'),
          const Text(
            '• FSS (Labelling & Display) Regulations 2020: reference values for %RDA\n'
            '• FSS (Advertising & Claims) Regulations 2018: Schedule I “low” levels\n'
            '• WHO South-East Asia Nutrient Profile Model 2017: category thresholds\n'
            '• ICMR-NIN Dietary Guidelines for Indians 2024\n'
            '• Codex General Standard for Food Additives / INS list',
          ),
        ]),
      ),
    );
  }
}
