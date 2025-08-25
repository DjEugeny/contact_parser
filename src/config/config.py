"""
Configuration management for Contact Parser
Handles secure API key management and provider configuration
"""

import os
from typing import Dict, Any
from pathlib import Path

class Config:
    """Configuration management class"""
    
    def __init__(self):
        self.config_file = Path(__file__).parent / "config.json"
        self._load_config()
    
    def _load_config(self):
        """Load configuration from environment variables and config files"""
        
        # Environment variables with proper defaults
        self.openrouter_api_key = os.getenv('OPENROUTER_API_KEY')
        self.groq_api_key = os.getenv('GROQ_API_KEY')
        self.replicate_api_key = os.getenv('REPLICATE_API_KEY')
        self.test_mode = os.getenv('TEST_MODE', 'false').lower() == 'true'
        
        # Load provider configuration from providers.json
        providers_config_path = Path(__file__).parent.parent / "config" / "providers.json"
        try:
            import json
            with open(providers_config_path, 'r') as f:
                providers_data = json.load(f)
                self.provider_order = providers_data.get('provider_order', ['openrouter', 'groq'])
                self.provider_settings = providers_data.get('provider_settings', {})
                self.fallback_settings = providers_data.get('fallback_settings', {})
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Warning: Could not load providers.json: {e}")
            # Fallback to basic configuration
            self.provider_order = ['openrouter', 'groq']
            self.provider_settings = {}
            self.fallback_settings = {}
        
        # Provider configurations based on providers.json and environment
        self.providers = {
            'openrouter': {
                'name': 'OpenRouter',
                'model': os.getenv('OPENROUTER_MODEL', 'qwen/qwen3-235b-a22b:free'),
                'base_url': "https://openrouter.ai/api/v1/chat/completions",
                'priority': self.provider_settings.get('openrouter', {}).get('priority', 3),
                'active': bool(self.openrouter_api_key),
                'failure_count': 0,
                'last_failure': None,
                'max_failures_before_skip': self.provider_settings.get('openrouter', {}).get('max_failures_before_skip', 3),
                'retry_delay_seconds': self.provider_settings.get('openrouter', {}).get('retry_delay_seconds', 5),
                'headers': {
                    'Content-Type': 'application/json',
                    'HTTP-Referer': 'https://localhost:3000',
                    'X-Title': 'Contact Extractor LLM'
                }
            },
            'groq': {
                'name': 'Groq',
                'model': os.getenv('GROQ_MODEL', 'llama3-8b-8192'),
                'base_url': "https://api.groq.com/openai/v1/chat/completions",
                'priority': self.provider_settings.get('groq', {}).get('priority', 2),
                'active': bool(self.groq_api_key),
                'failure_count': 0,
                'last_failure': None,
                'max_failures_before_skip': self.provider_settings.get('groq', {}).get('max_failures_before_skip', 3),
                'retry_delay_seconds': self.provider_settings.get('groq', {}).get('retry_delay_seconds', 3),
                'headers': {
                    'Content-Type': 'application/json'
                }
            },
            'replicate': {
                'name': 'Replicate',
                'model': os.getenv('REPLICATE_MODEL', 'meta/llama-2-70b-chat'),
                'base_url': "https://api.replicate.com/v1/predictions",
                'priority': self.provider_settings.get('replicate', {}).get('priority', 1),
                'active': bool(self.replicate_api_key),
                'failure_count': 0,
                'last_failure': None,
                'max_failures_before_skip': self.provider_settings.get('replicate', {}).get('max_failures_before_skip', 2),
                'retry_delay_seconds': self.provider_settings.get('replicate', {}).get('retry_delay_seconds', 10),
                'headers': {
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.replicate_api_key}'
                }
            }
        }
        
        # Retry and timeout settings
        self.max_retries = int(os.getenv('MAX_RETRIES', '3'))
        self.retry_delay = int(os.getenv('RETRY_DELAY', '1'))
        self.timeout = int(os.getenv('REQUEST_TIMEOUT', '30'))
        self.max_fallback_attempts = int(self.fallback_settings.get('max_fallback_attempts', 2))
        
        # Validation settings
        self.min_confidence = float(os.getenv('MIN_CONFIDENCE', '0.5'))
        self.max_contacts_per_email = int(os.getenv('MAX_CONTACTS_PER_EMAIL', '50'))
    
    def get_provider_config(self, provider_name: str) -> Dict[str, Any]:
        """Get configuration for a specific provider"""
        return self.providers.get(provider_name, {})
    
    def get_active_providers(self) -> Dict[str, Dict[str, Any]]:
        """Get only active providers"""
        return {name: config for name, config in self.providers.items() 
                if config.get('active', False)}
    
    def validate_api_keys(self) -> bool:
        """Validate that all required API keys are present"""
        missing_keys = []
        
        if not self.openrouter_api_key:
            missing_keys.append('OPENROUTER_API_KEY')
        if not self.groq_api_key:
            missing_keys.append('GROQ_API_KEY')
        if not self.replicate_api_key:
            missing_keys.append('REPLICATE_API_KEY')
        
        if missing_keys:
            print(f"❌ Missing API keys: {', '.join(missing_keys)}")
            print("Please set these environment variables before running the application.")
            return False
        
        return True
    
    def get_api_key(self, provider_name: str) -> str:
        """Get API key for a specific provider"""
        if provider_name == 'openrouter':
            return self.openrouter_api_key or ''
        elif provider_name == 'groq':
            return self.groq_api_key or ''
        elif provider_name == 'replicate':
            return self.replicate_api_key or ''
        return ''

# Global config instance
config = Config()