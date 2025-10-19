# mypy: disable-error-code="no-any-unimported"
import asyncio
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import AsyncGenerator, TypeAlias

import pytest
import pytest_asyncio
from aiofiles import open
from autogen_core import CancellationToken
from autogen_core.code_executor import CodeBlock
from autogen_ext.code_executors.docker import DockerCommandLineCodeExecutor, DockerCommandLineCodeExecutorConfig


def docker_tests_enabled() -> bool:
    if os.environ.get("SKIP_DOCKER", "unset").lower() == "true":
        return False

    try:
        import docker
        from docker.errors import DockerException
    except ImportError:
        return False

    try:
        client = docker.from_env()
        client.ping()  # type: ignore
        return True
    except DockerException:
        return False


@pytest_asyncio.fixture(scope="module")  # type: ignore
async def executor_and_temp_dir(
    request: pytest.FixtureRequest,
) -> AsyncGenerator[tuple[DockerCommandLineCodeExecutor, str], None]:
    if not docker_tests_enabled():
        pytest.skip("Docker tests are disabled")

    with tempfile.TemporaryDirectory() as temp_dir:
        async with DockerCommandLineCodeExecutor(work_dir=temp_dir) as executor:
            yield executor, temp_dir


ExecutorFixture: TypeAlias = tuple[DockerCommandLineCodeExecutor, str]


@pytest_asyncio.fixture(scope="function")  # type: ignore
async def cleanup_temp_dir(executor_and_temp_dir: ExecutorFixture) -> AsyncGenerator[None, None]:
    _executor, temp_dir = executor_and_temp_dir
    for file in Path(temp_dir).iterdir():
        if file.is_file():
            file.unlink()
        elif file.is_dir():
            shutil.rmtree(file)
    yield None


@pytest.mark.asyncio
@pytest.mark.parametrize("executor_and_temp_dir", ["docker"], indirect=True)
async def test_execute_code(executor_and_temp_dir: ExecutorFixture, cleanup_temp_dir: None) -> None:
    executor, _temp_dir = executor_and_temp_dir
    cancellation_token = CancellationToken()

    # Test single code block.
    code_blocks = [CodeBlock(code="import sys; print('hello world!')", language="python")]
    code_result = await executor.execute_code_blocks(code_blocks, cancellation_token)
    assert code_result.exit_code == 0 and "hello world!" in code_result.output and code_result.code_file is not None

    # Test multiple code blocks.
    code_blocks = [
        CodeBlock(code="import sys; print('hello world!')", language="python"),
        CodeBlock(code="a = 100 + 100; print(a)", language="python"),
    ]
    code_result = await executor.execute_code_blocks(code_blocks, cancellation_token)
    assert (
        code_result.exit_code == 0
        and "hello world!" in code_result.output
        and "200" in code_result.output
        and code_result.code_file is not None
    )

    # Test bash script.
    if sys.platform not in ["win32"]:
        code_blocks = [CodeBlock(code="echo 'hello world!'", language="bash")]
        code_result = await executor.execute_code_blocks(code_blocks, cancellation_token)
        assert code_result.exit_code == 0 and "hello world!" in code_result.output and code_result.code_file is not None

    # Test running code.
    file_lines = ["import sys", "print('hello world!')", "a = 100 + 100", "print(a)"]
    code_blocks = [CodeBlock(code="\n".join(file_lines), language="python")]
    code_result = await executor.execute_code_blocks(code_blocks, cancellation_token)
    assert (
        code_result.exit_code == 0
        and "hello world!" in code_result.output
        and "200" in code_result.output
        and code_result.code_file is not None
    )

    # Check saved code file.
    async with open(code_result.code_file) as f:
        code_lines = await f.readlines()
        for file_line, code_line in zip(file_lines, code_lines, strict=False):
            assert file_line.strip() == code_line.strip()


