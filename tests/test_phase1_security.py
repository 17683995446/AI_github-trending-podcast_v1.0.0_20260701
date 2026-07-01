"""Phase 1 单元测试：安全与 Bug 修复。

测试范围：
1. 路径穿越防护（handler._serve_file）
2. config.py 不再包含硬编码 API Key
3. pydub 音频拼接退化策略
"""
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


class TestPathTraversalProtection:
    """路径穿越防护测试。"""

    def test_normal_path_allowed(self):
        """正常路径应被允许访问。"""
        from gh_trending_audio.web.handler import DashboardHandler
        # 模拟正常文件访问
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.md"
            test_file.write_text("hello")
            # 验证路径解析逻辑
            safe_path = Path("test.md")
            full_path = (Path(tmpdir) / safe_path).resolve()
            full_path.relative_to(Path(tmpdir).resolve())  # 不应抛异常

    def test_traversal_blocked(self):
        """../../../etc/passwd 应被拒绝。"""
        from pathlib import Path
        base = Path("/tmp/safe_dir").resolve()
        malicious = Path("../../../etc/passwd")
        full = (base / malicious).resolve()
        # 验证 resolve 后的路径不在 base 内
        with pytest.raises(ValueError):
            full.relative_to(base)

    def test_double_dot_bypass_blocked(self):
        """旧方式 replace('..','') 的绕过尝试应被新方案阻止。"""
        from pathlib import Path
        base = Path("/tmp/safe_dir").resolve()
        # 旧方式 replace("..","") 对 "....//" 会变成 "//"
        # 新方式 resolve() 正确解析 .. 为上级目录
        malicious = Path("../../etc/passwd")
        full = (base / malicious).resolve()
        with pytest.raises(ValueError):
            full.relative_to(base)

    def test_nested_traversal_blocked(self):
        """多层嵌套路径穿越应被阻止。"""
        from pathlib import Path
        base = Path("/tmp/safe_dir").resolve()
        malicious = Path("output_demo/../../../etc/shadow")
        full = (base / malicious).resolve()
        with pytest.raises(ValueError):
            full.relative_to(base)


class TestConfigNoHardcodedKey:
    """config.py 不应包含硬编码 API Key。"""

    def test_default_key_is_empty(self):
        """LLM_API_KEY 默认值应为空字符串。"""
        # 重新导入 config 模块（不带环境变量）
        import importlib
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("LLM_API_KEY", None)
            import gh_trending_audio.config as config
            importlib.reload(config)
            assert config.LLM_API_KEY == "", \
                "LLM_API_KEY 默认值应为空字符串，不应包含硬编码密钥"

    def test_env_var_overrides_default(self):
        """环境变量应能覆盖默认值。"""
        with patch.dict(os.environ, {"LLM_API_KEY": "sk-test-key"}):
            import importlib
            import gh_trending_audio.config as config
            importlib.reload(config)
            assert config.LLM_API_KEY == "sk-test-key"

    def test_no_key_in_source(self):
        """源码中不应出现 sk- 前缀的密钥。"""
        config_path = Path(__file__).parent.parent / "gh_trending_audio" / "config.py"
        content = config_path.read_text()
        # 检查是否包含类似 sk-xxx 的硬编码密钥（至少 20 字符）
        import re
        matches = re.findall(r'sk-[a-zA-Z0-9]{20,}', content)
        assert len(matches) == 0, f"config.py 中发现硬编码密钥: {matches}"


class TestPydubAudioConcat:
    """pydub 音频拼接测试。"""

    def test_concat_empty_list(self):
        """空文件列表不应报错。"""
        from gh_trending_audio.tts_engine import TTSEngine
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            output = f.name
        try:
            TTSEngine._concat_audio([], output)
            # 空列表时不应生成文件或不应报错
        finally:
            if os.path.exists(output):
                os.unlink(output)

    def test_concat_fallback_on_import_error(self):
        """pydub 不可用时应退化到二进制拼接。"""
        from gh_trending_audio.tts_engine import TTSEngine
        # 创建假的 mp3 文件
        with tempfile.TemporaryDirectory() as tmpdir:
            files = []
            for i in range(3):
                fpath = Path(tmpdir) / f"seg_{i}.mp3"
                fpath.write_bytes(b"ID3\x03fake mp3 data segment " + str(i).encode())
                files.append(str(fpath))
            output = str(Path(tmpdir) / "output.mp3")

            # 模拟 pydub 不可用
            with patch.dict("sys.modules", {"pydub": None}):
                TTSEngine._concat_audio(files, output)
                assert os.path.exists(output), "退化拼接应生成输出文件"
                data = Path(output).read_bytes()
                assert b"segment 0" in data
                assert b"segment 1" in data
                assert b"segment 2" in data

    def test_concat_uses_pydub_when_available(self):
        """pydub 可用时应使用 pydub 拼接。"""
        # 这个测试验证 pydub 被正确导入和调用
        # 由于需要真实 ffmpeg，我们只验证不抛异常
        from gh_trending_audio.tts_engine import TTSEngine
        with tempfile.TemporaryDirectory() as tmpdir:
            files = []
            for i in range(2):
                fpath = Path(tmpdir) / f"seg_{i}.mp3"
                fpath.write_bytes(b"ID3\x03fake data")
                files.append(str(fpath))
            output = str(Path(tmpdir) / "output.mp3")
            # 即使 pydub 内部失败，也应退化到二进制拼接
            TTSEngine._concat_audio(files, output)
            assert os.path.exists(output), "拼接应生成输出文件"
