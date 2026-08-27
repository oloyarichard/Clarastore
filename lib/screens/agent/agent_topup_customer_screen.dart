import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api_client.dart';
import '../../providers/wallet_provider.dart';
import '../../widgets/loading_button.dart';

class AgentTopUpCustomerScreen extends ConsumerStatefulWidget {
  const AgentTopUpCustomerScreen({super.key});

  @override
  ConsumerState<AgentTopUpCustomerScreen> createState() => _AgentTopUpCustomerScreenState();
}

class _AgentTopUpCustomerScreenState extends ConsumerState<AgentTopUpCustomerScreen> {
  final _identifierController = TextEditingController();
  final _amountController = TextEditingController();
  bool _submitting = false;

  @override
  Widget build(BuildContext context) {
    final walletAsync = ref.watch(walletProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Top up a customer')),
      body: Padding(
        padding: const EdgeInsets.all(20),
        child: ListView(
          children: [
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: Colors.blue.shade50,
                borderRadius: BorderRadius.circular(10),
              ),
              child: const Row(
                children: [
                  Icon(Icons.info_outline, color: Colors.blue),
                  SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      'Collect cash from the customer first, then credit their wallet here. '
                      'The amount comes out of your own float.',
                      style: TextStyle(fontSize: 13),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),
            TextField(
              controller: _identifierController,
              decoration: const InputDecoration(labelText: "Customer's email or phone"),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _amountController,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(labelText: 'Amount (UGX)'),
            ),
            const SizedBox(height: 8),
            walletAsync.when(
              data: (wallet) => Text(
                'Your current float: UGX ${wallet.balance.toStringAsFixed(0)}',
                style: TextStyle(color: Colors.grey.shade600, fontSize: 13),
              ),
              loading: () => const SizedBox.shrink(),
              error: (_, __) => const SizedBox.shrink(),
            ),
            const SizedBox(height: 20),
            LoadingButton(
              label: 'Confirm top-up',
              isLoading: _submitting,
              onPressed: () async {
                final amount = double.tryParse(_amountController.text);
                if (amount == null || amount <= 0 || _identifierController.text.isEmpty) return;
                setState(() => _submitting = true);
                try {
                  await ref.read(walletServiceProvider).agentTopUpCustomer(
                        customerIdentifier: _identifierController.text.trim(),
                        amount: amount,
                      );
                  ref.read(walletProvider.notifier).refresh();
                  if (context.mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('Customer wallet topped up.')),
                    );
                    _identifierController.clear();
                    _amountController.clear();
                  }
                } catch (e) {
                  if (context.mounted) {
                    ScaffoldMessenger.of(context)
                        .showSnackBar(SnackBar(content: Text(apiErrorMessage(e))));
                  }
                } finally {
                  if (mounted) setState(() => _submitting = false);
                }
              },
            ),
          ],
        ),
      ),
    );
  }
}
