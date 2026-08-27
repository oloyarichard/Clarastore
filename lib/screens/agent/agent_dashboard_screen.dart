import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../core/api_client.dart';
import '../../providers/auth_provider.dart';
import '../../providers/order_provider.dart';
import '../../providers/wallet_provider.dart';
import '../../core/constants.dart';

final _currency = NumberFormat.currency(locale: 'en_UG', symbol: 'UGX ', decimalDigits: 0);

// Must match settings.AGENT_MINIMUM_FLOAT on the backend.
const _minimumFloat = 100000;

class AgentDashboardScreen extends ConsumerWidget {
  const AgentDashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(authProvider).valueOrNull;
    final walletAsync = ref.watch(walletProvider);
    final ordersAsync = ref.watch(orderListProvider);

    return Scaffold(
      appBar: AppBar(title: Text('Hi, ${user?.firstName ?? 'Agent'}')),
      body: RefreshIndicator(
        onRefresh: () async {
          await ref.read(walletProvider.notifier).refresh();
          await ref.read(orderListProvider.notifier).refresh();
        },
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            walletAsync.when(
              data: (wallet) {
                final belowMinimum = wallet.balance < _minimumFloat;
                return Container(
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(
                    color: belowMinimum ? const Color(0xFFFFF0F0) : AppTheme.surface,
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(
                      color: belowMinimum ? Colors.redAccent.withOpacity(0.5) : AppTheme.pink.withOpacity(0.4),
                    ),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Your float',
                          style: TextStyle(color: belowMinimum ? Colors.redAccent : AppTheme.muted)),
                      const SizedBox(height: 6),
                      Text(
                        _currency.format(wallet.balance),
                        style: TextStyle(
                          color: belowMinimum ? Colors.redAccent : AppTheme.pinkDark,
                          fontSize: 26,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      if (belowMinimum) ...[
                        const SizedBox(height: 8),
                        Text(
                          'Below the required minimum of ${_currency.format(_minimumFloat)}. Top up to keep crediting customers.',
                          style: const TextStyle(color: Colors.redAccent, fontSize: 12),
                        ),
                      ],
                    ],
                  ),
                );
              },
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (e, _) => Text(apiErrorMessage(e)),
            ),
            const SizedBox(height: 20),
            Row(
              children: [
                Expanded(
                  child: _ActionCard(
                    icon: Icons.person_add_alt_1_outlined,
                    label: 'Top up a customer',
                    onTap: () => context.push('/agent/topup-customer'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _ActionCard(
                    icon: Icons.payments_outlined,
                    label: 'My earnings',
                    onTap: () => context.push('/agent/wallet'),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 24),
            const Text('Assigned orders', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 16)),
            const SizedBox(height: 8),
            ordersAsync.when(
              data: (orders) {
                final active = orders
                    .where((o) => ['assigned', 'picked_up', 'dispatched'].contains(o.status))
                    .toList();
                if (active.isEmpty) {
                  return const Padding(
                    padding: EdgeInsets.only(top: 12),
                    child: Text('No active deliveries right now.'),
                  );
                }
                return Column(
                  children: active
                      .map((o) => Card(
                            elevation: 0,
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(12),
                              side: const BorderSide(color: AppTheme.line),
                            ),
                            child: ListTile(
                              title: Text('Order #${o.id} — ${o.districtName ?? ''}'),
                              subtitle: Text(o.status),
                              onTap: () => context.push('/orders/${o.id}'),
                            ),
                          ))
                      .toList(),
                );
              },
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (e, _) => Text(apiErrorMessage(e)),
            ),
          ],
        ),
      ),
    );
  }
}

class _ActionCard extends StatelessWidget {
  final IconData icon;
  final String label;
  final VoidCallback onTap;
  const _ActionCard({required this.icon, required this.label, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          border: Border.all(color: AppTheme.line),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, color: AppTheme.pinkDark),
            const SizedBox(height: 10),
            Text(label, style: const TextStyle(fontWeight: FontWeight.w600)),
          ],
        ),
      ),
    );
  }
}
