#pragma once
#include <cstdint>

#include "pyinterp/detail/math.hpp"

namespace pyinterp::detail::math {

namespace window {

/// Known window functions.
enum Function : uint8_t {
  kBlackman,
  kBlackmanHarris,
  kFlatTop,
  kHamming,
  kLanczos,
  kNuttall,
  kParzen,
  kParzenSWOT,
};

/// Hamming window function.
template <typename T>
constexpr auto hamming(const T& d, const T& r) -> T {
  if (d <= r) {
    return 0.53836 - 0.46164 * std::cos(pi<T>() * (d + r) / r);
  }
  return T(0);
}

/// kBlackman window function.
template <typename T>
constexpr auto blackman(const T& d, const T& r) -> T {
  if (d <= r) {
    auto ratio = (d + r) / r;
    return (T(7938) / T(18608)) -
           (T(9240) / T(18608)) * std::cos(pi<T>() * ratio) +
           (T(1430) / T(18608)) * std::cos(two_pi<T>() * ratio);
  }
  return T(0);
}

/// Flat top window function.
template <typename T>
constexpr auto flat_top(const T& d, const T& r) -> T {
  if (d <= r) {
    auto ratio = (d + r) / r;
    return 0.21557895 - 0.41663158 * std::cos(pi<T>() * ratio) +
           0.277263158 * std::cos(two_pi<T>() * ratio) -
           0.083578947 * std::cos(3 * pi<T>() * ratio) +
           0.006947368 * std::cos(4 * pi<T>() * ratio);
  }
  return T(0);
}

/// Nuttall window function.
template <typename T>
constexpr auto nuttall(const T& d, const T& r) -> T {
  if (d <= r) {
    auto ratio = (d + r) / r;
    return 0.3635819 - 0.4891775 * std::cos(pi<T>() * ratio) +
           0.1365995 * std::cos(two_pi<T>() * ratio);
  }
  return T(0);
}

/// kBlackman-Harris window function.
template <typename T>
constexpr auto blackman_harris(const T& d, const T& r) -> T {
  if (d <= r) {
    auto ratio = (d + r) / r;
    return 0.35875 - 0.48829 * std::cos(pi<T>() * ratio) +
           0.14128 * std::cos(2 * pi<T>() * ratio) -
           0.01168 * std::cos(3 * pi<T>() * ratio);
  }
  return T(0);
}
/// Lanczos window function.
template <typename T>
constexpr auto lanczos(const T& d, const T& r) -> T {
  if (d <= r) {
    return sinc(2 * (d + r) / (2 * r) - 1);
  }
  return T(0);
}

// Parzen window function.
template <typename T>
constexpr auto parzen(const T& d, const T& r) -> T {
  auto ratio = d / r;
  auto l = 2 * r /* + sampling */;
  if (d <= l / 4) {
    return 1 - 6 * std::pow(ratio, 2) * (1 - ratio);
  }
  if (l / 2 <= r || d > l / 4) {
    return 2 * std::pow(1 - ratio, 3);
  }
  return T(0);
}

// A window similar to the Parzen window used for SWOT products.
template <typename T>
constexpr auto parzen_swot(const T& d, const T& r) -> T {
  auto l = 2 * r;
  auto ratio = (2 * d) / l;
  if (d <= l / 4) {
    return 1 - 6 * std::pow(ratio, 2) + 6 * std::pow(ratio, 3);
  }
  if (d <= l / 2 || d > l / 4) {
    return 2 * std::pow(1 - ratio, 3);
  }
  return T(0);
}

}  // namespace window

/// In signal processing and statistics, a window function (also known as
/// tapering function) is a mathematical function that is zero-valued outside of
/// some chosen interval, normally symmetric around the middle of the interval,
/// usually near a maximum in the middle, and usually tapering away from the
/// middle. Mathematically, when another function or waveform/data-sequence is
/// "multiplied" by a window function, the product is also zero-valued outside
/// the interval: all that is left is the part where they overlap, the "view
/// through the window"
template <typename T>
class WindowFunction {
 public:
  /// Pointer to the Window Function used.
  using PtrWindowFunction = T (*)(const T&, const T&);

  /// Default constructor
  ///
  /// @param function The window function to use.
  WindowFunction(const window::Function wf) {
    switch (wf) {
      case window::Function::kBlackman:
        function_ = &window::blackman;
        break;
      case window::Function::kBlackmanHarris:
        function_ = &window::blackman_harris;
        break;
      case window::Function::kFlatTop:
        function_ = &window::flat_top;
        break;
      case window::Function::kLanczos:
        function_ = &window::lanczos;
        break;
      case window::Function::kHamming:
        function_ = &window::hamming;
        break;
      case window::Function::kNuttall:
        function_ = &window::nuttall;
        break;
      case window::Function::kParzen:
        function_ = &window::parzen;
        break;
      case window::Function::kParzenSWOT:
        function_ = &window::parzen_swot;
        break;
      default:
        throw std::invalid_argument("Window function unknown: " +
                                    std::to_string(static_cast<int>(wf)));
    }
  }

  /// Apply the window function to the data.
  ///
  /// @param data The data to apply the window function to.
  /// @param r The radius of the window function.
  /// @return The windowed data.
  constexpr auto operator()(const T& data, const T& r) const -> T {
    return (this->function_)(data, r);
  }

 private:
  /// The window function to use.
  PtrWindowFunction function_;
};

}  // namespace pyinterp::detail::math