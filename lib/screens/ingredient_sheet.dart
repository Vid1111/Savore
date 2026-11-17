import 'package:flutter/material.dart';

import '../data/api.dart';
import '../data/models.dart';
import '../widgets.dart';

/// Bottom sheet explaining one ingredient / INS code (loaded from the server).
void showIngredientSheet(BuildContext context, IngredientRef ref) {
  showModalBottomSheet(
    context: context,
    showDragHandle: true,
    isScrollControlled: true,
    constraints: const BoxConstraints(maxWidth: 640),
    builder: (ctx) => SafeArea(
      child: ConstrainedBox(
        constraints: const BoxConstraints(minHeight: 240),
        child: AsyncView<IngredientInfo>(
          load: () => Api.ingredient(ref.id!),
          builder: (context, ing) {
            final t = Theme.of(context).textTheme;
            Widget block(String title, String body, IconData icon) => Padding(
                  padding: const EdgeInsets.only(bottom: 16),
                  child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Icon(icon, size: 22),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text(title, style: t.labelLarge),
                        const SizedBox(height: 2),
                        Text(body),
                      ]),
                    ),
                  ]),
                );

            return SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(24, 0, 24, 24),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(ing.name, style: t.headlineSmall),
                  Wrap(spacing: 8, children: [
                    if (ing.insCode != null) Chip(label: Text(ing.insCode!)),
                    if (ing.functionalClass != null) Chip(label: Text(ing.functionalClass!)),
                  ]),
                  const SizedBox(height: 12),
                  block('What it is', ing.whatItIs, Icons.info_outline),
                  block('Why it’s used', ing.whyUsed, Icons.build_outlined),
                  block('Source', ing.source, Icons.menu_book_outlined),
                ],
              ),
            );
          },
        ),
      ),
    ),
  );
}
