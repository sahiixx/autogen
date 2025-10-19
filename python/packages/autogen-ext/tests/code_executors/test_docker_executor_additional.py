"""Additional comprehensive tests for DockerCommandLineCodeExecutor"""
import asyncio
import os
import sys
import tempfile
from pathlib import Path

import pytest
from autogen_core import CancellationToken
from autogen_core.code_executor import CodeBlock
from autogen_ext.code_executors.docker import DockerCommandLineCodeExecutor, DockerCommandLineCodeExecutorConfig


def docker_tests_enabled() -> bool:
    """Check if Docker tests should run"""
    if os.environ.get("SKIP_DOCKER", "unset").lower() == "true":
        return False
    try:
        import docker
        from docker.errors import DockerException
        client = docker.from_env()
        client.ping()
        return True
    except (ImportError, Exception):
        return False


@pytest.mark.asyncio
async def test_docker_skip_condition_environment_variable() -> None:
    """Test that SKIP_DOCKER environment variable properly disables tests"""
    original_value = os.environ.get("SKIP_DOCKER")
    
    try:
        os.environ["SKIP_DOCKER"] = "true"
        assert not docker_tests_enabled()
        
        os.environ["SKIP_DOCKER"] = "True"
        assert not docker_tests_enabled()
        
        os.environ["SKIP_DOCKER"] = "TRUE"
        assert not docker_tests_enabled()
        
        os.environ["SKIP_DOCKER"] = "false"
        result = docker_tests_enabled()
        assert isinstance(result, bool)
        
    finally:
        if original_value is None:
            os.environ.pop("SKIP_DOCKER", None)
        else:
            os.environ["SKIP_DOCKER"] = original_value


@pytest.mark.asyncio
async def test_docker_directory_creation_with_explicit_none() -> None:
    """Test that executor properly handles work_dir=None"""
    if not docker_tests_enabled():
        pytest.skip("Docker tests are disabled")
    
    executor = DockerCommandLineCodeExecutor(timeout=60, work_dir=None)
    
    try:
        await executor.start()
        work_dir = executor.work_dir
        assert work_dir.is_dir()
        assert work_dir.exists()
        
        cancellation_token = CancellationToken()
        code_blocks = [CodeBlock(code="print('test')", language="python")]
        result = await executor.execute_code_blocks(code_blocks, cancellation_token)
        assert result.exit_code == 0
        
        dir_path = work_dir
        await executor.stop()
        assert not dir_path.exists()
        
    except Exception as e:
        if hasattr(executor, '_running') and executor._running:
            await executor.stop()
        raise e


@pytest.mark.asyncio  
async def test_docker_executor_with_various_timeouts() -> None:
    """Test executor behavior with different timeout values"""
    if not docker_tests_enabled():
        pytest.skip("Docker tests are disabled")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        async with DockerCommandLineCodeExecutor(work_dir=temp_dir, timeout=1) as executor:
            cancellation_token = CancellationToken()
            code_blocks = [CodeBlock(code="print('quick test')", language="python")]
            result = await executor.execute_code_blocks(code_blocks, cancellation_token)
            assert result.exit_code == 0
        
        async with DockerCommandLineCodeExecutor(work_dir=temp_dir, timeout=120) as executor:
            cancellation_token = CancellationToken()
            code_blocks = [CodeBlock(code="import time; time.sleep(2); print('done')", language="python")]
            result = await executor.execute_code_blocks(code_blocks, cancellation_token)
            assert result.exit_code == 0


@pytest.mark.asyncio
async def test_docker_executor_error_handling_for_invalid_code() -> None:
    """Test executor properly handles various types of invalid Python code"""
    if not docker_tests_enabled():
        pytest.skip("Docker tests are disabled")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        async with DockerCommandLineCodeExecutor(work_dir=temp_dir) as executor:
            cancellation_token = CancellationToken()
            
            code_blocks = [CodeBlock(code="print('unclosed string)", language="python")]
            result = await executor.execute_code_blocks(code_blocks, cancellation_token)
            assert result.exit_code != 0
            
            code_blocks = [CodeBlock(code="raise ValueError('test error')", language="python")]
            result = await executor.execute_code_blocks(code_blocks, cancellation_token)
            assert result.exit_code != 0
            assert "ValueError" in result.output
            
            code_blocks = [CodeBlock(code="print(undefined_variable)", language="python")]
            result = await executor.execute_code_blocks(code_blocks, cancellation_token)
            assert result.exit_code != 0
            assert "NameError" in result.output


@pytest.mark.asyncio
async def test_docker_executor_empty_code_blocks_error() -> None:
    """Test that executor raises ValueError for empty code block list"""
    if not docker_tests_enabled():
        pytest.skip("Docker tests are disabled")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        async with DockerCommandLineCodeExecutor(work_dir=temp_dir) as executor:
            cancellation_token = CancellationToken()
            with pytest.raises(ValueError, match="No code blocks to execute"):
                await executor.execute_code_blocks([], cancellation_token)


@pytest.mark.asyncio
async def test_docker_executor_config_serialization_roundtrip() -> None:
    """Test that executor configuration can be serialized and deserialized"""
    test_config = DockerCommandLineCodeExecutorConfig(
        image="python:3.11-slim",
        container_name="test-container",
        timeout=90,
        work_dir="/tmp/test",
        bind_dir="/tmp/bind",
        auto_remove=False,
        stop_container=False,
        functions_module="custom_functions",
        extra_volumes={"/host/path": {"bind": "/container/path", "mode": "ro"}},
        extra_hosts={"test.example.com": "192.168.1.1"},
        init_command="echo 'initialization'",
        delete_tmp_files=True
    )
    
    executor = DockerCommandLineCodeExecutor._from_config(test_config)
    new_config = executor._to_config()
    
    assert new_config.image == test_config.image
    assert new_config.container_name == test_config.container_name
    assert new_config.timeout == test_config.timeout
    assert new_config.work_dir == test_config.work_dir
    assert new_config.bind_dir == test_config.bind_dir
    assert new_config.auto_remove == test_config.auto_remove
    assert new_config.stop_container == test_config.stop_container
    assert new_config.functions_module == test_config.functions_module
    assert new_config.extra_volumes == test_config.extra_volumes
    assert new_config.extra_hosts == test_config.extra_hosts
    assert new_config.init_command == test_config.init_command
    assert new_config.delete_tmp_files == test_config.delete_tmp_files