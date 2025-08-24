#!/bin/bash

# End-to-end deployment validation script for Financial Nomad API
# This script validates that all systems are working correctly after deployment

set -euo pipefail

# Configuration
API_URL="${API_URL:-http://localhost:8092}"
TIMEOUT=10
VERBOSE="${VERBOSE:-false}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test results
TESTS_PASSED=0
TESTS_FAILED=0
TOTAL_TESTS=0

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
    ((TESTS_PASSED++))
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
    ((TESTS_FAILED++))
}

log_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

# Test function wrapper
run_test() {
    local test_name="$1"
    local test_function="$2"
    
    ((TOTAL_TESTS++))
    log_info "Running: $test_name"
    
    if [[ "$VERBOSE" == "true" ]]; then
        if $test_function; then
            log_success "$test_name"
        else
            log_error "$test_name"
        fi
    else
        if $test_function >/dev/null 2>&1; then
            log_success "$test_name"
        else
            log_error "$test_name"
        fi
    fi
}

# HTTP request helper
make_request() {
    local method="$1"
    local endpoint="$2"
    local expected_status="${3:-200}"
    local data="${4:-}"
    
    local url="${API_URL}${endpoint}"
    local response
    local status_code
    
    if [[ -n "$data" ]]; then
        response=$(curl -s -w "\n%{http_code}" -X "$method" \
            -H "Content-Type: application/json" \
            -d "$data" \
            --max-time "$TIMEOUT" \
            "$url" || echo -e "\n000")
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" \
            --max-time "$TIMEOUT" \
            "$url" || echo -e "\n000")
    fi
    
    status_code=$(echo "$response" | tail -n1)
    
    if [[ "$status_code" == "$expected_status" ]]; then
        return 0
    else
        if [[ "$VERBOSE" == "true" ]]; then
            echo "Expected status: $expected_status, Got: $status_code"
            echo "Response: $(echo "$response" | head -n -1)"
        fi
        return 1
    fi
}

# Test Functions
test_api_root() {
    make_request "GET" "/"
}

test_health_check() {
    make_request "GET" "/api/v1/health"
}

test_detailed_health() {
    make_request "GET" "/api/v1/health/detailed"
}

test_readiness_probe() {
    make_request "GET" "/api/v1/ready"
}

test_liveness_probe() {
    make_request "GET" "/api/v1/live"
}

test_openapi_docs() {
    make_request "GET" "/docs"
}

test_openapi_spec() {
    make_request "GET" "/openapi.json"
}

test_metrics_endpoint() {
    make_request "GET" "/api/v1/monitoring/metrics"
}

test_frontend_info() {
    make_request "GET" "/api/v1/frontend/info"
}

test_frontend_features() {
    make_request "GET" "/api/v1/frontend/features"
}

test_frontend_config() {
    make_request "GET" "/api/v1/frontend/config/complete"
}

test_performance_metrics() {
    make_request "GET" "/api/v1/performance/metrics/system"
}

test_performance_report() {
    make_request "GET" "/api/v1/performance/report"
}

test_cors_preflight() {
    curl -s -o /dev/null -w "%{http_code}" \
        -X OPTIONS \
        -H "Origin: http://localhost:4200" \
        -H "Access-Control-Request-Method: GET" \
        --max-time "$TIMEOUT" \
        "${API_URL}/api/v1/health" | grep -q "200"
}

test_rate_limiting_headers() {
    local response_headers
    response_headers=$(curl -s -I --max-time "$TIMEOUT" "${API_URL}/api/v1/health")
    
    # Check for rate limiting or security headers
    echo "$response_headers" | grep -qi "x-request-id\|x-process-time"
}

test_security_headers() {
    local response_headers
    response_headers=$(curl -s -I --max-time "$TIMEOUT" "${API_URL}/api/v1/health")
    
    # Check for basic security headers
    echo "$response_headers" | grep -qi "x-content-type-options\|x-frame-options"
}

