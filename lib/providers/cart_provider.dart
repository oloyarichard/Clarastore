import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/cart_item.dart';
import '../services/cart_service.dart';

final cartServiceProvider = Provider((ref) => CartService());

class CartNotifier extends AsyncNotifier<Cart> {
  @override
  Future<Cart> build() async {
    return ref.read(cartServiceProvider).getCart();
  }

  Future<void> refresh() async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(() => ref.read(cartServiceProvider).getCart());
  }

  Future<void> addItem(int productId, {int quantity = 1}) async {
    await ref.read(cartServiceProvider).addItem(productId: productId, quantity: quantity);
    await refresh();
  }

  Future<void> updateQuantity(int itemId, int quantity) async {
    await ref.read(cartServiceProvider).updateQuantity(itemId: itemId, quantity: quantity);
    await refresh();
  }

  Future<void> removeItem(int itemId) async {
    await ref.read(cartServiceProvider).removeItem(itemId);
    await refresh();
  }

  Future<void> clear() async {
    await ref.read(cartServiceProvider).clearCart();
    await refresh();
  }
}

final cartProvider = AsyncNotifierProvider<CartNotifier, Cart>(CartNotifier.new);
