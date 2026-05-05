# TypeScript SDK Tests

This directory contains comprehensive test cases for the ExosphereHost TypeScript SDK, mirroring the test coverage of the Python SDK.

## Test Structure

The tests are organized to match the Python SDK test structure with one-to-one mappings:

### BaseNode Tests

- `test_base_node_abstract.test.ts` - Tests for abstract BaseNode functionality
- `test_base_node_comprehensive.test.ts` - Comprehensive BaseNode tests including edge cases
- `test_base_node.test.ts` - Basic BaseNode functionality tests

### Runtime Tests

- `test_runtime_comprehensive.test.ts` - Comprehensive runtime tests
- `test_runtime_edge_cases.test.ts` - Edge cases and error handling
- `test_runtime_validation.test.ts` - Runtime validation tests

### StateManager Tests

- `test_statemanager_comprehensive.test.ts` - Comprehensive StateManager tests

### Integration Tests

- `test_integration.test.ts` - End-to-end integration tests
- `test_signals_and_runtime_functions.test.ts` - Signal handling and runtime functions
- `test_coverage_additions.test.ts` - Additional coverage tests

### Package Tests

- `test_package_init.test.ts` - Package initialization and exports
- `test_models_and_statemanager_new.test.ts` - Model validation tests
- `test_version.test.ts` - Version handling tests

## Running Tests

```bash
# Run all tests
npm test

# Run tests with coverage
npm run test:coverage

# Run tests once (no watch mode)
npm run test:run
```

## Test Framework

The tests use [Vitest](https://vitest.dev/) as the testing framework, which provides:

- Fast test execution
- Built-in TypeScript support
- Coverage reporting
- Mocking capabilities
- Watch mode for development

## Test Coverage

The test suite provides comprehensive coverage including:

- ✅ BaseNode abstract class functionality
- ✅ Runtime initialization and configuration
- ✅ Runtime worker execution
- ✅ StateManager operations
- ✅ Signal handling (PruneSignal, ReQueueAfterSignal)
- ✅ Model validation
- ✅ Error handling and edge cases
- ✅ Integration scenarios
- ✅ Package exports and initialization

## Mocking

Tests use `vi.fn()` and `global.fetch` mocking to simulate HTTP requests and external dependencies, ensuring tests run in isolation without requiring actual external services.

## Environment Variables

Tests set up required environment variables:

- `EXOSPHERE_STATE_MANAGER_URI`
- `EXOSPHERE_API_KEY`

These are automatically configured in test setup and cleaned up between tests.