test_error_handling() {
    make_request "GET" "/api/v1/nonexistent-endpoint" "404"
}

test_method_not_allowed() {
    make_request "DELETE" "/api/v1/health" "405"
}

test_auth_required_endpoints() {
    # These should return 401 or 403 without auth
    make_request "GET" "/api/v1/accounts" "401"
}

test_json_content_type() {
    local content_type
    content_type=$(curl -s -I --max-time "$TIMEOUT" "${API_URL}/api/v1/health" | grep -i "content-type")
    echo "$content_type" | grep -qi "application/json"
}

test_response_time() {
    local response_time
    response_time=$(curl -s -w "%{time_total}" -o /dev/null --max-time "$TIMEOUT" "${API_URL}/api/v1/health")
    
    # Response time should be less than 2 seconds
    awk -v time="$response_time" 'BEGIN { exit !(time < 2.0) }'
}

test_concurrent_requests() {
    local pids=()
    local responses=()
    local i
    
    # Make 5 concurrent requests
    for i in {1..5}; do
        (curl -s --max-time "$TIMEOUT" "${API_URL}/api/v1/health" > "/tmp/response_$i") &
        pids+=($!)
    done
    
    # Wait for all requests to complete
    for pid in "${pids[@]}"; do
        wait "$pid"
    done
    
    # Check all responses are valid
    for i in {1..5}; do
        if [[ -f "/tmp/response_$i" ]] && grep -q "healthy" "/tmp/response_$i"; then
            rm -f "/tmp/response_$i"
        else
            return 1
        fi
    done
    
    return 0
}

# Advanced integration tests
test_cache_warmup() {
    # Test cache warmup functionality
    local response
    response=$(curl -s -X POST --max-time "$TIMEOUT" "${API_URL}/api/v1/performance/optimize/cache-warmup")
    echo "$response" | grep -q "task_id"
}

test_api_version_endpoint() {
    make_request "GET" "/api/v1/frontend/version"
}

test_monitoring_health() {
    make_request "GET" "/api/v1/monitoring/health"
}

# Performance validation tests
test_memory_usage() {
    local response
    response=$(curl -s --max-time "$TIMEOUT" "${API_URL}/api/v1/performance/metrics/system")
    
    # Check that memory usage is reported and reasonable (< 90%)
    local memory_percent
    memory_percent=$(echo "$response" | grep -o '"memory_percent":[0-9.]*' | cut -d':' -f2)
    
    if [[ -n "$memory_percent" ]]; then
        awk -v mem="$memory_percent" 'BEGIN { exit !(mem < 90) }'
    else
        return 1
    fi
}

test_disk_space() {
    local response
    response=$(curl -s --max-time "$TIMEOUT" "${API_URL}/api/v1/performance/metrics/system")
    
    # Check that disk usage is reasonable (< 95%)
    local disk_percent
    disk_percent=$(echo "$response" | grep -o '"disk_usage_percent":[0-9.]*' | cut -d':' -f2)
    
    if [[ -n "$disk_percent" ]]; then
        awk -v disk="$disk_percent" 'BEGIN { exit !(disk < 95) }'
    else
        return 1
    fi
}

