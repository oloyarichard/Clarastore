import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/wallet.dart';
import '../services/wallet_service.dart';

final walletServiceProvider = Provider((ref) => WalletService());

class WalletNotifier extends AsyncNotifier<Wallet> {
  @override
  Future<Wallet> build() async {
    return ref.read(walletServiceProvider).getWallet();
  }

  Future<void> refresh() async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(() => ref.read(walletServiceProvider).getWallet());
  }
}

final walletProvider = AsyncNotifierProvider<WalletNotifier, Wallet>(WalletNotifier.new);

final walletTransactionsProvider = FutureProvider.autoDispose<List<WalletTransaction>>((ref) async {
  return ref.read(walletServiceProvider).getTransactions();
});

final agentCommissionsProvider = FutureProvider.autoDispose<List<AgentCommission>>((ref) async {
  return ref.read(walletServiceProvider).getCommissions();
});

/// Drives the "check your phone" top-up flow: starts a request, then polls
/// status every few seconds until it's no longer pending (or times out).
class TopUpFlowNotifier extends StateNotifier<AsyncValue<TopUpRequest?>> {
  TopUpFlowNotifier(this._ref) : super(const AsyncValue.data(null));

  final Ref _ref;
  Timer? _pollTimer;

  Future<void> start({required double amount, required String phoneNumber, String? provider}) async {
    state = const AsyncValue.loading();
    try {
      final request = await _ref
          .read(walletServiceProvider)
          .initiateTopUp(amount: amount, phoneNumber: phoneNumber, provider: provider);
      state = AsyncValue.data(request);
      _startPolling(request.id);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  void _startPolling(int requestId) {
    _pollTimer?.cancel();
    var attempts = 0;
    _pollTimer = Timer.periodic(const Duration(seconds: 4), (timer) async {
      attempts++;
      try {
        final updated = await _ref.read(walletServiceProvider).checkTopUpStatus(requestId);
        state = AsyncValue.data(updated);
        if (updated.status != 'pending' || attempts >= 30) {
          // stop once resolved, or after ~2 minutes of polling
          timer.cancel();
          if (updated.status == 'successful') {
            _ref.read(walletProvider.notifier).refresh();
          }
        }
      } catch (_) {
        // transient network error while polling — keep trying until the cap
      }
    });
  }

  void reset() {
    _pollTimer?.cancel();
    state = const AsyncValue.data(null);
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }
}

final topUpFlowProvider =
    StateNotifierProvider<TopUpFlowNotifier, AsyncValue<TopUpRequest?>>((ref) => TopUpFlowNotifier(ref));
