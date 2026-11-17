import 'package:flutter/material.dart';

import '../data/api.dart';
import '../data/models.dart';
import '../widgets.dart';
import 'calculation_screen.dart';
import 'compare_screen.dart';
import 'ingredient_sheet.dart';

/// (server key, label, unit) for each row of the nutrition table.
const _rows = [
  ('energy_kcal', 'Energy', 'kcal'),
  ('protein_g', 'Protein', 'g'),
  ('carbohydrate_g', 'Carbohydrate', 'g'),
  ('total_sugar_g', 'Total sugars', 'g'),
  ('added_sugar_g', 'Added sugar', 'g'),
  ('total_fat_g', 'Total fat', 'g'),
  ('sat_fat_g', 'Saturated fat', 'g'),
  ('trans_fat_g', 'Trans fat', 'g'),
  ('fibre_g', 'Dietary fibre', 'g'),
  ('sodium_mg', 'Sodium', 'mg'),
];

const _levelNames = {
  'added_sugar': 'Added sugar',
  'sat_fat': 'Saturated fat',
  'sodium': 'Sodium',
};

class ProductScreen extends StatelessWidget {
  final int productId;
  final ProductDetail? initial; // already loaded (e.g. right after a barcode lookup)
  const ProductScreen({super.key, required this.productId, this.initial});

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Product')),
        body: AsyncView<ProductDetail>(
          initial: initial,
          load: () => Api.product(productId),
          builder: (context, d) => _ProductBody(d),
        ),
      );
}

class _ProductBody extends StatelessWidget {
  final ProductDetail d;
  const _ProductBody(this.d);

  String _fmt(double? v) {
    if (v == null) return 'Not declared';
    return v == v.roundToDouble() ? v.toStringAsFixed(0) : v.toStringAsFixed(1);
  }

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    final p = d.summary;
    final color = bandColor(d.score.band);

