import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/api_client.dart';
import '../../providers/wallet_provider.dart';

final _currency = NumberFormat.currency(locale: 'en_UG', symbol: 'UGX ', decimalDigits: 0);
final _dateFormat = DateFormat('d MMM, h:mm a');

class AgentWalletScreen extends ConsumerWidget {
  const AgentWalletScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final walletAsync = ref.watch(walletProvider);
    final commissionsAsync = ref.watch(agentCommissionsProvider);
    final transactionsAsync = ref.watch(walletTransactionsProvider);

    return DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('My wallet'),
          bottom: const TabBar(tabs: [Tab(text: 'Earnings'), Tab(text: 'All activity')]),
        ),
        body: Column(
          children: [
            Padding(
              padding: const EdgeInsets.all(20),
              child: walletAsync.when(
                data: (wallet) => Text(
                  _currency.format(wallet.balance),
                  style: const TextStyle(fontSize: 26, fontWeight: FontWeight.bold),
                ),
                loading: () => const CircularProgressIndicator(),
                error: (e, _) => Text(apiErrorMessage(e)),
              ),
            ),
            Expanded(
              child: TabBarView(
                children: [
                  commissionsAsync.when(
                    data: (commissions) {
                      if (commissions.isEmpty) {
                        return const Center(child: Text('No commissions earned yet.'));
                      }
                      final totalEarned =
                          commissions.fold<double>(0, (sum, c) => sum + c.commissionAmount);
                      return Column(
                        children: [
                          Padding(
                            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
                            child: Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                const Text('Total earned'),
                                Text(_currency.format(totalEarned),
                                    style: const TextStyle(fontWeight: FontWeight.bold)),
                              ],
                            ),
                          ),
                          Expanded(
                            child: ListView.builder(
                              padding: const EdgeInsets.symmetric(horizontal: 20),
                              itemCount: commissions.length,
                              itemBuilder: (context, index) {
                                final c = commissions[index];
                                return ListTile(
                                  contentPadding: EdgeInsets.zero,
                                  title: Text('Order #${c.orderId} — ${c.productName}'),
                                  subtitle: Text(_dateFormat.format(c.createdAt)),
                                  trailing: Text(
                                    '+${_currency.format(c.commissionAmount)}',
                                    style: TextStyle(
                                        color: Colors.green.shade700, fontWeight: FontWeight.w600),
                                  ),
                                );
                              },
                            ),
                          ),
                        ],
                      );
                    },
                    loading: () => const Center(child: CircularProgressIndicator()),
                    error: (e, _) => Center(child: Text(apiErrorMessage(e))),
                  ),
                  transactionsAsync.when(
                    data: (txns) => ListView.builder(
                      padding: const EdgeInsets.symmetric(horizontal: 20),
                      itemCount: txns.length,
                      itemBuilder: (context, index) {
                        final t = txns[index];
                        return ListTile(
                          contentPadding: EdgeInsets.zero,
                          leading: Icon(
                            t.amount >= 0 ? Icons.arrow_downward : Icons.arrow_upward,
                            color: t.amount >= 0 ? Colors.green : Colors.red,
                          ),
                          title: Text(t.label),
                          subtitle: Text(_dateFormat.format(t.createdAt)),
                          trailing: Text(
                            '${t.amount >= 0 ? '+' : ''}${_currency.format(t.amount)}',
                            style: TextStyle(
                              color: t.amount >= 0 ? Colors.green.shade700 : Colors.red.shade700,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        );
                      },
                    ),
                    loading: () => const Center(child: CircularProgressIndicator()),
                    error: (e, _) => Center(child: Text(apiErrorMessage(e))),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
