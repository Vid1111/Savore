import 'package:flutter/material.dart';

import '../data/api.dart';
import '../data/models.dart';
import '../widgets.dart';

/// "Not found" + product entry form. Sends the product to the server for review.
class ManualSubmitScreen extends StatefulWidget {
  final String? barcode; // set when a scan/lookup found nothing
  const ManualSubmitScreen({super.key, this.barcode});

  @override
  State<ManualSubmitScreen> createState() => _ManualSubmitScreenState();
}

/// (server key, label, required?)
const _nutrientFields = [
  ('energy_kcal', 'Energy (kcal)', true),
  ('protein_g', 'Protein (g)', true),
  ('carbohydrate_g', 'Carbohydrate (g)', true),
  ('total_sugar_g', 'Total sugars (g)', true),
  ('added_sugar_g', 'Added sugar (g), if printed', false),
  ('total_fat_g', 'Total fat (g)', true),
  ('sat_fat_g', 'Saturated fat (g)', true),
  ('fibre_g', 'Dietary fibre (g)', false),
  ('sodium_mg', 'Sodium (mg)', true),
];

class _ManualSubmitScreenState extends State<ManualSubmitScreen> {
  final _form = GlobalKey<FormState>();
  late final _barcode = TextEditingController(text: widget.barcode);
  final _name = TextEditingController();
  final _brand = TextEditingController();
  final _ingredients = TextEditingController();
  final _allergens = TextEditingController();
  final _serve = TextEditingController();
  final _nutrients = {for (final f in _nutrientFields) f.$1: TextEditingController()};
  late final Future<List<CategoryOption>> _categories = Api.categories();
  String? _category;
  bool _isVeg = true;
  bool _busy = false;

  String? _required(String? v) => (v == null || v.trim().isEmpty) ? 'Required' : null;

  String? _number(String? v, {bool required = false}) {
    if (v == null || v.trim().isEmpty) return required ? 'Required' : null;
    final n = double.tryParse(v.trim());
    if (n == null) return 'Enter a number';
    return n < 0 ? 'Cannot be negative' : null;
  }

  double? _d(String key) => double.tryParse(_nutrients[key]!.text.trim());