@pytest.mark.asyncio
@pytest.mark.parametrize("executor_and_temp_dir", ["docker"], indirect=True)
async def test_commandline_code_executor_timeout(
    executor_and_temp_dir: ExecutorFixture, cleanup_temp_dir: None
) -> None:
    _executor, temp_dir = executor_and_temp_dir
    cancellation_token = CancellationToken()
    code_blocks = [CodeBlock(code="import time; time.sleep(10); print('hello world!')", language="python")]

    async with DockerCommandLineCodeExecutor(timeout=1, work_dir=temp_dir) as executor:
        code_result = await executor.execute_code_blocks(code_blocks, cancellation_token)

    assert code_result.exit_code and "Timeout" in code_result.output


@pytest.mark.asyncio
@pytest.mark.parametrize("executor_and_temp_dir", ["docker"], indirect=True)
async def test_commandline_code_executor_cancellation(
    executor_and_temp_dir: ExecutorFixture, cleanup_temp_dir: None
) -> None:
    _executor, temp_dir = executor_and_temp_dir
    cancellation_token = CancellationToken()
    # Write code that sleep for 10 seconds and then write "hello world!"
    # to a file.
    code = """import time
time.sleep(10)
with open("hello.txt", "w") as f:
    f.write("hello world!")
"""
    code_blocks = [CodeBlock(code=code, language="python")]

    task = asyncio.create_task(_executor.execute_code_blocks(code_blocks, cancellation_token))
    # Cancel the task after 2 seconds
    await asyncio.sleep(2)
    cancellation_token.cancel()
    code_result = await task

    assert code_result.exit_code and "Code execution was cancelled" in code_result.output

    # Check if the file was not created
    hello_file_path = Path(temp_dir) / "hello.txt"
    assert not hello_file_path.exists(), f"File {hello_file_path} should not exist after cancellation"


@pytest.mark.asyncio
@pytest.mark.parametrize("executor_and_temp_dir", ["docker"], indirect=True)
async def test_invalid_relative_path(executor_and_temp_dir: ExecutorFixture, cleanup_temp_dir: None) -> None:
    executor, _temp_dir = executor_and_temp_dir
    cancellation_token = CancellationToken()
    code = """# filename: /tmp/test.py

print("hello world")
"""
    result = await executor.execute_code_blocks(
        [CodeBlock(code=code, language="python")], cancellation_token=cancellation_token
    )
    assert result.exit_code == 1 and "Filename is not in the workspace" in result.output


@pytest.mark.asyncio
@pytest.mark.parametrize("executor_and_temp_dir", ["docker"], indirect=True)
async def test_valid_relative_path(executor_and_temp_dir: ExecutorFixture, cleanup_temp_dir: None) -> None:
    executor, temp_dir_str = executor_and_temp_dir

    cancellation_token = CancellationToken()
    temp_dir = Path(temp_dir_str)

    code = """# filename: test.py

print("hello world")
"""
    result = await executor.execute_code_blocks(
        [CodeBlock(code=code, language="python")], cancellation_token=cancellation_token
    )
    assert result.exit_code == 0
    assert "hello world" in result.output
    assert result.code_file is not None
    assert "test.py" in result.code_file
    assert (temp_dir / Path("test.py")).resolve() == Path(result.code_file).resolve()
    assert (temp_dir / Path("test.py")).exists()


@pytest.mark.asyncio
async def test_docker_commandline_code_executor_start_stop() -> None:
    if not docker_tests_enabled():
        pytest.skip("Docker tests are disabled")

    with tempfile.TemporaryDirectory() as temp_dir:
        executor = DockerCommandLineCodeExecutor(work_dir=temp_dir)
        await executor.start()
        await executor.stop()


@pytest.mark.asyncio
async def test_docker_commandline_code_executor_start_stop_context_manager() -> None:
    if not docker_tests_enabled():
        pytest.skip("Docker tests are disabled")

    with tempfile.TemporaryDirectory() as temp_dir:
        async with DockerCommandLineCodeExecutor(work_dir=temp_dir) as _exec:
            pass


