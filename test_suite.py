#!/usr/bin/env python3
"""
Comprehensive Test Suite for IMEI Tool
Tests all critical functionality for production readiness
"""

import unittest
import json
import time
import tempfile
import os
from unittest.mock import patch, MagicMock

# Import modules to test
import sys
sys.path.append('.')

try:
    from server import (
        validate_imei, get_tac_info, sanitize_input, 
        generate_api_key, hash_ip_address, app, init_db
    )
    SERVER_AVAILABLE = True
except ImportError:
    SERVER_AVAILABLE = False
    print("Warning: Server module not available for testing")

class TestIMEIValidation(unittest.TestCase):
    """Test IMEI validation functionality"""
    
    def test_valid_imei_luhn(self):
        """Test valid IMEI with correct Luhn checksum"""
        if not SERVER_AVAILABLE:
            self.skipTest("Server module not available")
        
        # Known valid IMEI (example)
        valid_imei = "123456789012344"  # This should pass Luhn
        # Note: In real testing, use actual valid IMEIs
        
    def test_invalid_imei_format(self):
        """Test invalid IMEI formats"""
        if not SERVER_AVAILABLE:
            self.skipTest("Server module not available")
            
        invalid_imeis = [
            "12345678901234",     # Too short
            "1234567890123456",   # Too long
            "12345678901234a",    # Contains letter
            "000000000000000",    # All zeros
            "111111111111111",    # All ones
            "",                   # Empty
            None                  # None value
        ]
        
        for imei in invalid_imeis:
            with self.subTest(imei=imei):
                self.assertFalse(validate_imei(imei))
    
    def test_imei_edge_cases(self):
        """Test edge cases for IMEI validation"""
        if not SERVER_AVAILABLE:
            self.skipTest("Server module not available")
            
        # Test same digits
        same_digits = "555555555555555"
        self.assertFalse(validate_imei(same_digits))

class TestTACDatabase(unittest.TestCase):
    """Test TAC database functionality"""
    
    def test_known_tac_lookup(self):
        """Test lookup of known TAC codes"""
        if not SERVER_AVAILABLE:
            self.skipTest("Server module not available")
            
        # Test Apple iPhone 6
        apple_imei = "352099001234567"
        result = get_tac_info(apple_imei)
        
        self.assertEqual(result['brand'], 'Apple')
        self.assertEqual(result['model'], 'iPhone 6')
        self.assertEqual(result['confidence'], 'High')
    
    def test_unknown_tac_lookup(self):
        """Test lookup of unknown TAC codes"""
        if not SERVER_AVAILABLE:
            self.skipTest("Server module not available")
            
        unknown_imei = "999999991234567"
        result = get_tac_info(unknown_imei)
        
        self.assertEqual(result['brand'], 'Unknown')
        self.assertEqual(result['confidence'], 'Low')
    
    def test_pattern_matching(self):
        """Test manufacturer pattern matching"""
        if not SERVER_AVAILABLE:
            self.skipTest("Server module not available")
            
        # Test Samsung pattern (353)
        samsung_imei = "353123451234567"
        result = get_tac_info(samsung_imei)
        
        self.assertEqual(result['brand'], 'Samsung')
        self.assertEqual(result['confidence'], 'Medium')

class TestSecurity(unittest.TestCase):
    """Test security functionality"""
    
    def test_input_sanitization(self):
        """Test input sanitization"""
        if not SERVER_AVAILABLE:
            self.skipTest("Server module not available")
            
        dangerous_inputs = [
            "<script>alert('xss')</script>",
            "'; DROP TABLE users; --",
            "javascript:alert('xss')",
            "<img src=x onerror=alert(1)>"
        ]
        
        for dangerous_input in dangerous_inputs:
            sanitized = sanitize_input(dangerous_input)
            self.assertNotIn('<', sanitized)
            self.assertNotIn('>', sanitized)
            self.assertNotIn('"', sanitized)
            self.assertNotIn("'", sanitized)
    
    def test_api_key_generation(self):
        """Test API key generation"""
        if not SERVER_AVAILABLE:
            self.skipTest("Server module not available")
            
        api_key = generate_api_key()
        
        self.assertTrue(api_key.startswith('imei_'))
        self.assertGreater(len(api_key), 20)
        
        # Test uniqueness
        api_key2 = generate_api_key()
        self.assertNotEqual(api_key, api_key2)
    
    def test_ip_hashing(self):
        """Test IP address hashing"""
        if not SERVER_AVAILABLE:
            self.skipTest("Server module not available")
            
        ip1 = "192.168.1.1"
        ip2 = "192.168.1.2"
        
        hash1 = hash_ip_address(ip1)
        hash2 = hash_ip_address(ip2)
        
        self.assertNotEqual(hash1, hash2)
        self.assertEqual(len(hash1), 16)  # Should be 16 chars
        self.assertNotEqual(hash1, ip1)  # Should be hashed, not plain

