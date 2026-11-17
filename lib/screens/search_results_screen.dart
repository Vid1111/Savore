import 'package:flutter/material.dart';

import '../data/api.dart';
import '../data/models.dart';
import '../widgets.dart';
import 'manual_submit_screen.dart';

class SearchResultsScreen extends StatefulWidget {
  final String query;
  const SearchResultsScreen({super.key, required this.query});

  @override
  State<SearchResultsScreen> createState() => _SearchResultsScreenState();
}

class _SearchResultsScreenState extends State<SearchResultsScreen> {
  late String _query = widget.query;
  late final _ctrl = SearchController()..text = widget.query;

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final width = MediaQuery.sizeOf(context).width;
    final columns = width >= 1100 ? 3 : (width >= 700 ? 2 : 1);

    return Scaffold(
      appBar: AppBar(title: const Text('Search')),
      body: PageBody(
        child: Column(children: [
          Padding(
            padding: const EdgeInsets.all(16),
            child: SearchBar(
              controller: _ctrl,
              hintText: 'Search products',
              leading: const Icon(Icons.search),
              elevation: const WidgetStatePropertyAll(0),
              onSubmitted: (q) => setState(() => _query = q),
            ),
          ),
          Expanded(
            // A new key makes the list reload whenever the query changes.
            child: AsyncView<List<ProductSummary>>(
              key: ValueKey(_query),
              load: () => Api.search(_query),
              builder: (context, results) => Column(children: [
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  child: Align(
                    alignment: Alignment.centerLeft,
                    child: Text('${results.length} result(s)'
                        '${_query.isEmpty ? '' : ' for “$_query”'}'
                        '${results.length >= 50 ? ' (showing the first 50: type more to narrow down)' : ''}'),
                  ),
                ),
                Expanded(
                  child: results.isEmpty
                      ? Center(
                          child: Column(mainAxisSize: MainAxisSize.min, children: [
                            const Icon(Icons.search_off, size: 48),
                            const SizedBox(height: 8),
                            const Text('No products found'),
                            const SizedBox(height: 12),
                            FilledButton(
                              onPressed: () => Navigator.push(
                                  context,
                                  MaterialPageRoute(
                                      builder: (_) => const ManualSubmitScreen())),
                              child: const Text('Add this product'),
                            ),
                          ]),
                        )
                      : GridView.builder(
                          padding: const EdgeInsets.all(16),
                          gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                            crossAxisCount: columns,
                            mainAxisExtent: 84,
                            crossAxisSpacing: 8,
                          ),
                          itemCount: results.length,
                          itemBuilder: (_, i) => ProductTile(product: results[i]),
                        ),
                ),
              ]),
            ),
          ),
        ]),
      ),
    );
  }
}