@pytest.mark.asyncio
async def test_docker_commandline_code_executor_extra_args() -> None:
    if not docker_tests_enabled():
        pytest.skip("Docker tests are disabled")

    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a file in temp_dir to mount
        host_file_path = Path(temp_dir) / "host_file.txt"
        host_file_path.write_text("This is a test file.")

        container_file_path = "/container/host_file.txt"

        extra_volumes = {str(host_file_path): {"bind": container_file_path, "mode": "rw"}}
        init_command = "echo 'Initialization command executed' > /workspace/init_command.txt"
        extra_hosts = {"example.com": "127.0.0.1"}

        async with DockerCommandLineCodeExecutor(
            work_dir=temp_dir,
            extra_volumes=extra_volumes,
            init_command=init_command,
            extra_hosts=extra_hosts,
        ) as executor:
            cancellation_token = CancellationToken()

            # Verify init_command was executed
            init_command_file_path = Path(temp_dir) / "init_command.txt"
            assert init_command_file_path.exists()

            # Verify extra_hosts
            ns_lookup_code_blocks = [
                CodeBlock(code="import socket; print(socket.gethostbyname('example.com'))", language="python")
            ]
            ns_lookup_result = await executor.execute_code_blocks(ns_lookup_code_blocks, cancellation_token)
            assert ns_lookup_result.exit_code == 0
            assert "127.0.0.1" in ns_lookup_result.output

            # Verify the file is accessible in the volume mounted in extra_volumes
            code_blocks = [
                CodeBlock(code=f"with open('{container_file_path}') as f: print(f.read())", language="python")
            ]
            code_result = await executor.execute_code_blocks(code_blocks, cancellation_token)
            assert code_result.exit_code == 0
            assert "This is a test file." in code_result.output


@pytest.mark.asyncio
async def test_docker_commandline_code_executor_serialization() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        executor = DockerCommandLineCodeExecutor(work_dir=temp_dir)

        executor_config = executor.dump_component()
        loaded_executor = DockerCommandLineCodeExecutor.load_component(executor_config)

        assert executor.bind_dir == loaded_executor.bind_dir
        assert executor.timeout == loaded_executor.timeout


def test_invalid_timeout() -> None:
    with pytest.raises(ValueError, match="Timeout must be greater than or equal to 1."):
        _ = DockerCommandLineCodeExecutor(timeout=0)


@pytest.mark.asyncio
async def test_directory_not_initialized() -> None:
    executor = DockerCommandLineCodeExecutor()
    with pytest.raises(RuntimeError, match="Working directory not properly initialized"):
        _ = executor.work_dir


@pytest.mark.asyncio
@pytest.mark.parametrize("executor_and_temp_dir", ["docker"], indirect=True)
async def test_error_wrong_path(executor_and_temp_dir: ExecutorFixture, cleanup_temp_dir: None) -> None:
    if not docker_tests_enabled():
        pytest.skip("Docker tests are disabled")

    executor, _ = executor_and_temp_dir
    cancellation_token = CancellationToken()
    code_blocks = [
        CodeBlock(
            code="""with open("/nonexistent_dir/test.txt", "w") as f:
            f.write("hello world!")""",
            language="python",
        )
    ]
    result = await executor.execute_code_blocks(code_blocks, cancellation_token)
    assert result.exit_code != 0
    assert "No such file or directory" in result.output


@pytest.mark.asyncio
async def test_deprecated_warning() -> None:
    if not docker_tests_enabled():
        pytest.skip("Docker tests are disabled")

    with pytest.warns(DeprecationWarning, match="Using the current directory as work_dir is deprecated."):
        async with DockerCommandLineCodeExecutor(work_dir=".") as executor:
            await executor.start()
            cancellation_token = CancellationToken()
            code_block = CodeBlock(code='echo "hello world!"', language="sh")
            result = await executor.execute_code_blocks([code_block], cancellation_token)
            assert result.exit_code == 0
            assert "hello world!" in result.output


