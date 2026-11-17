import 'package:flutter/material.dart';

import 'data/api.dart';
import 'data/models.dart';
import 'screens/manual_submit_screen.dart';
import 'screens/product_screen.dart';

// ---------- Responsive helpers ----------

bool isWide(BuildContext context) => MediaQuery.sizeOf(context).width >= 800;

/// Centres content and caps its width so it reads well on tablets/desktop.
class PageBody extends StatelessWidget {
  final Widget child;
  final double maxWidth;
  const PageBody({super.key, required this.child, this.maxWidth = 1100});

  @override
  Widget build(BuildContext context) => Align(
        alignment: Alignment.topCenter,
        child: ConstrainedBox(
          constraints: BoxConstraints(maxWidth: maxWidth),
          child: child,
        ),
      );
}

// ---------- Loading / error wrapper ----------

/// Loads data from the server and shows a spinner, an error with Retry, or the result.
/// Pass [initial] when you already have the data (skips the first load).
class AsyncView<T> extends StatefulWidget {
  final Future<T> Function() load;
  final Widget Function(BuildContext context, T data) builder;
  final T? initial;
  const AsyncView({super.key, required this.load, required this.builder, this.initial});

  @override
  State<AsyncView<T>> createState() => _AsyncViewState<T>();
}

class _AsyncViewState<T> extends State<AsyncView<T>> {
  late Future<T> _future =
      widget.initial != null ? Future.value(widget.initial as T) : widget.load();

  void _retry() => setState(() => _future = widget.load());

  @override
  Widget build(BuildContext context) => FutureBuilder<T>(
        future: _future,
        builder: (context, snap) {
          if (snap.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snap.hasError) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(mainAxisSize: MainAxisSize.min, children: [
                  const Icon(Icons.cloud_off, size: 48),
                  const SizedBox(height: 12),
                  Text('${snap.error}', textAlign: TextAlign.center),
                  const SizedBox(height: 16),
                  FilledButton(onPressed: _retry, child: const Text('Try again')),
                ]),
              ),
            );
          }
          return widget.builder(context, snap.data as T);
        },
      );
}

// ---------- Navigation helpers ----------

/// Barcode lookup on the server: product page if found, otherwise the "Not found" form.
Future<void> openBarcode(BuildContext context, String code) async {
  final nav = Navigator.of(context);
  final messenger = ScaffoldMessenger.of(context);
  showDialog(
      context: context,
      barrierDismissible: false,
      builder: (_) => const Center(child: CircularProgressIndicator()));
  try {
    final detail = await Api.byBarcode(code);
    nav.pop(); // close the loading spinner
    if (detail != null) {
      addRecent(detail.summary);
      nav.push(MaterialPageRoute(
          builder: (_) => ProductScreen(productId: detail.summary.id, initial: detail)));
    } else {
      nav.push(MaterialPageRoute(builder: (_) => ManualSubmitScreen(barcode: code)));
    }
  } on ApiException catch (e) {
    nav.pop();
    messenger.showSnackBar(SnackBar(content: Text(e.message)));
  }
}

void openProduct(BuildContext context, ProductSummary p) {
  addRecent(p);
  Navigator.push(context, MaterialPageRoute(builder: (_) => ProductScreen(productId: p.id)));
}

// ---------- Colours ----------

/// Neutral blues for the score bands (PRD: no red/green moral framing on the score).
/// The band word is always shown next to the colour.
Color bandColor(String band) => switch (band) {
      'Limit' => const Color(0xFF37474F),
      'Moderate' => const Color(0xFF2F6DA3),
      _ => const Color(0xFF0E7C86), // Better choice
    };

Color levelColor(Level l) => switch (l) {
      Level.low => const Color(0xFF1B8E3E),
      Level.moderate => const Color(0xFFB26A00),
      Level.high => const Color(0xFFDC2626),
    };

// ---------- Small widgets ----------

