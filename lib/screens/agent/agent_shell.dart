import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

class AgentShell extends StatelessWidget {
  final Widget child;
  final int currentIndex;

  const AgentShell({super.key, required this.child, required this.currentIndex});

  static const _tabs = ['/agent/dashboard', '/agent/orders', '/agent/wallet', '/agent/profile'];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: child,
      bottomNavigationBar: NavigationBar(
        selectedIndex: currentIndex,
        onDestinationSelected: (index) => context.go(_tabs[index]),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.dashboard_outlined), label: 'Dashboard'),
          NavigationDestination(icon: Icon(Icons.local_shipping_outlined), label: 'Orders'),
          NavigationDestination(icon: Icon(Icons.account_balance_wallet_outlined), label: 'Wallet'),
          NavigationDestination(icon: Icon(Icons.person_outline), label: 'Profile'),
        ],
      ),
    );
  }
}
