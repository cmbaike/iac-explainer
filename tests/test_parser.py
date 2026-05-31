"""Deterministic parser tests — zero API calls."""
import pytest
from pathlib import Path

from iac_explainer.parser import parse, ParseError

FIXTURES = Path(__file__).parent / "fixtures"


# ── Helper ────────────────────────────────────────────────────────────────────

def _types(resources: list[dict]) -> list[str]:
    return [r["type"] for r in resources]


def _names(resources: list[dict]) -> list[str]:
    return [r["name"] for r in resources]


# ── simple_s3.tf ──────────────────────────────────────────────────────────────

class TestSimpleS3:
    def setup_method(self):
        self.raw, self.resources = parse(FIXTURES / "simple_s3.tf")

    def test_returns_raw_hcl(self):
        assert "aws_s3_bucket" in self.raw

    def test_resource_count(self):
        assert len(self.resources) == 4

    def test_resource_types(self):
        types = _types(self.resources)
        assert "aws_s3_bucket" in types
        assert "aws_s3_bucket_versioning" in types
        assert "aws_s3_bucket_server_side_encryption_configuration" in types
        assert "aws_s3_bucket_public_access_block" in types

    def test_resource_names(self):
        assert all(name == "app_logs" for name in _names(self.resources))

    def test_each_resource_has_required_keys(self):
        for r in self.resources:
            assert "type" in r
            assert "name" in r
            assert "config" in r

    def test_config_is_dict(self):
        for r in self.resources:
            assert isinstance(r["config"], dict)


# ── ec2_with_sg.tf ────────────────────────────────────────────────────────────

class TestEc2WithSg:
    def setup_method(self):
        _, self.resources = parse(FIXTURES / "ec2_with_sg.tf")

    def test_resource_count(self):
        assert len(self.resources) == 3

    def test_has_security_group(self):
        assert "aws_security_group" in _types(self.resources)

    def test_has_ec2_instance(self):
        assert "aws_instance" in _types(self.resources)

    def test_has_eip(self):
        assert "aws_eip" in _types(self.resources)

    def test_instance_type_in_config(self):
        instance = next(r for r in self.resources if r["type"] == "aws_instance")
        assert instance["config"]["instance_type"] == "t3.small"


# ── insecure_public_bucket.tf ─────────────────────────────────────────────────

class TestInsecureBucket:
    def setup_method(self):
        _, self.resources = parse(FIXTURES / "insecure_public_bucket.tf")

    def test_resource_count(self):
        # s3_bucket, public_access_block, security_group, iam_role, iam_role_policy
        assert len(self.resources) == 5

    def test_has_s3_bucket(self):
        assert "aws_s3_bucket" in _types(self.resources)

    def test_has_public_access_block(self):
        assert "aws_s3_bucket_public_access_block" in _types(self.resources)

    def test_has_iam_resources(self):
        types = _types(self.resources)
        assert "aws_iam_role" in types
        assert "aws_iam_role_policy" in types

    def test_public_access_block_disabled(self):
        pab = next(r for r in self.resources if r["type"] == "aws_s3_bucket_public_access_block")
        assert pab["config"]["block_public_acls"] is False
        assert pab["config"]["block_public_policy"] is False

    def test_security_group_present(self):
        assert "aws_security_group" in _types(self.resources)


# ── multi_resource.tf ─────────────────────────────────────────────────────────

class TestMultiResource:
    def setup_method(self):
        _, self.resources = parse(FIXTURES / "multi_resource.tf")

    def test_has_expected_types(self):
        types = set(_types(self.resources))
        expected = {
            "aws_vpc",
            "aws_subnet",
            "aws_db_subnet_group",
            "aws_security_group",
            "aws_db_instance",
            "aws_instance",
            "aws_elasticache_subnet_group",
            "aws_elasticache_cluster",
        }
        assert expected.issubset(types)

    def test_two_subnets(self):
        subnets = [r for r in self.resources if r["type"] == "aws_subnet"]
        assert len(subnets) == 2

    def test_two_security_groups(self):
        sgs = [r for r in self.resources if r["type"] == "aws_security_group"]
        assert len(sgs) == 2

    def test_db_instance_config(self):
        db = next(r for r in self.resources if r["type"] == "aws_db_instance")
        assert db["config"]["engine"] == "postgres"
        assert db["config"]["storage_encrypted"] is True
        assert db["config"]["multi_az"] is True


# ── Error handling ────────────────────────────────────────────────────────────

class TestErrors:
    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(ParseError, match="not found"):
            parse(tmp_path / "nonexistent.tf")

    def test_wrong_extension_raises(self, tmp_path):
        f = tmp_path / "config.yaml"
        f.write_text("key: value")
        with pytest.raises(ParseError, match=".tf"):
            parse(f)

    def test_empty_file_raises(self, tmp_path):
        f = tmp_path / "empty.tf"
        f.write_text("   ")
        with pytest.raises(ParseError, match="empty"):
            parse(f)

    def test_invalid_hcl_raises(self, tmp_path):
        f = tmp_path / "broken.tf"
        f.write_text("resource {{{ not valid hcl")
        with pytest.raises(ParseError, match="HCL parse error"):
            parse(f)
