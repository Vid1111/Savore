import 'package:flutter/material.dart';

import 'screens/home_screen.dart';

void main() => runApp(const SavoreApp());

class SavoreApp extends StatelessWidget {
  const SavoreApp({super.key});

  @override
  Widget build(BuildContext context) {
    final scheme = ColorScheme.fromSeed(seedColor: const Color(0xFF1B8E3E));
    return MaterialApp(
      title: 'Savoré',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: scheme,
        useMaterial3: true,
        scaffoldBackgroundColor: const Color(0xFFF6F8F6),
        cardTheme: const CardTheme(
          elevation: 0,
          margin: EdgeInsets.symmetric(vertical: 4),
          shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.all(Radius.circular(14))),
        ),
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: Colors.white,
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
        ),
      ),
      home: const HomeScreen(),
    );
  }
}
