import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/order.dart';
import '../services/order_service.dart';

final orderServiceProvider = Provider((ref) => OrderService());

/// The backend scopes this automatically by role: a customer sees their own
/// orders, an agent sees only orders assigned to them, admin sees all.
class OrderListNotifier extends AsyncNotifier<List<Order>> {
  @override
  Future<List<Order>> build() async {
    return ref.read(orderServiceProvider).listOrders();
  }

  Future<void> refresh() async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(() => ref.read(orderServiceProvider).listOrders());
  }
}

final orderListProvider = AsyncNotifierProvider<OrderListNotifier, List<Order>>(OrderListNotifier.new);

final orderDetailProvider = FutureProvider.family<Order, int>((ref, id) async {
  return ref.read(orderServiceProvider).getOrder(id);
});

final flaggedOrdersProvider = FutureProvider<List<Order>>((ref) async {
  return ref.read(orderServiceProvider).listFlaggedOrders();
});
