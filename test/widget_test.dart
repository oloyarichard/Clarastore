// Basic smoke test — confirms the app boots without throwing.
// Replace with real widget/unit tests as the app grows.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:clarastore/main.dart';

void main() {
  testWidgets('App boots without crashing', (WidgetTester tester) async {
    await tester.pumpWidget(const ProviderScope(child: ClarastoreApp()));
    // Just confirms the widget tree builds — the app briefly shows a
    // splash/loading state on boot while checking for a stored session.
    expect(find.byType(MaterialApp), findsOneWidget);
  });
}