  Future<void> _submit() async {
    if (!_form.currentState!.validate()) return;
    final body = {
      'barcode': _barcode.text.trim(),
      'name': _name.text.trim(),
      'brand': _brand.text.trim().isEmpty ? null : _brand.text.trim(),
      'category_code': _category,
      'veg_status': _isVeg ? 'veg' : 'non_veg',
      'serve_size': double.parse(_serve.text.trim()),
      'ingredients_text': _ingredients.text.trim(),
      'allergens': [
        for (final a in _allergens.text.split(',')) if (a.trim().isNotEmpty) a.trim()
      ],
      'nutrition': {
        for (final f in _nutrientFields)
          if (_d(f.$1) != null) f.$1: _d(f.$1),
      },
    };

    setState(() => _busy = true);
    try {
      await Api.submit(body);
      if (!mounted) return;
      await showDialog<void>(
        context: context,
        builder: (ctx) => AlertDialog(
          icon: const Icon(Icons.check_circle, color: Colors.green, size: 40),
          title: const Text('Thanks!'),
          content: Text('“${_name.text}” was sent for review. '
              'It will appear in the app once our team checks it.'),
          actions: [FilledButton(onPressed: () => Navigator.pop(ctx), child: const Text('OK'))],
        ),
      );
      if (mounted) Navigator.popUntil(context, (r) => r.isFirst);
    } on ApiException catch (e) {
      if (!mounted) return;
      await showDialog<void>(
        context: context,
        builder: (ctx) => AlertDialog(
          icon: const Icon(Icons.error_outline, size: 40),
          title: const Text('Can’t submit yet'),
          content: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
              if (e.errors.isEmpty) Text(e.message),
              for (final err in e.errors)
                Padding(padding: const EdgeInsets.only(bottom: 6), child: Text('• $err')),
            ]),
          ),
          actions: [FilledButton(onPressed: () => Navigator.pop(ctx), child: const Text('OK'))],
        ),
      );
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final wide = isWide(context);
    const gap = SizedBox(height: 12, width: 12);

    Widget pair(Widget a, Widget b) => wide
        ? Row(crossAxisAlignment: CrossAxisAlignment.start, children: [Expanded(child: a), gap, Expanded(child: b)])
        : Column(children: [a, gap, b]);

    final categoryField = FutureBuilder<List<CategoryOption>>(
      future: _categories,
      builder: (context, snap) {
        if (snap.hasError) return Text('Can’t load categories: ${snap.error}');
        return DropdownButtonFormField<String>(
          value: _category,
          isExpanded: true,
          decoration: const InputDecoration(labelText: 'Category *'),
          items: [
            for (final c in snap.data ?? const <CategoryOption>[])
              DropdownMenuItem(value: c.code, child: Text(c.name, overflow: TextOverflow.ellipsis)),
          ],
          onChanged: (v) => setState(() => _category = v),
          validator: _required,
        );
      },
    );

    return Scaffold(
      appBar: AppBar(title: Text(widget.barcode != null ? 'Product not found' : 'Add a product')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: PageBody(
          maxWidth: 800,
          child: Form(
            key: _form,
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              if (widget.barcode != null)
                Card(
                  color: const Color(0xFFFFF4E5),
                  child: ListTile(
                    leading: const Icon(Icons.search_off),
                    title: Text('We don’t have barcode ${widget.barcode} yet'),
                    subtitle: const Text('Help others by adding it from the pack label below.'),
                  ),
                ),
              const SectionTitle('Product'),
              pair(
                TextFormField(
                  controller: _barcode,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(labelText: 'Barcode *'),
                  validator: _required,
                ),
                TextFormField(
                  controller: _name,
                  decoration: const InputDecoration(labelText: 'Product name *'),
                  validator: _required,
                ),
              ),
              gap,
              pair(
                TextFormField(controller: _brand, decoration: const InputDecoration(labelText: 'Brand')),
                categoryField,
              ),
              gap,
              SegmentedButton<bool>(
                segments: const [
                  ButtonSegment(value: true, label: Text('Vegetarian'), icon: VegMark(isVeg: true, size: 16)),
                  ButtonSegment(
                      value: false, label: Text('Non-vegetarian'), icon: VegMark(isVeg: false, size: 16)),
                ],
                selected: {_isVeg},
                onSelectionChanged: (s) => setState(() => _isVeg = s.first),
              ),
              const SectionTitle('Ingredients and allergens'),
              TextFormField(
                controller: _ingredients,
                maxLines: 4,
                decoration: const InputDecoration(
                    labelText: 'Ingredients *',
                    hintText: 'Copy exactly from the pack, separated by commas'),
                validator: _required,
              ),
              gap,
              TextFormField(
                controller: _allergens,
                decoration: const InputDecoration(
                    labelText: 'Allergens (optional)', hintText: 'e.g. Gluten, Milk, Soy'),
              ),
              const SectionTitle('Nutrition (per 100 g, or per 100 ml for drinks)'),
              TextFormField(
                controller: _serve,
                keyboardType: const TextInputType.numberWithOptions(decimal: true),
                decoration: const InputDecoration(labelText: 'Serve size (g or ml) *'),
                validator: (v) => _number(v, required: true),
              ),
              gap,
              GridView.count(
                crossAxisCount: wide ? 3 : 2,
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                mainAxisSpacing: 12,
                crossAxisSpacing: 12,
                childAspectRatio: wide ? 3.2 : 2.4,
                children: [
                  for (final f in _nutrientFields)
                    TextFormField(
                      controller: _nutrients[f.$1],
                      keyboardType: const TextInputType.numberWithOptions(decimal: true),
                      decoration: InputDecoration(labelText: f.$3 ? '${f.$2} *' : f.$2),
                      validator: (v) => _number(v, required: f.$3),
                    ),
                ],
              ),
              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  onPressed: _busy ? null : _submit,
                  icon: _busy
                      ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Icon(Icons.send),
                  label: const Text('Submit for review'),
                ),
              ),
            ]),
          ),
        ),
      ),
    );
  }
}
