import 'package:dio/dio.dart';
import 'package:dio_cookie_manager/dio_cookie_manager.dart';
import 'package:cookie_jar/cookie_jar.dart';
import 'package:path_provider/path_provider.dart';

import 'constants.dart';
import 'token_storage.dart';

/// Thrown when a request fails after a refresh attempt too — callers
/// should treat this as "session expired, send the user to login".
class SessionExpiredException implements Exception {}

class ApiClient {
  ApiClient._internal() {
    _dio = Dio(BaseOptions(
      baseUrl: ApiConfig.baseUrl,
      connectTimeout: const Duration(seconds: 15),
      receiveTimeout: const Duration(seconds: 15),
      headers: {'Content-Type': 'application/json'},
    ));

    // The Django backend's guest cart relies on a session cookie
    // (request.session), not a bearer token — so browsing/cart actions
    // taken before signup only persist across requests if we carry that
    // cookie ourselves. A persistent cookie jar mirrors what a browser
    // does automatically, and survives app restarts so a guest's cart
    // isn't lost if they close the app before checking out.
    _initCookieJar();

    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        final token = await TokenStorage.getAccessToken();
        if (token != null) {
          options.headers['Authorization'] = 'Bearer $token';
        }
        handler.next(options);
      },
      onError: (DioException error, handler) async {
        // Only attempt a refresh once per failing request, and only on 401.
        final isUnauthorized = error.response?.statusCode == 401;
        final alreadyRetried = error.requestOptions.extra['retried'] == true;

        if (isUnauthorized && !alreadyRetried) {
          final refreshed = await _tryRefresh();
          if (refreshed) {
            final retryOptions = error.requestOptions;
            retryOptions.extra['retried'] = true;
            final token = await TokenStorage.getAccessToken();
            retryOptions.headers['Authorization'] = 'Bearer $token';
            try {
              final response = await _dio.fetch(retryOptions);
              return handler.resolve(response);
            } catch (_) {
              // fall through to reject below
            }
          } else {
            await TokenStorage.clearAuth();
            return handler.reject(DioException(
              requestOptions: error.requestOptions,
              error: SessionExpiredException(),
            ));
          }
        }
        handler.next(error);
      },
    ));
  }

  static final ApiClient instance = ApiClient._internal();
  late final Dio _dio;
  PersistCookieJar? _cookieJar;

  Dio get dio => _dio;

  Future<void> _initCookieJar() async {
    try {
      final dir = await getApplicationDocumentsDirectory();
      final jar = PersistCookieJar(storage: FileStorage('${dir.path}/.cookies/'));
      _cookieJar = jar;
      _dio.interceptors.insert(0, CookieManager(jar));
    } catch (_) {
      // Fall back silently (e.g. running in an environment without a
      // writable docs dir) — guest cart just won't persist across app
      // restarts in that case, checkout after login still works fine.
    }
  }

  /// Reads the Django `sessionid` cookie the guest cart was tracked under,
  /// so it can be passed to /cart/merge/ right after login/signup. Returns
  /// null if there's no active guest session yet (e.g. fresh install,
  /// no browsing done before signing up).
  Future<String?> getGuestSessionId() async {
    if (_cookieJar == null) return null;
    try {
      final cookies = await _cookieJar!.loadForRequest(Uri.parse(ApiConfig.baseUrl));
      final match = cookies.where((c) => c.name == 'sessionid');
      return match.isNotEmpty ? match.first.value : null;
    } catch (_) {
      return null;
    }
  }

  Future<bool> _tryRefresh() async {
    final refreshToken = await TokenStorage.getRefreshToken();
    if (refreshToken == null) return false;

    try {
      // Separate bare Dio instance — avoids recursing into this same
      // interceptor while refreshing.
      final plainDio = Dio(BaseOptions(baseUrl: ApiConfig.baseUrl));
      final response = await plainDio.post('/auth/refresh/', data: {'refresh': refreshToken});
      final newAccess = response.data['access'] as String;
      await TokenStorage.saveTokens(access: newAccess, refresh: refreshToken);
      return true;
    } catch (_) {
      return false;
    }
  }
}

/// Extracts a readable message from a DioException, preferring the
/// backend's own error/detail fields (DRF conventions) over generic text.
String apiErrorMessage(Object error) {
  if (error is SessionExpiredException) {
    return 'Your session expired — please log in again.';
  }
  if (error is DioException) {
    final data = error.response?.data;
    if (data is Map) {
      if (data['error'] != null) return data['error'].toString();
      if (data['detail'] != null) return data['detail'].toString();
      // DRF validation errors come back as {field: [messages]}
      final firstKey = data.keys.isNotEmpty ? data.keys.first : null;
      if (firstKey != null && data[firstKey] is List && (data[firstKey] as List).isNotEmpty) {
        return '$firstKey: ${(data[firstKey] as List).first}';
      }
    }
    if (error.type == DioExceptionType.connectionTimeout ||
        error.type == DioExceptionType.receiveTimeout) {
      return 'Connection timed out. Check your internet and try again.';
    }
    if (error.error is SessionExpiredException) {
      return 'Your session expired — please log in again.';
    }
    return 'Something went wrong. Please try again.';
  }
  return error.toString();
}
