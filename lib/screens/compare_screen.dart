import 'package:flutter/material.dart';

import '../data/api.dart';
import '../data/models.dart';
import '../widgets.dart';

class CompareScreen extends StatefulWidget {
  final ProductSummary? first;
  const CompareScreen({super.key, this.first});

  @override
  State<CompareScreen> createState() => _CompareScreenState();
}

class _CompareScreenState extends State<CompareScreen> {
  late ProductSummary? _a = widget.first;
  ProductSummary? _b;

  /// A tappable field that opens the search sheet (a dropdown can't hold thousands of products).
  Widget _picker(String label, ProductSummary? value, ValueChanged<ProductSummary> onPicked) => InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: () async {
          final p = await showModalBottomSheet<ProductSummary>(
            context: context,
            isScrollControlled: true,
            useSafeArea: true,
            showDragHandle: true,
            constraints: const BoxConstraints(maxWidth: 640),
            builder: (_) => const _PickerSheet(),
          );
          if (p != null) onPicked(p);
        },
        child: InputDecorator(
          decoration: InputDecoration(labelText: label, suffixIcon: const Icon(Icons.search)),
          child: Text(value == null ? 'Tap to search and choose' : '${value.name} (${value.brand ?? 'no brand'})',
              maxLines: 1, overflow: TextOverflow.ellipsis),
        ),
      );

  @override
  Widget build(BuildContext context) {
    final pa = _picker('Product 1', _a, (p) => setState(() => _a = p));
    final pb = _picker('Product 2', _b, (p) => setState(() => _b = p));
    return Scaffold(
      appBar: AppBar(title: const Text('Compare')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: PageBody(
          maxWidth: 900,
          child: Column(children: [
            if (isWide(context))
              Row(children: [
                Expanded(child: pa),
                const SizedBox(width: 16),
                Expanded(child: pb),
              ])
            else ...[pa, const SizedBox(height: 12), pb],
            const SizedBox(height: 16),
            if (_a == null || _b == null)
              const Card(
                child: Padding(
                  padding: EdgeInsets.all(24),
                  child: Text('Pick two products to compare them side by side.'),
                ),
              )
            else if (_a!.id == _b!.id)
              const Card(
                child: Padding(
                  padding: EdgeInsets.all(24),
                  child: Text('Pick two different products.'),
                ),
              )
            else
              // The key reloads the comparison whenever a different pair is chosen.
              AsyncView<CompareResult>(
                key: ValueKey('${_a!.id}-${_b!.id}'),
                load: () => Api.compare(_a!.id, _b!.id),
                builder: (context, r) => _ResultTable(r),
              ),
          ]),
        ),
      ),
    );
  }
}

/// Bottom sheet: search the whole catalogue and tap a product.
class _PickerSheet extends StatefulWidget {
  const _PickerSheet();

  @override
  State<_PickerSheet> createState() => _PickerSheetState();
}

class _PickerSheetState extends State<_PickerSheet> {
  String _query = '';

  @override
  Widget build(BuildContext context) => SizedBox(
        height: MediaQuery.sizeOf(context).height * 0.85,
        child: Column(children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
            child: TextField(
              autofocus: true,
              textInputAction: TextInputAction.search,
              decoration: const InputDecoration(
                  hintText: 'Search by name, brand or barcode', prefixIcon: Icon(Icons.search)),
              onSubmitted: (q) => setState(() => _query = q),
            ),
          ),
          Expanded(
            child: AsyncView<List<ProductSummary>>(
              key: ValueKey(_query),
              load: () => Api.search(_query),
              builder: (context, list) => list.isEmpty
                  ? const Center(child: Text('No products found'))
                  : ListView.builder(
                      itemCount: list.length,
                      itemBuilder: (_, i) => ListTile(
                        leading: ScoreBadge(score: list[i].score, band: list[i].band, size: 40),
                        title: Text(list[i].name, maxLines: 1, overflow: TextOverflow.ellipsis),
                        subtitle: Text('${list[i].brand ?? 'no brand'} · ${list[i].categoryName}',
                            maxLines: 1, overflow: TextOverflow.ellipsis),
                        onTap: () => Navigator.pop(context, list[i]),
                      ),
                    ),
            ),
          ),
        ]),
      );
}

