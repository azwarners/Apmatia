from pathlib import Path
import importlib

import pytest

from apmatia.core.modules.manifest import load_module_manifest
from apmatia.core.registry import ModuleCategory, ModuleMetadata, ModuleStatus


def _write_manifest(tmp_path: Path, module_fields: str = "", metadata: str = "") -> Path:
    module_dir = tmp_path / "example"
    module_dir.mkdir()
    (module_dir / "manifest.toml").write_text(
        f"""[module]
module_id = "example"
name = "Example"
{module_fields}

[metadata]
{metadata}
""",
        encoding="utf-8",
    )
    return module_dir


def test_manifest_metadata_defaults_and_extension_data(tmp_path: Path):
    manifest = load_module_manifest(_write_manifest(tmp_path, metadata='owner = "team"'))
    assert manifest.status is ModuleStatus.DEVELOPMENT
    assert manifest.category is ModuleCategory.FEATURE
    assert manifest.default_enabled is True
    assert manifest.tags == ()
    assert manifest.metadata == {"owner": "team"}


@pytest.mark.parametrize("status", ["stable", "development"])
def test_manifest_parses_status_and_tags(tmp_path: Path, status: str):
    manifest = load_module_manifest(
        _write_manifest(
            tmp_path,
            f'status = "{status}"\ncategory = "tool"\ntags = ["one", "two"]',
        )
    )
    assert manifest.status.value == status
    assert manifest.category is ModuleCategory.TOOL
    assert manifest.tags == ("one", "two")


@pytest.mark.parametrize(
    "field,value",
    [("status", "unknown"), ("category", "unknown")],
)
def test_manifest_rejects_unknown_standard_values(tmp_path: Path, field: str, value: str):
    with pytest.raises(ValueError, match="Unsupported module"):
        load_module_manifest(_write_manifest(tmp_path, f'{field} = "{value}"'))


def test_first_class_values_override_legacy_metadata(tmp_path: Path):
    manifest = load_module_manifest(
        _write_manifest(
            tmp_path,
            'category = "integration"\ntags = ["new"]',
            'category = "tool"\ntags = ["old"]\ncustom = true',
        )
    )
    assert manifest.category is ModuleCategory.INTEGRATION
    assert manifest.tags == ("new",)
    assert manifest.metadata == {"custom": True}


def test_legacy_standard_values_are_supported_without_duplication(tmp_path: Path):
    manifest = load_module_manifest(
        _write_manifest(tmp_path, metadata='category = "tool"\ntags = ["legacy"]\ncustom = 1')
    )
    assert manifest.category is ModuleCategory.TOOL
    assert manifest.tags == ("legacy",)
    assert manifest.metadata == {"custom": 1}


def test_bundled_runtime_metadata_matches_manifests():
    modules_dir = Path(__file__).resolve().parents[2] / "src" / "apmatia" / "modules"
    for module_dir in sorted(path for path in modules_dir.iterdir() if (path / "manifest.toml").exists()):
        manifest = load_module_manifest(module_dir)
        runtime_module = importlib.import_module(f"apmatia.modules.{module_dir.name}.module")
        runtime_metadata = next(
            value for value in vars(runtime_module).values() if isinstance(value, ModuleMetadata)
        )
        assert runtime_metadata.module_id == manifest.module_id
        assert runtime_metadata.name == manifest.name
        assert runtime_metadata.version == manifest.version
        assert runtime_metadata.description == manifest.description
        assert runtime_metadata.author == manifest.author
        assert runtime_metadata.status is manifest.status
        assert runtime_metadata.category is manifest.category
        assert runtime_metadata.default_enabled is manifest.default_enabled
        assert runtime_metadata.tags == manifest.tags
        assert not {"status", "category", "default_enabled", "tags"}.intersection(runtime_metadata.metadata)
