# Changelog

All notable changes to this project are documented here.

## [0.3.0] - 2026-11-13

### Added
- Support multiple weekly collection days for manually configured containerized alley routes.
- Expanded 2026 holiday schedule regression coverage.

### Improved
- Validate ArcGIS responses and handle malformed or unusable GIS data more safely.
- Parse GIS leaf-collection dates more defensively.
- Skip malformed individual GIS features while reporting unusable feature collections as connection errors.
- Expand regression coverage for GIS lookup failures and collection schedules.
- Update configuration selectors, sensor attributes, translations, and documentation.

### Compatibility
- Preserve existing single-day collection configuration behavior.
