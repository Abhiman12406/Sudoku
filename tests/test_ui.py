import io
import pandas as pd
import pytest

from src.ui.app import (
    format_severity_badge,
    generate_corrupt_sample_template_bytes,
    generate_sample_template_bytes,
)


def test_format_severity_badge():
    assert format_severity_badge("Critical") == "🔴 Critical"
    assert format_severity_badge("Warning") == "🟡 Warning"
    assert format_severity_badge("Info") == "🔵 Info"
    assert format_severity_badge("CRITICAL") == "🔴 Critical"


def test_generate_sample_template_bytes():
    clean_bytes = generate_sample_template_bytes()
    assert isinstance(clean_bytes, bytes)
    df = pd.read_excel(io.BytesIO(clean_bytes))
    assert len(df) == 14
    assert "Tag" in df.columns
    assert "IO Type" in df.columns


def test_generate_corrupt_sample_template_bytes():
    corrupt_bytes = generate_corrupt_sample_template_bytes()
    assert isinstance(corrupt_bytes, bytes)
    df = pd.read_excel(io.BytesIO(corrupt_bytes))
    assert len(df) >= 7
    assert "XYZ_CORRUPT" in list(df["IO Type"])