/// Indian veg (green dot) / non-veg (brown triangle) mark.
class VegMark extends StatelessWidget {
  final bool isVeg;
  final bool unknown; // label doesn't say: grey box with a question mark
  final double size;
  const VegMark({super.key, required this.isVeg, this.unknown = false, this.size = 18});

  @override
  Widget build(BuildContext context) {
    if (unknown) {
      return Tooltip(
        message: 'Veg / non-veg not declared',
        child: Container(
          width: size,
          height: size,
          alignment: Alignment.center,
          decoration: BoxDecoration(
              border: Border.all(color: Colors.grey.shade600, width: 1.6),
              borderRadius: BorderRadius.circular(2)),
          child: Text('?',
              style: TextStyle(fontSize: size * 0.7, fontWeight: FontWeight.bold, color: Colors.grey.shade700)),
        ),
      );
    }
    final c = isVeg ? const Color(0xFF1B8E3E) : const Color(0xFF7B3F00);
    return Tooltip(
      message: isVeg ? 'Vegetarian' : 'Non-vegetarian',
      child: Container(
        width: size,
        height: size,
        padding: EdgeInsets.all(size * 0.18),
        decoration: BoxDecoration(
            border: Border.all(color: c, width: 1.6), borderRadius: BorderRadius.circular(2)),
        child: isVeg
            ? DecoratedBox(decoration: BoxDecoration(color: c, shape: BoxShape.circle))
            : CustomPaint(painter: _TrianglePainter(c)),
      ),
    );
  }
}

class _TrianglePainter extends CustomPainter {
  final Color color;
  _TrianglePainter(this.color);
  @override
  void paint(Canvas canvas, Size s) {
    final path = Path()
      ..moveTo(s.width / 2, 0)
      ..lineTo(s.width, s.height)
      ..lineTo(0, s.height)
      ..close();
    canvas.drawPath(path, Paint()..color = color);
  }

  @override
  bool shouldRepaint(_TrianglePainter old) => old.color != color;
}

class ScoreBadge extends StatelessWidget {
  final int score;
  final String band;
  final double size;
  const ScoreBadge({super.key, required this.score, required this.band, this.size = 44});

  @override
  Widget build(BuildContext context) => Semantics(
        label: 'Score $score, $band',
        child: Container(
          width: size,
          height: size,
          alignment: Alignment.center,
          decoration: BoxDecoration(color: bandColor(band), shape: BoxShape.circle),
          child: Text('$score',
              style: TextStyle(
                  color: Colors.white, fontWeight: FontWeight.bold, fontSize: size * 0.38)),
        ),
      );
}

class LevelChip extends StatelessWidget {
  final String label;
  final Level level;
  const LevelChip({super.key, required this.label, required this.level});

  @override
  Widget build(BuildContext context) {
    final c = levelColor(level);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: c.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: c.withValues(alpha: 0.5)),
      ),
      child: Text('$label: ${level.label}',
          style: TextStyle(color: c, fontWeight: FontWeight.w600)),
    );
  }
}

class SectionTitle extends StatelessWidget {
  final String text;
  const SectionTitle(this.text, {super.key});
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(top: 20, bottom: 8),
        child: Text(text, style: Theme.of(context).textTheme.titleMedium),
      );
}

/// Row used in search results and recent scans.
class ProductTile extends StatelessWidget {
  final ProductSummary product;
  const ProductTile({super.key, required this.product});

  @override
  Widget build(BuildContext context) {
    final p = product;
    return Card(
      child: ListTile(
        onTap: () => openProduct(context, p),
        leading: ScoreBadge(score: p.score, band: p.band),
        title: Row(children: [
          VegMark(isVeg: p.isVeg, unknown: p.vegUnknown, size: 14),
          const SizedBox(width: 8),
          Expanded(child: Text(p.name, overflow: TextOverflow.ellipsis)),
        ]),
        subtitle: Text('${p.brand ?? 'Unknown brand'} · ${p.categoryName} · ${p.band}',
            maxLines: 2, overflow: TextOverflow.ellipsis),
        trailing: const Icon(Icons.chevron_right),
      ),
    );
  }
}