@pytest.mark.asyncio
async def test_directory_creation_cleanup() -> None:
    if not docker_tests_enabled():
        pytest.skip("Docker tests are disabled")

    executor = DockerCommandLineCodeExecutor(timeout=60, work_dir=None)

    await executor.start()

    directory = executor.work_dir
    assert directory.is_dir()

    await executor.stop()

    assert not Path(directory).exists()


@pytest.mark.asyncio
async def test_delete_tmp_files() -> None:
    if not docker_tests_enabled():
        pytest.skip("Docker tests are disabled")

    with tempfile.TemporaryDirectory() as temp_dir:
        # Test with delete_tmp_files=False (default)
        async with DockerCommandLineCodeExecutor(work_dir=temp_dir) as executor:
            cancellation_token = CancellationToken()
            code_blocks = [CodeBlock(code="print('test output')", language="python")]
            result = await executor.execute_code_blocks(code_blocks, cancellation_token)
            assert result.exit_code == 0
            assert result.code_file is not None
            # Verify file exists after execution
            assert Path(result.code_file).exists()

        # Test with delete_tmp_files=True
        async with DockerCommandLineCodeExecutor(work_dir=temp_dir, delete_tmp_files=True) as executor:
            cancellation_token = CancellationToken()
            code_blocks = [CodeBlock(code="print('test output')", language="python")]
            result = await executor.execute_code_blocks(code_blocks, cancellation_token)
            assert result.exit_code == 0
            assert result.code_file is not None
            # Verify file is deleted after execution
            assert not Path(result.code_file).exists()

            # Test with multiple code blocks
            code_blocks = [
                CodeBlock(code="print('first block')", language="python"),
                CodeBlock(code="print('second block')", language="python"),
            ]
            result = await executor.execute_code_blocks(code_blocks, cancellation_token)
            assert result.exit_code == 0
            assert result.code_file is not None
            # Verify files are deleted after execution
            assert not Path(result.code_file).exists()

            # Test deletion with execution error
            code_blocks = [CodeBlock(code="raise Exception('test error')", language="python")]
            result = await executor.execute_code_blocks(code_blocks, cancellation_token)
            assert result.exit_code != 0
            assert result.code_file is not None
            # Verify file is deleted even after error
            assert not Path(result.code_file).exists()


@pytest.mark.asyncio
@pytest.mark.parametrize("executor_and_temp_dir", ["docker"], indirect=True)
async def test_docker_commandline_code_executor_with_multiple_tasks(
    executor_and_temp_dir: ExecutorFixture, cleanup_temp_dir: None
) -> None:
    if not docker_tests_enabled():
        pytest.skip("Docker tests are disabled")

    async def run_cancellation_scenario(executor: DockerCommandLineCodeExecutor) -> None:
        token = CancellationToken()
        code_block = CodeBlock(language="bash", code="sleep 10")
        exec_task = asyncio.create_task(executor.execute_code_blocks([code_block], cancellation_token=token))
        await asyncio.sleep(1)
        token.cancel()
        try:
            await exec_task
        except asyncio.CancelledError:
            pass

    def run_scenario_in_new_loop(executor_instance: DockerCommandLineCodeExecutor) -> None:
        asyncio.run(run_cancellation_scenario(executor_instance))

    executor, _ = executor_and_temp_dir
    await asyncio.get_running_loop().run_in_executor(None, run_scenario_in_new_loop, executor)