const _lowerIsBetter = {'Energy', 'Added sugar', 'Saturated fat', 'Total fat', 'Sodium'};

class _ResultTable extends StatelessWidget {
  final CompareResult r;
  const _ResultTable(this.r);

  String _fmt(double v) => v == v.roundToDouble() ? v.toStringAsFixed(0) : v.toStringAsFixed(1);

  @override
  Widget build(BuildContext context) {
    TableRow row(String label, Widget x, Widget y, {bool header = false}) => TableRow(
          decoration:
              header ? BoxDecoration(color: Theme.of(context).colorScheme.primaryContainer) : null,
          children: [
            for (final w in [Text(label, style: const TextStyle(fontWeight: FontWeight.w600)), x, y])
              Padding(padding: const EdgeInsets.all(10), child: w),
          ],
        );

    // Highlight the better side only where the claims guard allowed a comparison.
    (bool, bool) better(CompareRow c) {
      if (c.verdict == 'similar') return (false, false);
      final aHasLess = c.verdict == 'less';
      final aWins = _lowerIsBetter.contains(c.nutrient) ? aHasLess : !aHasLess;
      return (aWins, !aWins);
    }

    Widget val(CompareRow c, bool a, bool win) => Text('${_fmt(a ? c.a : c.b)} ${c.unit}',
        style: TextStyle(
            fontWeight: win ? FontWeight.bold : null,
            color: win ? const Color(0xFF1B8E3E) : null));

    final statements = [for (final c in r.rows) if (c.statement != null) c.statement!];

    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      if (r.warning != null)
        Card(
          color: const Color(0xFFFFF4E5),
          child: ListTile(leading: const Icon(Icons.warning_amber), title: Text(r.warning!)),
        ),
      Card(
        clipBehavior: Clip.antiAlias,
        child: Table(
          columnWidths: const {0: FlexColumnWidth(1.1)},
          border: TableBorder.symmetric(inside: BorderSide(color: Colors.grey.shade300)),
          defaultVerticalAlignment: TableCellVerticalAlignment.middle,
          children: [
            row(
                '',
                Text(r.a.name, style: const TextStyle(fontWeight: FontWeight.bold)),
                Text(r.b.name, style: const TextStyle(fontWeight: FontWeight.bold)),
                header: true),
            row('Score', Row(children: [ScoreBadge(score: r.a.score, band: r.a.band, size: 36)]),
                Row(children: [ScoreBadge(score: r.b.score, band: r.b.band, size: 36)])),
            row('Band', Text(r.a.band), Text(r.b.band)),
            row('Veg / Non-veg', Row(children: [VegMark(isVeg: r.a.isVeg, unknown: r.a.vegUnknown)]),
                Row(children: [VegMark(isVeg: r.b.isVeg, unknown: r.b.vegUnknown)])),
            row('Category', Text(r.a.categoryName), Text(r.b.categoryName)),
            for (final c in r.rows)
              row(c.nutrient, val(c, true, better(c).$1), val(c, false, better(c).$2)),
            row('High in', Text(r.highInA.isEmpty ? 'Nothing' : r.highInA.join(', ')),
                Text(r.highInB.isEmpty ? 'Nothing' : r.highInB.join(', '))),
          ],
        ),
      ),
      const SizedBox(height: 8),
      if (statements.isNotEmpty) ...[
        const SectionTitle('What stands out'),
        for (final s in statements)
          Padding(padding: const EdgeInsets.only(bottom: 6), child: Text('• $s')),
      ],
      const Padding(
        padding: EdgeInsets.only(top: 8),
        child: Text(
          'Green bold = the better value, shown only where the difference is at least 25% and meets '
          'FSSAI’s minimum amount, and both products are in the same category. Otherwise “similar”.',
          style: TextStyle(fontSize: 12, color: Colors.black54),
        ),
      ),
    ]);
  }
}