    // --- Header ---
    final header = Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Container(
        width: 72,
        height: 72,
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12)),
        child: const Icon(Icons.inventory_2_outlined, size: 36),
      ),
      const SizedBox(width: 16),
      Expanded(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            VegMark(isVeg: p.isVeg, unknown: p.vegUnknown),
            const SizedBox(width: 8),
            Text(p.vegUnknown ? 'Veg / non-veg not declared' : (p.isVeg ? 'Vegetarian' : 'Non-vegetarian'),
                style: t.labelMedium),
          ]),
          const SizedBox(height: 4),
          Text(p.name, style: t.titleLarge),
          Text('${p.brand ?? 'Unknown brand'} · ${p.barcode}', style: t.bodySmall),
        ]),
      ),
    ]);

    // --- Unverified notice ---
    final unverified = p.verified
        ? const SizedBox.shrink()
        : Container(
            width: double.infinity,
            margin: const EdgeInsets.only(top: 12),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
                color: const Color(0xFFE3F2FD), borderRadius: BorderRadius.circular(10)),
            child: Text(p.source == 'off'
                ? 'Unverified: imported from Open Food Facts and not yet checked by our team. '
                    'Compare it with the pack.'
                : 'Unverified: added by a user, waiting for a reviewer to check it.'),
          );

    // --- Allergen strip ---
    final allergens = Container(
      width: double.infinity,
      margin: const EdgeInsets.only(top: 16),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: d.allergens.isEmpty ? const Color(0xFFE8F5E9) : const Color(0xFFFFF4E5),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Row(children: [
        Icon(d.allergens.isEmpty ? Icons.check_circle_outline : Icons.warning_amber, size: 20),
        const SizedBox(width: 8),
        Expanded(
          child: Text(d.allergens.isEmpty
              ? 'No common allergens declared'
              : 'Contains: ${d.allergens.join(', ')}'),
        ),
      ]),
    );

    // --- Score card ---
    final scoreCard = Card(
      color: color.withValues(alpha: 0.08),
      margin: const EdgeInsets.only(top: 16),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            ScoreBadge(score: d.score.score, band: d.score.band, size: 72),
            const SizedBox(width: 16),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(d.score.band,
                    style: t.headlineSmall?.copyWith(color: color, fontWeight: FontWeight.bold)),
                Text('${d.score.score} / 100 · ${p.categoryName}'),
              ]),
            ),
          ]),
          if (!d.score.categoryConfirmed)
            const Padding(
              padding: EdgeInsets.only(top: 8),
              child: Text('Category not confirmed: this score uses the Overall half only.',
                  style: TextStyle(fontSize: 13)),
            ),
          const SizedBox(height: 8),
          Wrap(spacing: 8, children: [
            TextButton.icon(
              icon: const Icon(Icons.calculate_outlined),
              label: const Text('How was this calculated?'),
              onPressed: () => Navigator.push(context,
                  MaterialPageRoute(builder: (_) => CalculationScreen(productId: p.id))),
            ),
            TextButton.icon(
              icon: const Icon(Icons.compare_arrows),
              label: const Text('Compare'),
              onPressed: () => Navigator.push(
                  context, MaterialPageRoute(builder: (_) => CompareScreen(first: p))),
            ),
          ]),
        ]),
      ),
    );

    // --- High in badges + level chips ---
    final badges = Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      if (d.highIn.isNotEmpty) ...[
        const SectionTitle('Watch out (provisional: FSSAI thresholds not yet notified)'),
        Wrap(spacing: 8, runSpacing: 8, children: [
          for (final h in d.highIn)
            Chip(
              avatar: const Icon(Icons.priority_high, color: Colors.white, size: 16),
              label: Text('High in ${h.toLowerCase()}', style: const TextStyle(color: Colors.white)),
              backgroundColor: const Color(0xFFDC2626),
              side: BorderSide.none,
            ),
        ]),
      ],
      SectionTitle('Nutrient levels (${d.basis})'),
      Wrap(spacing: 8, runSpacing: 8, children: [
        for (final e in d.labels.entries)
          LevelChip(label: _levelNames[e.key] ?? e.key, level: e.value),
      ]),
    ]);

    // --- Nutrition table ---
    final table = Card(
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: DataTable(
          columnSpacing: 20,
          headingTextStyle: t.labelLarge,
          columns: [
            const DataColumn(label: Text('Nutrient')),
            DataColumn(label: Text(d.basis[0].toUpperCase() + d.basis.substring(1)), numeric: true),
            DataColumn(
                label: Text('Per serve (${_fmt(d.serveSize)} ${d.serveUnit})'), numeric: true),
            const DataColumn(label: Text('%RDA*'), numeric: true),
          ],
          rows: [
            for (final (key, label, unit) in _rows)
              DataRow(cells: [
                DataCell(Text(label)),
                DataCell(Text(d.per100[key] == null ? 'Not declared' : '${_fmt(d.per100[key])} $unit')),
                DataCell(Text(d.perServe[key] == null ? '–' : '${_fmt(d.perServe[key])} $unit')),
                DataCell(Text(d.rdaPercent[key] == null ? '–' : '${d.rdaPercent[key]}%')),
              ]),
          ],
        ),
      ),
    );

    // --- Ingredients ---
    final ingredients = Wrap(spacing: 8, runSpacing: 8, children: [
      for (final ing in d.ingredients)
        ing.id != null
            ? ActionChip(
                label: Text(ing.insCode == null ? ing.name : '${ing.name} (${ing.insCode})'),
                onPressed: () => showIngredientSheet(context, ing),
              )
            : Chip(label: Text(ing.name)), // not in our reference list: nothing to explain yet
    ]);

    final disclaimer = Padding(
      padding: const EdgeInsets.only(top: 24),
      child: Text(
        '*%RDA uses FSSAI reference values (and ICMR-NIN for protein, carbohydrate and fibre). '
        '${d.disclaimer}'
        '${p.source == 'off' ? '\n\nProduct data: Open Food Facts contributors, licensed under the ODbL.' : ''}',
        style: const TextStyle(fontSize: 12, color: Colors.black54),
      ),
    );

    final left = Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [header, unverified, allergens, scoreCard, badges]);
    final right = Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      const SectionTitle('Nutrition information'),
      table,
      const SectionTitle('Ingredients (tap for details)'),
      ingredients,
      disclaimer,
    ]);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: PageBody(
        child: isWide(context)
            ? Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Expanded(child: left),
                const SizedBox(width: 24),
                Expanded(child: right),
              ])
            : Column(children: [left, right]),
      ),
    );
  }
}
