import importlib

import pytest


def reload_modules():
    import app.core.config as config_module
    import app.services.execution_service as exec_module
    importlib.reload(config_module)
    importlib.reload(exec_module)
    return exec_module


def _set_minimal_env(monkeypatch, env='development', allow=None):
    monkeypatch.setenv('ENVIRONMENT', env)
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///./test.db')
    monkeypatch.setenv('SECRET_KEY', 'x' * 32)
    monkeypatch.setenv('REFRESH_SECRET_KEY', 'y' * 32)
    monkeypatch.setenv('CORS_ORIGINS', 'http://localhost:3000')
    monkeypatch.setenv('TRUSTED_HOSTS', 'localhost,127.0.0.1,[::1]')
    monkeypatch.setenv('MAX_REQUEST_SIZE', '1048576')
    monkeypatch.setenv('MAX_UPLOAD_SIZE', '1048576')
    monkeypatch.setenv('MAX_RESPONSE_SIZE', '1048576')
    monkeypatch.setenv('REQUEST_TIMEOUT_SECONDS', '5')
    if allow is not None:
        monkeypatch.setenv('ALLOW_LOCALHOST_TARGETS', '1' if allow else '0')


def test_localhost_allowed_by_default_in_development(monkeypatch):
    _set_minimal_env(monkeypatch, env='development', allow=None)
    exec_module = reload_modules()
    svc = exec_module.ExecutionService(db=None)
    # should not raise for loopback address when in development default
    assert svc._validate_url('http://127.0.0.1:8000') == 'http://127.0.0.1:8000'
    # IPv6 loopback should also be permitted in development
    assert svc._validate_url('http://[::1]:8000') == 'http://[::1]:8000'


def test_localhost_rejected_by_default_in_production(monkeypatch):
    _set_minimal_env(monkeypatch, env='production', allow=None)
    exec_module = reload_modules()
    svc = exec_module.ExecutionService(db=None)
    with pytest.raises(exec_module.InvalidRequestURLError):
        svc._validate_url('http://127.0.0.1:8000')
    # IPv6 loopback should also be rejected in production
    with pytest.raises(exec_module.InvalidRequestURLError):
        svc._validate_url('http://[::1]:8000')
