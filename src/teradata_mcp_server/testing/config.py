"""
Configuration management for the testing framework.
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from pathlib import Path
import yaml


@dataclass
class TestConfig:
    """Configuration for test execution."""
    
    # Test execution settings
    timeout_seconds: int = 300
    max_retries: int = 1
    parallel_execution: bool = False
    stop_on_first_failure: bool = False
    
    # Test filtering
    test_patterns: List[str] = field(default_factory=lambda: ["test_*Tools"])
    module_patterns: List[str] = field(default_factory=lambda: ["*"])
    excluded_tests: List[str] = field(default_factory=list)
    excluded_modules: List[str] = field(default_factory=list)
    
    # Output settings
    output_directory: str = "test_results"
    generate_html_report: bool = True
    generate_json_report: bool = True
    verbose_logging: bool = False
    
    # Database settings
    use_test_database: bool = True
    test_database_suffix: str = "_test"
    cleanup_test_data: bool = True
    
    # LLM client settings
    llm_provider: str = "anthropic"  # anthropic, openai, etc.
    llm_model: str = "claude-3-sonnet-20240229"
    llm_max_tokens: int = 4000
    llm_temperature: float = 0.1
    
    # Advanced settings
    capture_tool_calls: bool = True
    save_conversation_logs: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_file(cls, config_path: str) -> 'TestConfig':
        """Load configuration from YAML file."""
        if not os.path.exists(config_path):
            return cls()
        
        with open(config_path, 'r') as f:
            data = yaml.safe_load(f)
        
        return cls(**data)

    def save_to_file(self, config_path: str):
        """Save configuration to YAML file."""
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        with open(config_path, 'w') as f:
            yaml.dump(self.__dict__, f, default_flow_style=False)

    def get_output_dir(self) -> Path:
        """Get output directory as Path object."""
        return Path(self.output_directory)

    def ensure_output_dir(self):
        """Ensure output directory exists."""
        self.get_output_dir().mkdir(parents=True, exist_ok=True)