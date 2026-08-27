import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../core/api_client.dart';
import '../../providers/order_provider.dart';
import '../../widgets/order_status_badge.dart';
import '../../core/constants.dart';

final _currency = NumberFormat.currency(locale: 'en_UG', symbol: 'UGX ', decimalDigits: 0);
final _dateFormat = DateFormat('d MMM, h:mm a');

class OrdersScreen extends ConsumerWidget {
  const OrdersScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final ordersAsync = ref.watch(orderListProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('My Orders')),
      body: RefreshIndicator(
        onRefresh: () => ref.read(orderListProvider.notifier).refresh(),
        child: ordersAsync.when(
          data: (orders) {
            if (orders.isEmpty) {
              return ListView(
                children: const [
                  SizedBox(height: 120),
                  Center(child: Text('No orders yet.')),
                ],
              );
            }
            return ListView.separated(
              padding: const EdgeInsets.all(16),
              itemCount: orders.length,
              separatorBuilder: (_, __) => const SizedBox(height: 12),
              itemBuilder: (context, index) {
                final order = orders[index];
                return Card(
                  elevation: 0,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                    side: const BorderSide(color: AppTheme.line),
                  ),
                  child: ListTile(
                    onTap: () => context.push('/orders/${order.id}'),
                    title: Text('Order #${order.id}', style: const TextStyle(fontWeight: FontWeight.w600)),
                    subtitle: Text(
                      '${order.itemsCount ?? order.items.length} item(s) · ${_currency.format(order.totalAmount)}\n${_dateFormat.format(order.createdAt)}',
                    ),
                    isThreeLine: true,
                    trailing: OrderStatusBadge(status: order.status),
                  ),
                );
              },
            );
          },
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (e, _) => Center(child: Text('Could not load orders: ${apiErrorMessage(e)}')),
        ),
      ),
    );
  }
}
