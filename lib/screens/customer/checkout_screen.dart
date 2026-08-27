import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../core/api_client.dart';
import '../../core/constants.dart';
import '../../providers/auth_provider.dart';
import '../../providers/cart_provider.dart';
import '../../providers/order_provider.dart';
import '../../providers/wallet_provider.dart';
import '../../services/order_service.dart';
import '../../widgets/loading_button.dart';

final _currency = NumberFormat.currency(locale: 'en_UG', symbol: 'UGX ', decimalDigits: 0);

class CheckoutScreen extends ConsumerStatefulWidget {
  const CheckoutScreen({super.key});

  @override
  ConsumerState<CheckoutScreen> createState() => _CheckoutScreenState();
}

class _CheckoutScreenState extends ConsumerState<CheckoutScreen> {
  int? _selectedDistrict;
  bool _placing = false;

  @override
  void initState() {
    super.initState();
    // Default to the customer's own delivery district, they can change it.
    final user = ref.read(authProvider).valueOrNull;
    _selectedDistrict = user?.district;
  }

  @override
  Widget build(BuildContext context) {
    final cartAsync = ref.watch(cartProvider);
    final walletAsync = ref.watch(walletProvider);
    final districtsAsync = ref.watch(districtsProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Checkout')),
      body: cartAsync.when(
        data: (cart) => SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Delivery district', style: TextStyle(fontWeight: FontWeight.w600)),
              const SizedBox(height: 8),
              districtsAsync.when(
                data: (districts) => DropdownButtonFormField<int>(
                  value: _selectedDistrict,
                  items: districts
                      .map((d) => DropdownMenuItem(
                            value: d.id,
                            child: Text(d.isHub ? '${d.name} (Hub — direct delivery)' : '${d.name} (via hub, taxi/bus)'),
                          ))
                      .toList(),
                  onChanged: (v) => setState(() => _selectedDistrict = v),
                ),
                loading: () => const LinearProgressIndicator(),
                error: (e, _) => Text(apiErrorMessage(e)),
              ),
              const SizedBox(height: 24),
              const Text('Order summary', style: TextStyle(fontWeight: FontWeight.w600)),
              const SizedBox(height: 8),
              ...cart.items.map((item) => Padding(
                    padding: const EdgeInsets.symmetric(vertical: 4),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Expanded(child: Text('${item.product.name} x${item.quantity}')),
                        Text(_currency.format(item.subtotal)),
                      ],
                    ),
                  )),
              const Divider(height: 32),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text('Total', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                  Text(_currency.format(cart.total),
                      style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                ],
              ),
              const SizedBox(height: 16),
              walletAsync.when(
                data: (wallet) {
                  final insufficient = wallet.balance < cart.total;
                  return Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: insufficient ? const Color(0xFFFFF0F0) : const Color(0xFFEAFAF3),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                        color: insufficient ? AppTheme.danger.withOpacity(0.4) : AppTheme.green.withOpacity(0.4),
                      ),
                    ),
                    child: Row(
                      children: [
                        Icon(
                          insufficient ? Icons.error_outline : Icons.account_balance_wallet_outlined,
                          color: insufficient ? AppTheme.danger : AppTheme.green,
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            insufficient
                                ? 'Wallet balance ${_currency.format(wallet.balance)} is not enough. Top up before checking out.'
                                : 'Paying from wallet — balance ${_currency.format(wallet.balance)}',
                            style: TextStyle(color: insufficient ? AppTheme.danger : AppTheme.green),
                          ),
                        ),
                      ],
                    ),
                  );
                },
                loading: () => const LinearProgressIndicator(),
                error: (e, _) => Text(apiErrorMessage(e)),
              ),
              const SizedBox(height: 24),
              LoadingButton(
                label: 'Place order',
                isLoading: _placing,
                onPressed: _selectedDistrict == null
                    ? null
                    : () async {
                        setState(() => _placing = true);
                        try {
                          final order = await OrderService().checkout(districtId: _selectedDistrict!);
                          ref.invalidate(cartProvider);
                          ref.invalidate(walletProvider);
                          ref.read(orderListProvider.notifier).refresh();
                          if (context.mounted) {
                            context.go('/orders/${order.id}');
                          }
                        } catch (e) {
                          if (context.mounted) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(content: Text(apiErrorMessage(e))),
                            );
                          }
                        } finally {
                          if (mounted) setState(() => _placing = false);
                        }
                      },
              ),
              TextButton(
                onPressed: () => context.push('/wallet'),
                child: const Text('Top up wallet'),
              ),
            ],
          ),
        ),
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text(apiErrorMessage(e))),
      ),
    );
  }
}
