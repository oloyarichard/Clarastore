import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/api_client.dart';
import '../../core/constants.dart';
import '../../providers/wallet_provider.dart';
import '../../widgets/loading_button.dart';

final _currency = NumberFormat.currency(locale: 'en_UG', symbol: 'UGX ', decimalDigits: 0);
final _dateFormat = DateFormat('d MMM, h:mm a');

class WalletScreen extends ConsumerWidget {
  const WalletScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final walletAsync = ref.watch(walletProvider);
    final transactionsAsync = ref.watch(walletTransactionsProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Wallet')),
      body: RefreshIndicator(
        onRefresh: () async {
          await ref.read(walletProvider.notifier).refresh();
          ref.invalidate(walletTransactionsProvider);
        },
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: AppTheme.surface,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: AppTheme.pink.withOpacity(0.4)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Balance', style: TextStyle(color: AppTheme.muted)),
                  const SizedBox(height: 6),
                  walletAsync.when(
                    data: (wallet) => Text(
                      _currency.format(wallet.balance),
                      style: const TextStyle(
                          color: AppTheme.pinkDark, fontSize: 28, fontWeight: FontWeight.bold),
                    ),
                    loading: () => const SizedBox(
                      height: 28,
                      child: CircularProgressIndicator(color: AppTheme.pink, strokeWidth: 2),
                    ),
                    error: (e, _) => const Text('—', style: TextStyle(color: Colors.white)),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                onPressed: () => _showTopUpSheet(context, ref),
                icon: const Icon(Icons.add_circle_outline),
                label: const Text('Top up (MTN MoMo / Airtel Money)'),
              ),
            ),
            const SizedBox(height: 24),
            const Text('Recent activity', style: TextStyle(fontWeight: FontWeight.w600)),
            const SizedBox(height: 8),
            transactionsAsync.when(
              data: (txns) {
                if (txns.isEmpty) {
                  return const Padding(
                    padding: EdgeInsets.only(top: 16),
                    child: Text('No activity yet.'),
                  );
                }
                return Column(
                  children: txns
                      .map((t) => ListTile(
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
                          ))
                      .toList(),
                );
              },
              loading: () => const Padding(
                padding: EdgeInsets.only(top: 20),
                child: Center(child: CircularProgressIndicator()),
              ),
              error: (e, _) => Text('Could not load activity: ${apiErrorMessage(e)}'),
            ),
          ],
        ),
      ),
    );
  }

  void _showTopUpSheet(BuildContext context, WidgetRef ref) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (_) => const _TopUpSheet(),
    );
  }
}

class _TopUpSheet extends ConsumerStatefulWidget {
  const _TopUpSheet();

  @override
  ConsumerState<_TopUpSheet> createState() => _TopUpSheetState();
}

class _TopUpSheetState extends ConsumerState<_TopUpSheet> {
  final _amountController = TextEditingController();
  final _phoneController = TextEditingController();
  String? _provider; // null = auto-detect from phone prefix

  @override
  Widget build(BuildContext context) {
    final flowState = ref.watch(topUpFlowProvider);

    ref.listen(topUpFlowProvider, (previous, next) {
      next.whenOrNull(
        data: (request) {
          if (request != null && request.status == 'successful') {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('Top-up successful!')),
            );
            Navigator.of(context).pop();
          } else if (request != null && request.status == 'failed') {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('Top-up failed or was declined.')),
            );
          }
        },
        error: (error, _) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(apiErrorMessage(error))),
          );
        },
      );
    });

    final request = flowState.valueOrNull;
    final isWaiting = flowState.isLoading || (request != null && request.status == 'pending');

    return Padding(
      padding: EdgeInsets.only(
        left: 20,
        right: 20,
        top: 20,
        bottom: MediaQuery.of(context).viewInsets.bottom + 20,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Top up wallet', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
          const SizedBox(height: 16),
          if (request != null && request.status == 'pending') ...[
            const Center(
              child: Column(
                children: [
                  CircularProgressIndicator(),
                  SizedBox(height: 16),
                  Text('Check your phone and approve the payment prompt.',
                      textAlign: TextAlign.center),
                ],
              ),
            ),
          ] else ...[
            TextField(
              controller: _amountController,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(labelText: 'Amount (UGX)'),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _phoneController,
              keyboardType: TextInputType.phone,
              decoration: const InputDecoration(labelText: 'Phone number', hintText: '07XXXXXXXX'),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: ChoiceChip(
                    label: const Text('Auto-detect'),
                    selected: _provider == null,
                    onSelected: (_) => setState(() => _provider = null),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: ChoiceChip(
                    label: const Text('MTN MoMo'),
                    selected: _provider == 'mtn_momo',
                    onSelected: (_) => setState(() => _provider = 'mtn_momo'),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: ChoiceChip(
                    label: const Text('Airtel'),
                    selected: _provider == 'airtel_money',
                    onSelected: (_) => setState(() => _provider = 'airtel_money'),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            LoadingButton(
              label: 'Send top-up request',
              isLoading: isWaiting,
              onPressed: () {
                final amount = double.tryParse(_amountController.text);
                if (amount == null || amount <= 0 || _phoneController.text.isEmpty) return;
                ref.read(topUpFlowProvider.notifier).start(
                      amount: amount,
                      phoneNumber: _phoneController.text.trim(),
                      provider: _provider,
                    );
              },
            ),
          ],
        ],
      ),
    );
  }
}
