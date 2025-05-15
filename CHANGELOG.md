# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.2.0] - 2025-05-15

### Core Features
* Introduced a stable integration mechanism from Pydantic to `immutables.Map`
* Fully implemented an Action pooling system to enhance performance when reusing the same Action frequently
* Established an immutable state container infrastructure that automatically converts mutable data into immutable forms
* Complete support for ReactiveX (RxPy) reactive data streams

### Added
* Utility functions: `to_immutable`, `to_dict`, and `to_pydantic` for easy conversion between Pydantic models and `immutables.Map`
* Tool functions `update_in` and `batch_update` for efficient deep updates and batch updates
* A comprehensive middleware suite:

  * `LoggerMiddleware`: logs state changes
  * `ThunkMiddleware`: supports dispatching functions
  * `AwaitableMiddleware`: supports dispatching coroutines
  * `ErrorMiddleware`: unified error handling
  * `ImmutableEnforceMiddleware`: enforces immutability
  * `PersistMiddleware`: state persistence
  * `DevToolsMiddleware`: developer tools support
  * `PerformanceMonitorMiddleware`: performance monitoring
  * `DebounceMiddleware`: debounce handling
  * `BatchMiddleware`: batch processing
  * `AnalyticsMiddleware`: user behavior analytics

### Changed
* Used `immutables.Map` to implement fully immutable Action objects
* Action object pooling significantly reduced memory usage and creation overhead
* Improved effect registration and management, now supporting module-level lifecycle management
* Optimized selector memoization with deep equality checks and TTL caching strategies
* Enhanced error handling system to provide structured error reports

### Architecture
* Strict adherence to the NgRx/Redux architectural patterns for unified state management flows
* Modular design with clear separation of concerns
* A full middleware architecture that supports extensible workflows
* `.pyi` stub files provide precise type hints

### Developer Experience
* Out-of-the-box middleware options reduce boilerplate code
* Detailed documentation and comments in English and Chinese for the Chinese-speaking community
* Complete example projects, including a counter and demo for detection
* A more concise API design to minimize boilerplate

### Fixed
* Resolved edge-case immutability guarantee issues

### Deprecated
- Removed `*.ipy` files as they are no longer needed; `.py` files now provide type hints and detailed comments.

## [0.1.8] - 2025-04-19

### Added
* Introduced the `StoreModule` class with static methods for dynamic feature module registration and deregistration

### Changed
* Improved type annotations for action creators to support more robust systems
* Enhanced effect registration mechanism with better error handling and logging
* Optimized middleware pipeline processing for improved performance
* Updated documentation and examples with additional Chinese explanations

### Fixed
* Fixed middleware errors occurring with specific actions
* Resolved potential memory leak issues during effect registration
