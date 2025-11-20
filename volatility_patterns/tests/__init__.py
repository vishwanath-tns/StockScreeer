"""
Tests Module for VCP Detection System
====================================

Comprehensive testing suite for all VCP components:
- Unit tests for data service
- VCP detection algorithm tests
- Technical indicator validation
- Performance and accuracy tests
"""

# Test configuration
TEST_SYMBOLS = ['RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK']
TEST_DATE_RANGE = ('2024-01-01', '2024-12-31')
PERFORMANCE_THRESHOLD_SECONDS = 2  # Max time for 6-month data fetch

__all__ = ['TEST_SYMBOLS', 'TEST_DATE_RANGE', 'PERFORMANCE_THRESHOLD_SECONDS']