@pytest.mark.asyncio
async def test_docker_skip_condition_environment_variable() -> None:
    """Test that SKIP_DOCKER environment variable properly disables tests"""
    # Save original value
    original_value = os.environ.get("SKIP_DOCKER")
    
    try:
        # Test with SKIP_DOCKER=true
        os.environ["SKIP_DOCKER"] = "true"
        assert not docker_tests_enabled(), "docker_tests_enabled should return False when SKIP_DOCKER=true"
        
        # Test with SKIP_DOCKER=True (capital T)
        os.environ["SKIP_DOCKER"] = "True"
        assert not docker_tests_enabled(), "docker_tests_enabled should return False when SKIP_DOCKER=True"
        
        # Test with SKIP_DOCKER=TRUE (all caps)
        os.environ["SKIP_DOCKER"] = "TRUE"
        assert not docker_tests_enabled(), "docker_tests_enabled should return False when SKIP_DOCKER=TRUE"
        
        # Test with SKIP_DOCKER=false
        os.environ["SKIP_DOCKER"] = "false"
        # Result depends on whether docker is available, so we just ensure it doesn't crash
        result = docker_tests_enabled()
        assert isinstance(result, bool), "docker_tests_enabled should return a boolean"
        
    finally:
        # Restore original value
        if original_value is None:
            os.environ.pop("SKIP_DOCKER", None)
        else:
            os.environ["SKIP_DOCKER"] = original_value


@pytest.mark.asyncio
async def test_docker_directory_creation_with_explicit_none() -> None:
    """Test that executor properly handles work_dir=None"""
    if not docker_tests_enabled():
        pytest.skip("Docker tests are disabled")
    
    # Create executor with explicit None for work_dir
    executor = DockerCommandLineCodeExecutor(timeout=60, work_dir=None)
    
    try:
        await executor.start()
        
        # Verify work_dir was created
        work_dir = executor.work_dir
        assert work_dir.is_dir(), "Work directory should be created"
        assert work_dir.exists(), "Work directory should exist"
        
        # Verify we can execute code in the created directory
        cancellation_token = CancellationToken()
        code_blocks = [CodeBlock(code="print('test')", language="python")]
        result = await executor.execute_code_blocks(code_blocks, cancellation_token)
        assert result.exit_code == 0, "Code execution should succeed"
        
        # Store directory path for later verification
        dir_path = work_dir
        
        await executor.stop()
        
        # Verify directory was cleaned up
        assert not dir_path.exists(), "Temporary directory should be cleaned up after stop"
        
    except Exception as e:
        # Ensure cleanup even on failure
        if hasattr(executor, '_running') and executor._running:
            await executor.stop()
        raise e


@pytest.mark.asyncio  
async def test_docker_executor_with_various_timeouts() -> None:
    """Test executor behavior with different timeout values"""
    if not docker_tests_enabled():
        pytest.skip("Docker tests are disabled")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Test with minimum valid timeout
        async with DockerCommandLineCodeExecutor(work_dir=temp_dir, timeout=1) as executor:
            cancellation_token = CancellationToken()
            code_blocks = [CodeBlock(code="print('quick test')", language="python")]
            result = await executor.execute_code_blocks(code_blocks, cancellation_token)
            assert result.exit_code == 0, "Quick code should complete within 1 second"
        
        # Test with larger timeout
        async with DockerCommandLineCodeExecutor(work_dir=temp_dir, timeout=120) as executor:
            cancellation_token = CancellationToken()
            code_blocks = [CodeBlock(code="import time; time.sleep(2); print('done')", language="python")]
            result = await executor.execute_code_blocks(code_blocks, cancellation_token)
            assert result.exit_code == 0, "Code requiring multiple seconds should complete"


@pytest.mark.asyncio
async def test_docker_executor_multiple_start_stop_cycles() -> None:
    """Test that executor can be started and stopped multiple times"""
    if not docker_tests_enabled():
        pytest.skip("Docker tests are disabled")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        executor = DockerCommandLineCodeExecutor(work_dir=temp_dir, timeout=60)
        
        # First cycle
        await executor.start()
        assert executor._running, "Executor should be running after start"
        await executor.stop()
        assert not executor._running, "Executor should not be running after stop"
        
        # Second cycle
        await executor.start()
        assert executor._running, "Executor should be running after second start"
        
        # Execute code to verify it's functional
        cancellation_token = CancellationToken()
        code_blocks = [CodeBlock(code="print('cycle test')", language="python")]
        result = await executor.execute_code_blocks(code_blocks, cancellation_token)
        assert result.exit_code == 0, "Code should execute successfully"
        
        await executor.stop()
        assert not executor._running, "Executor should not be running after second stop"


