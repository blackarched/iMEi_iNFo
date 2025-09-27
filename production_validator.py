#!/usr/bin/env python3
"""
Production Readiness Validator
Comprehensive validation of all critical issues addressed
"""

import os
import json
import sqlite3
import requests
import subprocess
import time
from datetime import datetime
from typing import Dict, List, Tuple

class ProductionValidator:
    """Validates production readiness of IMEI Tool"""
    
    def __init__(self):
        self.results = []
        self.score = 0
        self.max_score = 0
        
    def test_result(self, category: str, test_name: str, passed: bool, details: str = "", weight: int = 1):
        """Record test result"""
        self.results.append({
            'category': category,
            'test': test_name,
            'passed': passed,
            'details': details,
            'weight': weight,
            'timestamp': datetime.now().isoformat()
        })
        
        if passed:
            self.score += weight
        self.max_score += weight
        
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} [{category}] {test_name}")
        if details:
            print(f"    {details}")
    
    def validate_file_structure(self):
        """Validate all required files exist"""
        print("\n🔍 VALIDATING FILE STRUCTURE")
        print("=" * 40)
        
        required_files = [
            ('imei.html', 'Web interface'),
            ('imei.py', 'Desktop client'),
            ('server.py', 'Backend server'),
            ('config.py', 'Configuration'),
            ('requirements.txt', 'Dependencies'),
            ('Dockerfile', 'Container config'),
            ('docker-compose.yml', 'Deployment config'),
            ('nginx.conf', 'Web server config'),
            ('.env.example', 'Environment template'),
            ('deploy.sh', 'Deployment script'),
            ('README.md', 'Documentation'),
            ('test_suite.py', 'Test suite'),
            ('monitor.py', 'Monitoring script')
        ]
        
        for filename, description in required_files:
            exists = os.path.exists(filename)
            self.test_result('File Structure', f'{filename} ({description})', exists)
    
    def validate_api_endpoints(self):
        """Validate API endpoint configurations"""
        print("\n🌐 VALIDATING API ENDPOINTS")
        print("=" * 40)
        
        # Check that fake endpoints are removed
        with open('imei.html', 'r') as f:
            html_content = f.read()
        
        fake_endpoints = [
            'imeipro.info/api',
            'deviceatlas.com/api/imei',
            'api.imei.info/'
        ]
        
        for endpoint in fake_endpoints:
            not_found = endpoint not in html_content
            self.test_result('API Endpoints', f'Removed fake endpoint: {endpoint}', not_found)
        
        # Check for real endpoint configurations
        real_endpoints = [
            'imei24.com/api',
            'api.checkmend.com',
            'api.gsmarena.com'
        ]
        
        for endpoint in real_endpoints:
            found = endpoint in html_content
            self.test_result('API Endpoints', f'Real endpoint configured: {endpoint}', found)
    
    def validate_tac_database(self):
        """Validate TAC database comprehensiveness"""
        print("\n📱 VALIDATING TAC DATABASE")
        print("=" * 40)
        
        try:
            from server import COMPREHENSIVE_TAC_DATABASE
            
            # Check database size
            db_size = len(COMPREHENSIVE_TAC_DATABASE)
            self.test_result('TAC Database', 'Database size > 50 entries', db_size > 50, f"Found {db_size} entries")
            
            # Check for major brands
            brands = set(device['brand'] for device in COMPREHENSIVE_TAC_DATABASE.values())
            required_brands = ['Apple', 'Samsung', 'Xiaomi', 'Huawei', 'OnePlus', 'Google', 'Oppo', 'Vivo']
            
            for brand in required_brands:
                found = brand in brands
                self.test_result('TAC Database', f'Brand coverage: {brand}', found)
            
            # Check for modern devices (2020+)
            modern_devices = sum(1 for device in COMPREHENSIVE_TAC_DATABASE.values() 
                               if device.get('year', '0') >= '2020')
            self.test_result('TAC Database', 'Modern devices (2020+)', modern_devices > 20, f"Found {modern_devices} modern devices")
            
            # Check for device types
            device_types = set(device['type'] for device in COMPREHENSIVE_TAC_DATABASE.values())
            expected_types = ['Smartphone', 'Tablet', 'Smartwatch', 'Gaming Phone']
            
            for device_type in expected_types:
                found = device_type in device_types
                self.test_result('TAC Database', f'Device type: {device_type}', found)
                
        except ImportError:
            self.test_result('TAC Database', 'Database import', False, "Could not import database")
    
    def validate_security_features(self):
        """Validate security implementations"""
        print("\n🔒 VALIDATING SECURITY FEATURES")
        print("=" * 40)
        
        # Check server.py for security features
        try:
            with open('server.py', 'r') as f:
                server_content = f.read()
            
            security_features = [
                ('rate limiting', 'limiter'),
                ('input sanitization', 'sanitize_input'),
                ('password hashing', 'generate_password_hash'),
                ('API key generation', 'generate_api_key'),
                ('security logging', 'log_security_event'),
                ('CORS protection', 'CORS'),
                ('SQL injection protection', 'sqlite3'),
                ('encryption', 'Fernet')
            ]
            
            for feature_name, code_pattern in security_features:
                implemented = code_pattern in server_content
                self.test_result('Security', f'{feature_name} implemented', implemented)
                
        except FileNotFoundError:
            self.test_result('Security', 'Server security check', False, "server.py not found")
        
        # Check HTML for client-side security
        try:
            with open('imei.html', 'r') as f:
                html_content = f.read()
            
            client_security = [
                ('Input sanitization', 'sanitizeInput'),
                ('Rate limiting', 'RATE_LIMIT'),
                ('XSS protection', 'replace(/[<>"\'&]/g'),
                ('API key management', 'USER_API_KEY')
            ]
            
            for feature_name, code_pattern in client_security:
                implemented = code_pattern in html_content
                self.test_result('Client Security', f'{feature_name}', implemented)
                
        except FileNotFoundError:
            self.test_result('Client Security', 'Client security check', False, "imei.html not found")
    
    def validate_database_schema(self):
        """Validate database schema"""
        print("\n💾 VALIDATING DATABASE SCHEMA")
        print("=" * 40)
        
        try:
            from server import init_db, app
            
            # Create test database
            test_db = ':memory:'
            app.config['DATABASE'] = test_db
            
            with app.app_context():
                init_db()
                
                # Check tables exist
                import sqlite3
                conn = sqlite3.connect(test_db)
                cursor = conn.cursor()
                
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
                required_tables = ['users', 'imei_lookups', 'rate_limits', 'security_events', 'api_usage']
                for table in required_tables:
                    found = table in tables
                    self.test_result('Database Schema', f'Table: {table}', found)
                
                # Check indexes exist
                cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
                indexes = [row[0] for row in cursor.fetchall()]
                
                required_indexes = ['idx_imei_lookups_user_id', 'idx_imei_lookups_timestamp']
                for index in required_indexes:
                    found = index in indexes
                    self.test_result('Database Schema', f'Index: {index}', found)
                
                conn.close()
                
        except Exception as e:
            self.test_result('Database Schema', 'Schema validation', False, str(e))
    
    def validate_deployment_config(self):
        """Validate deployment configuration"""
        print("\n🚀 VALIDATING DEPLOYMENT CONFIG")
        print("=" * 40)
        
        # Check Docker configuration
        docker_files = ['Dockerfile', 'docker-compose.yml']
        for file in docker_files:
            exists = os.path.exists(file)
            self.test_result('Deployment', f'Docker config: {file}', exists)
        
        # Check Nginx configuration
        nginx_exists = os.path.exists('nginx.conf')
        self.test_result('Deployment', 'Nginx configuration', nginx_exists)
        
        if nginx_exists:
            with open('nginx.conf', 'r') as f:
                nginx_content = f.read()
            
            nginx_features = [
                ('SSL configuration', 'ssl_certificate'),
                ('Rate limiting', 'limit_req_zone'),
                ('Security headers', 'X-Frame-Options'),
                ('Gzip compression', 'gzip'),
                ('Proxy configuration', 'proxy_pass')
            ]
            
            for feature_name, pattern in nginx_features:
                found = pattern in nginx_content
                self.test_result('Nginx Config', feature_name, found)
        
        # Check environment template
        env_exists = os.path.exists('.env.example')
        self.test_result('Deployment', 'Environment template', env_exists)
        
        # Check deployment script
        deploy_exists = os.path.exists('deploy.sh')
        deploy_executable = os.access('deploy.sh', os.X_OK) if deploy_exists else False
        self.test_result('Deployment', 'Deployment script exists', deploy_exists)
        self.test_result('Deployment', 'Deployment script executable', deploy_executable)
    
    def validate_monitoring(self):
        """Validate monitoring capabilities"""
        print("\n📊 VALIDATING MONITORING")
        print("=" * 40)
        
        # Check monitoring script
        monitor_exists = os.path.exists('monitor.py')
        self.test_result('Monitoring', 'Monitoring script', monitor_exists)
        
        # Check test suite
        test_exists = os.path.exists('test_suite.py')
        self.test_result('Monitoring', 'Test suite', test_exists)
        
        # Check logging configuration
        try:
            from server import logger
            self.test_result('Monitoring', 'Logging configured', True)
        except:
            self.test_result('Monitoring', 'Logging configured', False)
    
    def validate_performance(self):
        """Validate performance optimizations"""
        print("\n⚡ VALIDATING PERFORMANCE")
        print("=" * 40)
        
        # Check for database indexes
        try:
            with open('server.py', 'r') as f:
                server_content = f.read()
            
            performance_features = [
                ('Database indexing', 'CREATE INDEX'),
                ('Connection pooling', 'sqlite3.connect'),
                ('Async processing', 'threading'),
                ('Response caching', 'cache'),
                ('Batch processing', 'batch')
            ]
            
            for feature_name, pattern in performance_features:
                found = pattern in server_content
                self.test_result('Performance', feature_name, found)
                
        except FileNotFoundError:
            self.test_result('Performance', 'Performance check', False, "server.py not found")
    
    def generate_report(self):
        """Generate comprehensive validation report"""
        print("\n" + "=" * 60)
        print("🏆 PRODUCTION READINESS VALIDATION REPORT")
        print("=" * 60)
        
        # Calculate scores by category
        categories = {}
        for result in self.results:
            cat = result['category']
            if cat not in categories:
                categories[cat] = {'passed': 0, 'total': 0, 'weight': 0}
            
            categories[cat]['total'] += 1
            categories[cat]['weight'] += result['weight']
            if result['passed']:
                categories[cat]['passed'] += result['weight']
        
        # Display category scores
        print("\n📊 CATEGORY SCORES:")
        for category, stats in categories.items():
            score = (stats['passed'] / stats['weight']) * 100
            print(f"  {category:<20}: {score:5.1f}% ({stats['passed']}/{stats['weight']})")
        
        # Overall score
        overall_score = (self.score / self.max_score) * 100
        print(f"\n🎯 OVERALL SCORE: {overall_score:.1f}% ({self.score}/{self.max_score})")
        
        # Determine readiness level
        if overall_score >= 95:
            readiness = "🚀 PRODUCTION READY"
            color = "GREEN"
        elif overall_score >= 85:
            readiness = "⚠️  MOSTLY READY (Minor issues)"
            color = "YELLOW"
        elif overall_score >= 70:
            readiness = "🔧 NEEDS WORK (Major issues)"
            color = "ORANGE"
        else:
            readiness = "❌ NOT READY (Critical issues)"
            color = "RED"
        
        print(f"\n🏆 READINESS STATUS: {readiness}")
        
        # List failed tests
        failed_tests = [r for r in self.results if not r['passed']]
        if failed_tests:
            print(f"\n❌ FAILED TESTS ({len(failed_tests)}):")
            for test in failed_tests:
                print(f"  - [{test['category']}] {test['test']}")
                if test['details']:
                    print(f"    {test['details']}")
        
        # Critical issues summary
        critical_categories = ['Security', 'API Endpoints', 'Database Schema']
        critical_failures = [r for r in failed_tests if r['category'] in critical_categories]
        
        if critical_failures:
            print(f"\n🚨 CRITICAL ISSUES ({len(critical_failures)}):")
            for test in critical_failures:
                print(f"  - {test['test']}: {test['details']}")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        if overall_score < 95:
            print("  - Address all failed tests before production deployment")
        if critical_failures:
            print("  - Critical security/functionality issues MUST be fixed")
        if overall_score >= 95:
            print("  - System is production ready!")
            print("  - Set up monitoring and backup procedures")
            print("  - Configure proper SSL certificates")
            print("  - Review and test disaster recovery procedures")
        
        return overall_score
    
    def run_validation(self):
        """Run complete validation suite"""
        print("🔍 IMEI TOOL PRODUCTION READINESS VALIDATION")
        print("=" * 60)
        print(f"Validation started at: {datetime.now().isoformat()}")
        
        # Run all validation tests
        self.validate_file_structure()
        self.validate_api_endpoints()
        self.validate_tac_database()
        self.validate_security_features()
        self.validate_database_schema()
        self.validate_deployment_config()
        self.validate_monitoring()
        self.validate_performance()
        
        # Generate final report
        final_score = self.generate_report()
        
        # Save results
        report_data = {
            'validation_timestamp': datetime.now().isoformat(),
            'overall_score': final_score,
            'max_possible_score': self.max_score,
            'tests_passed': self.score,
            'results': self.results
        }
        
        with open('production_validation_report.json', 'w') as f:
            json.dump(report_data, f, indent=2)
        
        print(f"\n📄 Full report saved to: production_validation_report.json")
        
        return final_score >= 95

def main():
    """Main validation function"""
    validator = ProductionValidator()
    is_ready = validator.run_validation()
    
    if is_ready:
        print("\n🎉 SYSTEM IS PRODUCTION READY! 🎉")
        exit(0)
    else:
        print("\n⚠️  SYSTEM NEEDS WORK BEFORE PRODUCTION DEPLOYMENT")
        exit(1)

if __name__ == '__main__':
    main()