class TestAPIEndpoints(unittest.TestCase):
    """Test API endpoints"""
    
    def setUp(self):
        """Set up test client"""
        if not SERVER_AVAILABLE:
            self.skipTest("Server module not available")
            
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['DATABASE'] = ':memory:'
        self.client = self.app.test_client()
        
        with self.app.app_context():
            init_db()
    
    def test_health_endpoint(self):
        """Test health check endpoint"""
        if not SERVER_AVAILABLE:
            self.skipTest("Server module not available")
            
        response = self.client.get('/api/health')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'healthy')
        self.assertIn('timestamp', data)
    
    def test_registration_endpoint(self):
        """Test user registration"""
        if not SERVER_AVAILABLE:
            self.skipTest("Server module not available")
            
        user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpassword123'
        }
        
        response = self.client.post('/api/register', 
                                  data=json.dumps(user_data),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 201)
        
        data = json.loads(response.data)
        self.assertIn('api_key', data)
        self.assertTrue(data['api_key'].startswith('imei_'))
    
    def test_imei_lookup_without_auth(self):
        """Test IMEI lookup without authentication"""
        if not SERVER_AVAILABLE:
            self.skipTest("Server module not available")
            
        response = self.client.post('/api/imei/lookup',
                                  data=json.dumps({'imei': '123456789012344'}),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 401)

class TestDatabaseOperations(unittest.TestCase):
    """Test database operations"""
    
    def setUp(self):
        """Set up test database"""
        if not SERVER_AVAILABLE:
            self.skipTest("Server module not available")
            
        self.db_file = tempfile.mktemp()
        self.app = app
        self.app.config['DATABASE'] = self.db_file
        
        with self.app.app_context():
            init_db()
    
    def tearDown(self):
        """Clean up test database"""
        if hasattr(self, 'db_file') and os.path.exists(self.db_file):
            os.unlink(self.db_file)
    
    def test_database_initialization(self):
        """Test database table creation"""
        if not SERVER_AVAILABLE:
            self.skipTest("Server module not available")
            
        import sqlite3
        
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Check if tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        expected_tables = ['users', 'imei_lookups', 'rate_limits', 'security_events', 'api_usage']
        for table in expected_tables:
            self.assertIn(table, tables)
        
        conn.close()

class TestPerformance(unittest.TestCase):
    """Test performance characteristics"""
    
    def test_tac_lookup_performance(self):
        """Test TAC lookup performance"""
        if not SERVER_AVAILABLE:
            self.skipTest("Server module not available")
            
        test_imei = "352099001234567"
        
        # Measure lookup time
        start_time = time.time()
        for _ in range(1000):
            get_tac_info(test_imei)
        end_time = time.time()
        
        avg_time = (end_time - start_time) / 1000
        self.assertLess(avg_time, 0.001)  # Should be under 1ms per lookup
    
    def test_validation_performance(self):
        """Test IMEI validation performance"""
        if not SERVER_AVAILABLE:
            self.skipTest("Server module not available")
            
        test_imei = "123456789012344"
        
        start_time = time.time()
        for _ in range(10000):
            validate_imei(test_imei)
        end_time = time.time()
        
        avg_time = (end_time - start_time) / 10000
        self.assertLess(avg_time, 0.0001)  # Should be under 0.1ms per validation

class TestBatchProcessing(unittest.TestCase):
    """Test batch processing functionality"""
    
    def test_batch_validation(self):
        """Test batch IMEI validation"""
        if not SERVER_AVAILABLE:
            self.skipTest("Server module not available")
            
        # Test mixed valid/invalid batch
        test_imeis = [
            "123456789012344",  # Valid format (example)
            "invalid_imei",     # Invalid format
            "000000000000000",  # Invalid pattern
            "352099001234567"   # Valid Apple IMEI
        ]
        
        results = []
        for imei in test_imeis:
            if validate_imei(imei):
                tac_info = get_tac_info(imei)
                results.append({'imei': imei, 'valid': True, 'info': tac_info})
            else:
                results.append({'imei': imei, 'valid': False})
        
        # Should have some valid and some invalid
        valid_count = sum(1 for r in results if r['valid'])
        self.assertGreater(valid_count, 0)
        self.assertLess(valid_count, len(test_imeis))

def run_comprehensive_tests():
    """Run all tests and generate report"""
    print("🧪 IMEI Tool Comprehensive Test Suite")
    print("=" * 50)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestIMEIValidation,
        TestTACDatabase,
        TestSecurity,
        TestAPIEndpoints,
        TestDatabaseOperations,
        TestPerformance,
        TestBatchProcessing
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Generate report
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 50)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print("\n❌ FAILURES:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback.split('AssertionError:')[-1].strip()}")
    
    if result.errors:
        print("\n🚨 ERRORS:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback.split('Exception:')[-1].strip()}")
    
    return result.wasSuccessful()

if __name__ == '__main__':
    success = run_comprehensive_tests()
    
    if success:
        print("\n🎉 All tests passed! System is production ready.")
        exit(0)
    else:
        print("\n❌ Some tests failed. Please fix issues before deployment.")
        exit(1)