import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class ApiConfig {
  // Hardcoded directly here rather than passed in via --dart-define at
  // build time — one less place for the value to silently drift out of
  // sync. Update this line directly whenever your local IP changes
  // (routers often reassign it), then rebuild.
  static const String baseUrl = 'http://192.168.78.196:8000/api';
}

class OrderStatusMeta {
  static const Map<String, String> labels = {
    'pending': 'Pending',
    'assigned': 'Assigned to agent',
    'picked_up': 'Picked up',
    'dispatched': 'Dispatched',
    'awaiting_confirmation': 'Awaiting your confirmation',
    'delivered': 'Delivered',
    'flagged': 'Flagged — under investigation',
    'lost': 'Lost / Refunded',
    'cancelled': 'Cancelled',
  };

  // Tuned for the light pink/cream background — same semantic meaning as
  // before, retinted so each one holds contrast against a light surface
  // instead of black.
  static const Map<String, Color> colors = {
    'pending': AppTheme.muted,
    'assigned': AppTheme.lavender,
    'picked_up': AppTheme.lavender,
    'dispatched': AppTheme.pink,
    'awaiting_confirmation': Color(0xFFE0A83E),
    'delivered': AppTheme.green,
    'flagged': AppTheme.danger,
    'lost': AppTheme.danger,
    'cancelled': AppTheme.muted,
  };

  static String labelFor(String status) => labels[status] ?? status;
  static Color colorFor(String status) => colors[status] ?? AppTheme.muted;
}

/// Clarastore's theme — warm pink/lavender on a soft cream background,
/// matching clarastore.com exactly (same hex values, same typefaces:
/// Plus Jakarta Sans for headings, DM Sans for body text).
class AppTheme {
  static const Color background = Color(0xFFFFFAFC);
  static const Color surface = Color(0xFFFFFFFF);
  static const Color surface2 = Color(0xFFFFF1F6);
  static const Color ink = Color(0xFF211B24);
  static const Color muted = Color(0xFF817782);
  static const Color line = Color(0xFFEEE3E9);
  static const Color pink = Color(0xFFFF5C9A);
  static const Color pinkDark = Color(0xFFE94382);
  static const Color lavender = Color(0xFF8F7CFF);
  static const Color green = Color(0xFF20A879);
  static const Color danger = Color(0xFFDF5B68);

  static ThemeData get theme {
    final colorScheme = const ColorScheme.light(
      primary: pink,
      onPrimary: Colors.white,
      secondary: lavender,
      onSecondary: Colors.white,
      surface: surface,
      onSurface: ink,
      error: danger,
      onError: Colors.white,
    );

    final displayFont = GoogleFonts.plusJakartaSansTextTheme();
    final bodyFont = GoogleFonts.dmSansTextTheme();

    return ThemeData(
      useMaterial3: true,
      colorScheme: colorScheme,
      scaffoldBackgroundColor: background,
      dividerColor: line,
      appBarTheme: AppBarTheme(
        backgroundColor: background,
        foregroundColor: ink,
        elevation: 0,
        centerTitle: false,
        titleTextStyle: GoogleFonts.plusJakartaSans(
          color: ink,
          fontSize: 20,
          fontWeight: FontWeight.w700,
        ),
      ),
      cardTheme: CardThemeData(
        color: surface,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: const BorderSide(color: line),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: pink,
          foregroundColor: Colors.white,
          disabledBackgroundColor: pink.withOpacity(0.35),
          disabledForegroundColor: AppTheme.muted,
          padding: const EdgeInsets.symmetric(vertical: 14),
          textStyle: GoogleFonts.dmSans(fontWeight: FontWeight.w700),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: pinkDark,
          side: const BorderSide(color: pink),
          padding: const EdgeInsets.symmetric(vertical: 14),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(foregroundColor: pinkDark),
      ),
      inputDecorationTheme: InputDecorationTheme(
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: line),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: line),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: pink, width: 1.5),
        ),
        filled: true,
        fillColor: surface,
        labelStyle: GoogleFonts.dmSans(color: muted),
        hintStyle: GoogleFonts.dmSans(color: muted.withOpacity(0.7)),
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: surface,
        indicatorColor: pink.withOpacity(0.14),
        labelTextStyle: WidgetStateProperty.resolveWith((states) => GoogleFonts.dmSans(
              fontSize: 12,
              fontWeight: FontWeight.w600,
              color: states.contains(WidgetState.selected) ? pinkDark : muted,
            )),
        iconTheme: WidgetStateProperty.resolveWith((states) => IconThemeData(
              color: states.contains(WidgetState.selected) ? pinkDark : muted,
            )),
      ),
      textTheme: bodyFont.copyWith(
        displayLarge: displayFont.displayLarge?.copyWith(color: ink),
        displayMedium: displayFont.displayMedium?.copyWith(color: ink),
        displaySmall: displayFont.displaySmall?.copyWith(color: ink),
        headlineLarge: displayFont.headlineLarge?.copyWith(color: ink, fontWeight: FontWeight.w800),
        headlineMedium: displayFont.headlineMedium?.copyWith(color: ink, fontWeight: FontWeight.w800),
        headlineSmall: displayFont.headlineSmall?.copyWith(color: ink, fontWeight: FontWeight.w700),
        titleLarge: displayFont.titleLarge?.copyWith(color: ink, fontWeight: FontWeight.w700),
        titleMedium: displayFont.titleMedium?.copyWith(color: ink, fontWeight: FontWeight.w700),
        bodyLarge: bodyFont.bodyLarge?.copyWith(color: ink),
        bodyMedium: bodyFont.bodyMedium?.copyWith(color: ink),
        bodySmall: bodyFont.bodySmall?.copyWith(color: muted),
      ),
      iconTheme: const IconThemeData(color: ink),
      dialogTheme: DialogThemeData(
        backgroundColor: surface,
        titleTextStyle: GoogleFonts.plusJakartaSans(color: ink, fontSize: 18, fontWeight: FontWeight.w700),
        contentTextStyle: GoogleFonts.dmSans(color: muted),
      ),
      snackBarTheme: SnackBarThemeData(
        backgroundColor: ink,
        contentTextStyle: GoogleFonts.dmSans(color: Colors.white),
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      ),
      colorSchemeSeed: null,
    );
  }
}