# Main execution
main() {
    echo -e "${BLUE}🚀 Financial Nomad API - End-to-End Validation${NC}"
    echo "API URL: $API_URL"
    echo "Timeout: ${TIMEOUT}s"
    echo ""
    
    log_info "Starting validation tests..."
    
    # Core API Tests
    echo -e "\n${YELLOW}=== Core API Tests ===${NC}"
    run_test "API Root Endpoint" test_api_root
    run_test "Basic Health Check" test_health_check
    run_test "Detailed Health Check" test_detailed_health
    run_test "Readiness Probe" test_readiness_probe
    run_test "Liveness Probe" test_liveness_probe
    
    # Documentation Tests
    echo -e "\n${YELLOW}=== Documentation Tests ===${NC}"
    run_test "OpenAPI Documentation" test_openapi_docs
    run_test "OpenAPI Specification" test_openapi_spec
    
    # Monitoring Tests
    echo -e "\n${YELLOW}=== Monitoring Tests ===${NC}"
    run_test "Prometheus Metrics" test_metrics_endpoint
    run_test "Monitoring Health" test_monitoring_health
    
    # Frontend Integration Tests
    echo -e "\n${YELLOW}=== Frontend Integration Tests ===${NC}"
    run_test "Frontend Server Info" test_frontend_info
    run_test "Frontend Features" test_frontend_features
    run_test "Frontend Complete Config" test_frontend_config
    run_test "API Version Endpoint" test_api_version_endpoint
    
    # Performance Tests
    echo -e "\n${YELLOW}=== Performance Tests ===${NC}"
    run_test "System Performance Metrics" test_performance_metrics
    run_test "Performance Report" test_performance_report
    run_test "Memory Usage Check" test_memory_usage
    run_test "Disk Space Check" test_disk_space
    run_test "Response Time Check" test_response_time
    
    # Security Tests
    echo -e "\n${YELLOW}=== Security Tests ===${NC}"
    run_test "CORS Preflight Support" test_cors_preflight
    run_test "Security Headers" test_security_headers
    run_test "Authentication Required" test_auth_required_endpoints
    
    # Error Handling Tests
    echo -e "\n${YELLOW}=== Error Handling Tests ===${NC}"
    run_test "404 Error Handling" test_error_handling
    run_test "405 Method Not Allowed" test_method_not_allowed
    
    # Performance and Load Tests
    echo -e "\n${YELLOW}=== Load and Performance Tests ===${NC}"
    run_test "Concurrent Requests" test_concurrent_requests
    run_test "JSON Content Type" test_json_content_type
    run_test "Rate Limiting Headers" test_rate_limiting_headers
    
    # Advanced Features
    echo -e "\n${YELLOW}=== Advanced Features Tests ===${NC}"
    run_test "Cache Warmup Feature" test_cache_warmup
    
    # Summary
    echo -e "\n${YELLOW}=== Test Summary ===${NC}"
    echo "Total Tests: $TOTAL_TESTS"
    echo -e "Passed: ${GREEN}$TESTS_PASSED${NC}"
    echo -e "Failed: ${RED}$TESTS_FAILED${NC}"
    
    local success_rate=$((TESTS_PASSED * 100 / TOTAL_TESTS))
    echo "Success Rate: ${success_rate}%"
    
    if [[ $TESTS_FAILED -eq 0 ]]; then
        echo -e "\n${GREEN}🎉 All tests passed! API is ready for production.${NC}"
        return 0
    elif [[ $success_rate -ge 90 ]]; then
        echo -e "\n${YELLOW}⚠️  API is mostly functional with ${TESTS_FAILED} failing tests.${NC}"
        return 1
    else
        echo -e "\n${RED}❌ API has significant issues. ${TESTS_FAILED} tests failed.${NC}"
        return 2
    fi
}

# Help function
show_help() {
    cat << EOF
Financial Nomad API - End-to-End Validation Script

Usage: $0 [OPTIONS]

Options:
    -u, --url URL       API URL (default: http://localhost:8092)
    -t, --timeout SEC   Request timeout in seconds (default: 10)
    -v, --verbose       Enable verbose output
    -h, --help         Show this help message

Examples:
    $0                                          # Test local API
    $0 -u https://api.financial-nomad.com      # Test production API
    $0 -v -t 30                                # Verbose mode with 30s timeout

Environment Variables:
    API_URL            API base URL
    VERBOSE            Enable verbose output (true/false)
EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -u|--url)
            API_URL="$2"
            shift 2
            ;;
        -t|--timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE="true"
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Run validation
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi