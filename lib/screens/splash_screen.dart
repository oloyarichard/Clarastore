import 'package:flutter/material.dart';
import '../core/constants.dart';

class SplashScreen extends StatelessWidget {
  const SplashScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Image.asset(
              'assets/images/logo.png',
              width: 72,
              height: 72,
              errorBuilder: (context, error, stackTrace) =>
                  const Icon(Icons.checkroom, size: 56, color: AppTheme.pink),
            ),
            const SizedBox(height: 20),
            const CircularProgressIndicator(color: AppTheme.pink),
          ],
        ),
      ),
    );
  }
}
