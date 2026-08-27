import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/token_storage.dart';
import '../models/user.dart';
import '../services/auth_service.dart';
import '../services/cart_service.dart';

final authServiceProvider = Provider((ref) => AuthService());

/// Holds the current logged-in user, or null if signed out / guest.
/// AsyncValue so the UI can show a loading state while we check for an
/// existing session on app start (auto-login from stored tokens).
class AuthNotifier extends AsyncNotifier<AppUser?> {
  @override
  Future<AppUser?> build() async {
    final hasSession = await TokenStorage.hasValidSession();
    if (!hasSession) return null;
    try {
      return await ref.read(authServiceProvider).getProfile();
    } catch (_) {
      // Stored token is stale/invalid — treat as signed out.
      await TokenStorage.clearAuth();
      return null;
    }
  }

  Future<void> login({required String email, required String password}) async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(() async {
      final user = await ref.read(authServiceProvider).login(email: email, password: password);
      // Merge whatever the guest added to their cart before signing in.
      await CartService().mergeGuestCartIfAny();
      return user;
    });
  }

  Future<void> register({
    required String email,
    required String password,
    required String passwordConfirm,
    required String firstName,
    required String lastName,
    required String phone,
    required int districtId,
  }) async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(() async {
      await ref.read(authServiceProvider).register(
            email: email,
            password: password,
            passwordConfirm: passwordConfirm,
            firstName: firstName,
            lastName: lastName,
            phone: phone,
            districtId: districtId,
          );
      // Registration doesn't log the user in automatically on the backend
      // — log in right after so the flow feels seamless.
      final user = await ref.read(authServiceProvider).login(email: email, password: password);
      await CartService().mergeGuestCartIfAny();
      return user;
    });
  }

  Future<void> logout() async {
    await ref.read(authServiceProvider).logout();
    state = const AsyncValue.data(null);
  }

  Future<void> refreshProfile() async {
    final user = await ref.read(authServiceProvider).getProfile();
    state = AsyncValue.data(user);
  }
}

final authProvider = AsyncNotifierProvider<AuthNotifier, AppUser?>(AuthNotifier.new);

final districtsProvider = FutureProvider<List<District>>((ref) async {
  return ref.read(authServiceProvider).getDistricts();
});
