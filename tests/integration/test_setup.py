"""
Integration tests for project setup and infrastructure.
"""
import os
import sys
import pytest
import importlib
from pathlib import Path

from src.config import get_config


class TestProjectStructure:
    """Test that project structure is correctly set up."""

    def test_all_directories_exist(self):
        """Test that all required directories exist."""
        project_root = Path(__file__).parent.parent.parent

        required_dirs = [
            'src',
            'src/config',
            'src/models',
            'src/services',
            'src/aggregators',
            'src/calculators',
            'src/readers',
            'src/writers',
            'tests',
            'tests/unit',
            'tests/integration',
            'tests/fixtures',
            'docs',
            '.github/workflows'
        ]

        for dir_path in required_dirs:
            assert (project_root / dir_path).exists(), f"Directory {dir_path} does not exist"
            assert (project_root / dir_path).is_dir(), f"{dir_path} is not a directory"

    def test_python_packages_have_init_files(self):
        """Test that all Python packages have __init__.py files."""
        project_root = Path(__file__).parent.parent.parent

        package_dirs = [
            'src',
            'src/config',
            'src/models',
            'src/services',
            'src/aggregators',
            'src/calculators',
            'src/readers',
            'src/writers',
            'tests',
            'tests/unit',
            'tests/integration',
            'tests/fixtures'
        ]

        for package_dir in package_dirs:
            init_file = project_root / package_dir / '__init__.py'
            assert init_file.exists(), f"Missing __init__.py in {package_dir}"

    def test_required_config_files_exist(self):
        """Test that required configuration files exist."""
        project_root = Path(__file__).parent.parent.parent

        required_files = [
            'requirements.txt',
            'requirements-dev.txt',
            'pytest.ini',
            'conftest.py',
            '.pre-commit-config.yaml',
            '.github/workflows/ci.yml',
            'README.md',
            'DEVELOPMENT_PLAN.md',
            'docs/README.md',
            'docs/ARCHITECTURE.md',
            '.env.example'
        ]

        for file_path in required_files:
            assert (project_root / file_path).exists(), f"Required file {file_path} does not exist"
            assert (project_root / file_path).is_file(), f"{file_path} is not a file"


class TestImportStructure:
    """Test that all modules can be imported correctly."""

    def test_config_module_imports(self):
        """Test that configuration module imports work."""
        # Test main config imports
        from src.config import get_config, load_config, reload_config, BillingSystemConfig

        # Test that functions are callable
        assert callable(get_config)
        assert callable(load_config)
        assert callable(reload_config)
        assert isinstance(BillingSystemConfig, type)

    def test_src_module_imports(self):
        """Test that src module can be imported."""
        import src
        assert hasattr(src, '__file__')

    def test_all_package_imports(self):
        """Test that all package modules can be imported."""
        packages = [
            'src.config',
            'src.models',
            'src.services',
            'src.aggregators',
            'src.calculators',
            'src.readers',
            'src.writers'
        ]

        for package in packages:
            try:
                importlib.import_module(package)
            except ImportError as e:
                pytest.fail(f"Failed to import {package}: {e}")

    def test_tests_module_imports(self):
        """Test that test modules can be imported."""
        test_modules = [
            'tests.unit',
            'tests.integration',
            'tests.fixtures'
        ]

        for module in test_modules:
            try:
                importlib.import_module(module)
            except ImportError as e:
                pytest.fail(f"Failed to import {module}: {e}")


class TestConfigurationIntegration:
    """Test configuration integration with environment."""

    def test_config_loads_in_test_environment(self, mock_env):
        """Test that configuration loads correctly in test environment."""
        config = get_config()

        assert config is not None
        assert config.environment == 'testing'
        assert config.google_project_id == 'test-project'

    def test_config_validation_passes(self, test_config):
        """Test that configuration passes all validation."""
        # This should not raise any exceptions
        service_account_info = test_config.get_google_service_account_info()

        # Verify service account info structure
        required_keys = [
            'type', 'project_id', 'private_key_id', 'private_key',
            'client_email', 'client_id', 'auth_uri', 'token_uri',
            'auth_provider_x509_cert_url', 'client_x509_cert_url'
        ]

        for key in required_keys:
            assert key in service_account_info, f"Missing key {key} in service account info"

    def test_google_api_credentials_structure(self, test_config):
        """Test that Google API credentials have correct structure."""
        service_account_info = test_config.get_google_service_account_info()

        assert service_account_info['type'] == 'service_account'
        assert service_account_info['project_id'] == test_config.google_project_id
        assert service_account_info['private_key'].startswith('-----BEGIN PRIVATE KEY-----')
        assert '@' in service_account_info['client_email']


