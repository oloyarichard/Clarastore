import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/api_client.dart';
import '../../providers/auth_provider.dart';
import '../../providers/order_provider.dart';
import '../../services/order_service.dart';
import '../../widgets/loading_button.dart';
import '../../widgets/order_status_badge.dart';

final _currency = NumberFormat.currency(locale: 'en_UG', symbol: 'UGX ', decimalDigits: 0);
final _dateFormat = DateFormat('d MMM yyyy, h:mm a');

class OrderDetailScreen extends ConsumerStatefulWidget {
  final int orderId;
  const OrderDetailScreen({super.key, required this.orderId});

  @override
  ConsumerState<OrderDetailScreen> createState() => _OrderDetailScreenState();
}

class _OrderDetailScreenState extends ConsumerState<OrderDetailScreen> {
  bool _updating = false;

  Future<void> _runAction(Future<void> Function() action) async {
    setState(() => _updating = true);
    try {
      await action();
      ref.invalidate(orderDetailProvider(widget.orderId));
      ref.read(orderListProvider.notifier).refresh();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(apiErrorMessage(e))));
      }
    } finally {
      if (mounted) setState(() => _updating = false);
    }
  }

  Future<void> _promptDispatch() async {
    final controller = TextEditingController();
    final result = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Dispatch via taxi/bus'),
        content: TextField(
          controller: controller,
          decoration: const InputDecoration(
            labelText: 'Transport reference',
            hintText: 'Route, taxi/bus, driver contact',
          ),
          maxLines: 2,
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
          ElevatedButton(
            onPressed: () => Navigator.pop(ctx, controller.text.trim()),
            child: const Text('Confirm dispatch'),
          ),
        ],
      ),
    );
    if (result != null && result.isNotEmpty) {
      _runAction(() => OrderService().markDispatched(widget.orderId, result));
    }
  }

  @override
  Widget build(BuildContext context) {
    final orderAsync = ref.watch(orderDetailProvider(widget.orderId));
    final user = ref.watch(authProvider).valueOrNull;

    return Scaffold(
      appBar: AppBar(title: Text('Order #${widget.orderId}')),
      body: orderAsync.when(
        data: (order) {
          final isCustomer = user != null && user.isCustomer;
          final isAgent = user != null && user.isAgent && order.assignedAgent == user.id;
          // A hub-direct order's district and hub are the same district;
          // a sub-district order forwards to a different hub.
          final isHubDirect = order.districtName != null && order.districtName == order.hubName;

          return SingleChildScrollView(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text('Placed ${_dateFormat.format(order.createdAt)}',
                        style: TextStyle(color: Colors.grey.shade600)),
                    OrderStatusBadge(status: order.status),
                  ],
                ),
                const SizedBox(height: 16),
                _infoRow('Delivery district', order.districtName ?? '—'),
                _infoRow('Hub', order.hubName ?? '—'),
                if (order.assignedAgentName != null) _infoRow('Agent', order.assignedAgentName!),
                if (order.transportReference.isNotEmpty)
                  _infoRow('Transport', order.transportReference),
                const Divider(height: 32),
                const Text('Items', style: TextStyle(fontWeight: FontWeight.w600)),
                const SizedBox(height: 8),
                ...order.items.map((item) => Padding(
                      padding: const EdgeInsets.symmetric(vertical: 4),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Expanded(child: Text('${item.productName} x${item.quantity}')),
                          Text(_currency.format(item.subtotal)),
                        ],
                      ),
                    )),
                const Divider(height: 32),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text('Total', style: TextStyle(fontWeight: FontWeight.bold)),
                    Text(_currency.format(order.totalAmount),
                        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                  ],
                ),
                const SizedBox(height: 32),

                // --- Customer actions ---
                if (isCustomer && order.canConfirmOrFlag) ...[
                  const Text('Has your order arrived?', style: TextStyle(fontWeight: FontWeight.w600)),
                  const SizedBox(height: 12),
                  LoadingButton(
                    label: 'Confirm received',
                    icon: Icons.check_circle_outline,
                    isLoading: _updating,
                    onPressed: () => _runAction(() => OrderService().confirmReceived(order.id)),
                  ),
                  const SizedBox(height: 8),
                  TextButton.icon(
                    onPressed: _updating
                        ? null
                        : () => _runAction(() => OrderService().reportNotReceived(order.id)),
                    icon: const Icon(Icons.error_outline, color: Colors.red),
                    label: const Text('Not received', style: TextStyle(color: Colors.red)),
                  ),
                ],

                // --- Agent actions ---
                if (isAgent && order.status == 'assigned')
                  LoadingButton(
                    label: 'Mark picked up',
                    icon: Icons.inventory_2_outlined,
                    isLoading: _updating,
                    onPressed: () => _runAction(() => OrderService().markPickedUp(order.id)),
                  ),
                if (isAgent && order.status == 'picked_up' && !isHubDirect)
                  LoadingButton(
                    label: 'Dispatch via taxi/bus',
                    icon: Icons.local_shipping_outlined,
                    isLoading: _updating,
                    onPressed: _promptDispatch,
                  ),
                if (isAgent && order.status == 'picked_up' && isHubDirect)
                  LoadingButton(
                    label: 'Mark delivered to customer',
                    icon: Icons.done_all,
                    isLoading: _updating,
                    onPressed: () => _runAction(
                      () => OrderService().updateStatus(orderId: order.id, status: 'awaiting_confirmation'),
                    ),
                  ),
              ],
            ),
          );
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Could not load order: ${apiErrorMessage(e)}')),
      ),
    );
  }

  Widget _infoRow(String label, String value) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 3),
        child: Row(
          children: [
            SizedBox(width: 120, child: Text(label, style: TextStyle(color: Colors.grey.shade600))),
            Expanded(child: Text(value, style: const TextStyle(fontWeight: FontWeight.w500))),
          ],
        ),
      );
}
