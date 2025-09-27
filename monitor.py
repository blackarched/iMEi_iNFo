#!/usr/bin/env python3
"""
Production Monitoring Script for IMEI Tool
Real-time monitoring of system health and performance
"""

import time
import json
import sqlite3
import requests
import psutil
import logging
from datetime import datetime, timedelta
from typing import Dict, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class IMEIToolMonitor:
    """Comprehensive monitoring for IMEI Tool"""
    
    def __init__(self, config_file='monitoring_config.json'):
        self.config = self.load_config(config_file)
        self.alerts = []
        
    def load_config(self, config_file: str) -> Dict:
        """Load monitoring configuration"""
        default_config = {
            'server_url': 'http://localhost:5000',
            'database_path': 'data/imei_tool.db',
            'thresholds': {
                'response_time_ms': 5000,
                'cpu_usage_percent': 80,
                'memory_usage_percent': 80,
                'disk_usage_percent': 90,
                'error_rate_percent': 5,
                'daily_requests_max': 10000
            },
            'check_interval': 60,  # seconds
            'alert_cooldown': 300  # 5 minutes
        }
        
        try:
            with open(config_file, 'r') as f:
                user_config = json.load(f)
                default_config.update(user_config)
        except FileNotFoundError:
            logger.info(f"Config file {config_file} not found, using defaults")
            
        return default_config
    
    def check_server_health(self) -> Dict:
        """Check server health and response time"""
        try:
            start_time = time.time()
            response = requests.get(
                f"{self.config['server_url']}/api/health",
                timeout=30
            )
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'status': 'healthy',
                    'response_time_ms': response_time,
                    'server_time': data.get('timestamp'),
                    'version': data.get('version')
                }
            else:
                return {
                    'status': 'unhealthy',
                    'response_time_ms': response_time,
                    'status_code': response.status_code
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'response_time_ms': None
            }
    
    def check_database_health(self) -> Dict:
        """Check database health and performance"""
        try:
            db_path = self.config['database_path']
            if not os.path.exists(db_path):
                return {'status': 'error', 'error': 'Database file not found'}
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check table integrity
            cursor.execute("PRAGMA integrity_check")
            integrity = cursor.fetchone()[0]
            
            # Get database stats
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM imei_lookups")
            lookup_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM imei_lookups WHERE DATE(timestamp) = DATE('now')")
            today_lookups = cursor.fetchone()[0]
            
            # Get database size
            db_size = os.path.getsize(db_path)
            
            conn.close()
            
            return {
                'status': 'healthy' if integrity == 'ok' else 'error',
                'integrity': integrity,
                'user_count': user_count,
                'total_lookups': lookup_count,
                'today_lookups': today_lookups,
                'size_bytes': db_size,
                'size_mb': round(db_size / 1024 / 1024, 2)
            }
            
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def check_system_resources(self) -> Dict:
        """Check system resource usage"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'cpu_usage_percent': cpu_percent,
                'memory_usage_percent': memory.percent,
                'memory_available_mb': round(memory.available / 1024 / 1024, 2),
                'disk_usage_percent': disk.percent,
                'disk_free_gb': round(disk.free / 1024 / 1024 / 1024, 2)
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def check_api_endpoints(self) -> List[Dict]:
        """Check external API endpoint health"""
        endpoints = [
            'https://imei24.com',
            'https://api.checkmend.com',
            'https://api.gsmarena.com'
        ]
        
        results = []
        for endpoint in endpoints:
            try:
                start_time = time.time()
                response = requests.head(endpoint, timeout=10)
                response_time = (time.time() - start_time) * 1000
                
                results.append({
                    'endpoint': endpoint,
                    'status': 'online' if response.ok else 'error',
                    'status_code': response.status_code,
                    'response_time_ms': response_time
                })
                
            except Exception as e:
                results.append({
                    'endpoint': endpoint,
                    'status': 'offline',
                    'error': str(e)
                })
        
        return results
    
    def generate_alert(self, alert_type: str, message: str, severity: str = 'WARNING'):
        """Generate monitoring alert"""
        alert = {
            'type': alert_type,
            'message': message,
            'severity': severity,
            'timestamp': datetime.now().isoformat()
        }
        
        self.alerts.append(alert)
        logger.warning(f"ALERT [{severity}] {alert_type}: {message}")
        
        # In production, send to alerting system (email, Slack, etc.)
        return alert
    
    def check_thresholds(self, metrics: Dict):
        """Check if metrics exceed configured thresholds"""
        thresholds = self.config['thresholds']
        
        # Check response time
        if metrics.get('server', {}).get('response_time_ms', 0) > thresholds['response_time_ms']:
            self.generate_alert(
                'HIGH_RESPONSE_TIME',
                f"Server response time: {metrics['server']['response_time_ms']}ms",
                'WARNING'
            )
        
        # Check system resources
        system = metrics.get('system', {})
        if system.get('cpu_usage_percent', 0) > thresholds['cpu_usage_percent']:
            self.generate_alert(
                'HIGH_CPU_USAGE',
                f"CPU usage: {system['cpu_usage_percent']}%",
                'CRITICAL'
            )
        
        if system.get('memory_usage_percent', 0) > thresholds['memory_usage_percent']:
            self.generate_alert(
                'HIGH_MEMORY_USAGE',
                f"Memory usage: {system['memory_usage_percent']}%",
                'CRITICAL'
            )
        
        if system.get('disk_usage_percent', 0) > thresholds['disk_usage_percent']:
            self.generate_alert(
                'HIGH_DISK_USAGE',
                f"Disk usage: {system['disk_usage_percent']}%",
                'CRITICAL'
            )
        
        # Check daily request volume
        db_stats = metrics.get('database', {})
        if db_stats.get('today_lookups', 0) > thresholds['daily_requests_max']:
            self.generate_alert(
                'HIGH_REQUEST_VOLUME',
                f"Daily requests: {db_stats['today_lookups']}",
                'INFO'
            )
    
    def run_health_check(self) -> Dict:
        """Run complete health check"""
        logger.info("Running comprehensive health check...")
        
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'server': self.check_server_health(),
            'database': self.check_database_health(),
            'system': self.check_system_resources(),
            'external_apis': self.check_api_endpoints()
        }
        
        # Check thresholds and generate alerts
        self.check_thresholds(metrics)
        
        # Calculate overall health score
        health_score = self.calculate_health_score(metrics)
        metrics['health_score'] = health_score
        metrics['alerts'] = self.alerts[-10:]  # Last 10 alerts
        
        return metrics
    
    def calculate_health_score(self, metrics: Dict) -> float:
        """Calculate overall health score (0-100)"""
        score = 100.0
        
        # Server health
        if metrics['server']['status'] != 'healthy':
            score -= 30
        elif metrics['server'].get('response_time_ms', 0) > 1000:
            score -= 10
        
        # Database health
        if metrics['database']['status'] != 'healthy':
            score -= 25
        
        # System resources
        system = metrics['system']
        if system.get('cpu_usage_percent', 0) > 80:
            score -= 15
        if system.get('memory_usage_percent', 0) > 80:
            score -= 15
        if system.get('disk_usage_percent', 0) > 90:
            score -= 20
        
        # External API availability
        api_results = metrics['external_apis']
        online_apis = sum(1 for api in api_results if api['status'] == 'online')
        if online_apis == 0:
            score -= 10
        elif online_apis < len(api_results) / 2:
            score -= 5
        
        return max(0, score)
    
    def start_monitoring(self):
        """Start continuous monitoring"""
        logger.info("Starting continuous monitoring...")
        
        try:
            while True:
                metrics = self.run_health_check()
                
                # Log metrics
                logger.info(f"Health Score: {metrics['health_score']:.1f}/100")
                logger.info(f"Server: {metrics['server']['status']}")
                logger.info(f"Database: {metrics['database']['status']}")
                logger.info(f"CPU: {metrics['system'].get('cpu_usage_percent', 0):.1f}%")
                logger.info(f"Memory: {metrics['system'].get('memory_usage_percent', 0):.1f}%")
                
                # Save metrics to file
                with open('metrics.json', 'w') as f:
                    json.dump(metrics, f, indent=2)
                
                # Sleep until next check
                time.sleep(self.config['check_interval'])
                
        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")
        except Exception as e:
            logger.error(f"Monitoring error: {str(e)}")

def main():
    """Main monitoring function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='IMEI Tool Monitoring')
    parser.add_argument('--once', action='store_true', help='Run health check once')
    parser.add_argument('--config', default='monitoring_config.json', help='Config file path')
    
    args = parser.parse_args()
    
    monitor = IMEIToolMonitor(args.config)
    
    if args.once:
        metrics = monitor.run_health_check()
        print(json.dumps(metrics, indent=2))
    else:
        monitor.start_monitoring()

if __name__ == '__main__':
    main()