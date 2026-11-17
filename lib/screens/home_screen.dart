import 'package:flutter/material.dart';

import '../data/api.dart';
import '../data/models.dart';
import '../widgets.dart';
import 'compare_screen.dart';
import 'manual_submit_screen.dart';
import 'scanner_screen.dart';
import 'search_results_screen.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  Future<void> _scan(BuildContext context) async {
    final code = await Navigator.push<String>(
        context, MaterialPageRoute(builder: (_) => const ScannerScreen()));
    if (code != null && context.mounted) openBarcode(context, code);
  }

  Future<void> _typeBarcode(BuildContext context) async {
    final ctrl = TextEditingController();
    final code = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Type barcode'),
        content: TextField(
          controller: ctrl,
          autofocus: true,
          keyboardType: TextInputType.number,
          decoration: const InputDecoration(hintText: 'e.g. 8901000000011'),
          onSubmitted: (v) => Navigator.pop(ctx, v),
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('Cancel')),
          FilledButton(
              onPressed: () => Navigator.pop(ctx, ctrl.text),
              child: const Text('Look up')),
        ],
      ),
    );
    if (code != null && code.trim().isNotEmpty && context.mounted) {
      openBarcode(context, code);
    }
  }

  void _search(BuildContext context, String q) => Navigator.push(context,
      MaterialPageRoute(builder: (_) => SearchResultsScreen(query: q)));

  @override
  Widget build(BuildContext context) {
    final wide = isWide(context);

    final scanCard = Card(
      color: Theme.of(context).colorScheme.primaryContainer,
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Know what’s inside',
                style: Theme.of(context).textTheme.headlineSmall),
            const SizedBox(height: 4),
            const Text('Scan a packaged food barcode to see its score, '
                'nutrition and ingredients.'),
            const SizedBox(height: 16),
            Wrap(spacing: 12, runSpacing: 12, children: [
              FilledButton.icon(
                onPressed: () => _scan(context),
                icon: const Icon(Icons.qr_code_scanner),
                label: const Text('Scan barcode'),
              ),
              OutlinedButton.icon(
                onPressed: () => _typeBarcode(context),
                icon: const Icon(Icons.keyboard),
                label: const Text('Type barcode'),
              ),
            ]),
          ],
        ),
      ),
    );

    final searchBar = SearchBar(
      hintText: 'Search products, brands, categories',
      leading: const Icon(Icons.search),
      elevation: const WidgetStatePropertyAll(0),
      onSubmitted: (q) => _search(context, q),
    );

    final recent = ValueListenableBuilder<List<ProductSummary>>(
      valueListenable: recentScans,
      builder: (context, list, _) {
        if (list.isEmpty) {
          return const Card(
            child: Padding(
              padding: EdgeInsets.all(20),
              child: Text('No scans yet. Try barcode 8901000000011, '
                  'or search “noodles”.'),
            ),
          );
        }
        return Column(
            children: [for (final p in list) ProductTile(product: p)]);
      },
    );

    final quickLinks = Wrap(spacing: 8, runSpacing: 8, children: [
      ActionChip(
        avatar: const Icon(Icons.compare_arrows, size: 18),
        label: const Text('Compare products'),
        onPressed: () => Navigator.push(context,
            MaterialPageRoute(builder: (_) => const CompareScreen())),
      ),
      ActionChip(
        avatar: const Icon(Icons.add_box_outlined, size: 18),
        label: const Text('Add a product'),
        onPressed: () => Navigator.push(context,
            MaterialPageRoute(builder: (_) => const ManualSubmitScreen())),
      ),
      ActionChip(
        avatar: const Icon(Icons.list, size: 18),
        label: const Text('Browse all'),
        onPressed: () => _search(context, ''),
      ),
    ]);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Savoré'),
        actions: [
          IconButton(
            tooltip: 'Compare',
            icon: const Icon(Icons.compare_arrows),
            onPressed: () => Navigator.push(context,
                MaterialPageRoute(builder: (_) => const CompareScreen())),
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: PageBody(
          child: wide
              ? Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                        child: Column(children: [
                      searchBar,
                      const SizedBox(height: 12),
                      scanCard,
                      const SizedBox(height: 12),
                      Align(alignment: Alignment.centerLeft, child: quickLinks),
                    ])),
                    const SizedBox(width: 24),
                    Expanded(
                        child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                          const SectionTitle('Recent scans'),
                          recent,
                        ])),
                  ],
                )
              : Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    searchBar,
                    const SizedBox(height: 12),
                    scanCard,
                    const SizedBox(height: 12),
                    quickLinks,
                    const SectionTitle('Recent scans'),
                    recent,
                  ],
                ),
        ),
      ),
    );
  }
}