@pytest.mark.asyncio
async def test_docker_executor_error_handling_for_invalid_code() -> None:
    """Test executor properly handles various types of invalid Python code"""
    if not docker_tests_enabled():
        pytest.skip("Docker tests are disabled")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        async with DockerCommandLineCodeExecutor(work_dir=temp_dir) as executor:
            cancellation_token = CancellationToken()
            
            # Test syntax error
            code_blocks = [CodeBlock(code="print('unclosed string)", language="python")]
            result = await executor.execute_code_blocks(code_blocks, cancellation_token)
            assert result.exit_code != 0, "Syntax error should result in non-zero exit code"
            
            # Test runtime error  
            code_blocks = [CodeBlock(code="raise ValueError('test error')", language="python")]
            result = await executor.execute_code_blocks(code_blocks, cancellation_token)
            assert result.exit_code != 0, "Runtime error should result in non-zero exit code"
            assert "ValueError" in result.output, "Error message should mention ValueError"
            
            # Test undefined variable
            code_blocks = [CodeBlock(code="print(undefined_variable)", language="python")]
            result = await executor.execute_code_blocks(code_blocks, cancellation_token)
            assert result.exit_code != 0, "Undefined variable should result in non-zero exit code"
            assert "NameError" in result.output, "Error message should mention NameError"


@pytest.mark.asyncio
async def test_docker_executor_empty_code_blocks_error() -> None:
    """Test that executor raises ValueError for empty code block list"""
    if not docker_tests_enabled():
        pytest.skip("Docker tests are disabled")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        async with DockerCommandLineCodeExecutor(work_dir=temp_dir) as executor:
            cancellation_token = CancellationToken()
            
            # Test with empty list
            with pytest.raises(ValueError, match="No code blocks to execute"):
                await executor.execute_code_blocks([], cancellation_token)


@pytest.mark.asyncio
async def test_docker_executor_bash_script_execution() -> None:
    """Test executor can run various bash commands"""
    if not docker_tests_enabled():
        pytest.skip("Docker tests are disabled")
    
    if sys.platform == "win32":
        pytest.skip("Bash tests not supported on Windows")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        async with DockerCommandLineCodeExecutor(work_dir=temp_dir) as executor:
            cancellation_token = CancellationToken()
            
            # Test basic echo
            code_blocks = [CodeBlock(code="echo 'Hello from bash'", language="bash")]
            result = await executor.execute_code_blocks(code_blocks, cancellation_token)
            assert result.exit_code == 0, "Echo command should succeed"
            assert "Hello from bash" in result.output, "Output should contain echoed text"
            
            # Test environment variable
            code_blocks = [CodeBlock(code="export TEST_VAR='test_value'; echo $TEST_VAR", language="sh")]
            result = await executor.execute_code_blocks(code_blocks, cancellation_token)
            assert result.exit_code == 0, "Environment variable test should succeed"
            assert "test_value" in result.output, "Output should contain variable value"
            
            # Test file operations in bash
            code_blocks = [CodeBlock(code="echo 'file content' > test.txt; cat test.txt", language="bash")]
            result = await executor.execute_code_blocks(code_blocks, cancellation_token)
            assert result.exit_code == 0, "File operations should succeed"
            assert "file content" in result.output, "Output should contain file content"


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
    
    # Create executor from config
    executor = DockerCommandLineCodeExecutor._from_config(test_config)
    
    # Convert back to config
    new_config = executor._to_config()
    
    # Verify all fields match
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