class TestDevelopmentWorkflow:
    """Test development workflow integration."""

    def test_pytest_configuration(self):
        """Test that pytest is configured correctly."""
        # Check that pytest can find tests
        pytest_config = pytest.main(['--collect-only', '-q'])
        assert pytest_config == 0, "Pytest test collection failed"

    def test_coverage_configuration(self):
        """Test that coverage is configured correctly."""
        # This test runs pytest with coverage to ensure it's working
        exit_code = pytest.main([
            '--cov=src',
            '--cov-report=term',
            'tests/unit/test_config.py::TestBillingSystemConfig::test_config_with_valid_env_vars',
            '-v'
        ])
        assert exit_code == 0, "Coverage testing failed"

    def test_import_paths_work_from_project_root(self):
        """Test that imports work correctly from project root."""
        project_root = Path(__file__).parent.parent.parent

        # Temporarily add project root to Python path
        original_path = sys.path[:]
        try:
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))

            # Test that we can import from src
            from src.config import get_config
            config = get_config()
            assert config is not None

        finally:
            # Restore original path
            sys.path[:] = original_path


class TestFileContents:
    """Test that configuration files have expected content."""

    def test_requirements_file_content(self):
        """Test that requirements.txt contains expected dependencies."""
        project_root = Path(__file__).parent.parent.parent
        requirements_file = project_root / 'requirements.txt'

        content = requirements_file.read_text()

        # Check for essential dependencies
        essential_deps = [
            'google-auth',
            'google-api-python-client',
            'pandas',
            'python-dotenv',
            'pydantic',
            'click',
            'pytest'
        ]

        for dep in essential_deps:
            assert dep in content, f"Missing dependency {dep} in requirements.txt"

    def test_pytest_ini_configuration(self):
        """Test that pytest.ini has correct configuration."""
        project_root = Path(__file__).parent.parent.parent
        pytest_ini = project_root / 'pytest.ini'

        content = pytest_ini.read_text()

        # Check for essential pytest settings
        essential_settings = [
            'testpaths = tests',
            '--cov=src',
            '--cov-fail-under=90',
            'markers'
        ]

        for setting in essential_settings:
            assert setting in content, f"Missing pytest setting: {setting}"

    def test_github_workflow_configuration(self):
        """Test that GitHub workflow is configured correctly."""
        project_root = Path(__file__).parent.parent.parent
        workflow_file = project_root / '.github' / 'workflows' / 'ci.yml'

        content = workflow_file.read_text()

        # Check for essential workflow components
        essential_components = [
            'python-version: [3.9, "3.10", "3.11"]',
            'pytest',
            'black',
            'flake8',
            'mypy'
        ]

        for component in essential_components:
            assert component in content, f"Missing workflow component: {component}"


@pytest.mark.slow
class TestEndToEndSetup:
    """End-to-end tests for complete setup."""

    def test_full_development_setup(self, mock_env):
        """Test that the complete development setup works end-to-end."""
        # Test configuration loading
        config = get_config()
        assert config.environment == 'testing'

        # Test that Google service account info can be generated
        service_account_info = config.get_google_service_account_info()
        assert service_account_info['type'] == 'service_account'

        # Test that all modules can be imported
        from src.config import BillingSystemConfig
        assert issubclass(BillingSystemConfig, object)

    def test_production_readiness_checklist(self):
        """Test production readiness checklist."""
        project_root = Path(__file__).parent.parent.parent

        # Check for essential production files
        production_files = [
            'requirements.txt',
            'README.md',
            '.env.example',
            'docs/README.md'
        ]

        for file_path in production_files:
            file_obj = project_root / file_path
            assert file_obj.exists(), f"Production file {file_path} missing"
            assert file_obj.stat().st_size > 0, f"Production file {file_path} is empty"