"""Tests for HITL approval workflow."""

import pytest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from agentic_fleet.skills.approval import (
    ApprovalStatus,
    ApprovalDecision,
    SkillApprovalWorkflow,
    ApprovalStore,
    approval_store,
)
from agentic_fleet.skills.creator import SkillApprovalRequest


class TestApprovalStatus:
    """Tests for ApprovalStatus enum."""

    def test_all_statuses(self):
        """Test all approval statuses are defined."""
        assert ApprovalStatus.PENDING.value == "pending"
        assert ApprovalStatus.APPROVED.value == "approved"
        assert ApprovalStatus.REJECTED.value == "rejected"
        assert ApprovalStatus.REVISION_REQUESTED.value == "revision_requested"


class TestApprovalDecision:
    """Tests for ApprovalDecision model."""

    def test_create_approved_decision(self):
        """Test creating approved decision."""
        decision = ApprovalDecision(
            status=ApprovalStatus.APPROVED,
            feedback="Looks good!",
            reviewed_by="senior-dev",
        )

        assert decision.status == ApprovalStatus.APPROVED
        assert decision.feedback == "Looks good!"
        assert decision.reviewed_by == "senior-dev"

    def test_create_rejected_decision(self):
        """Test creating rejected decision with feedback."""
        decision = ApprovalDecision(
            status=ApprovalStatus.REJECTED,
            feedback="Does not meet requirements",
            reviewed_by="tech-lead",
        )

        assert decision.status == ApprovalStatus.REJECTED
        assert decision.feedback == "Does not meet requirements"

    def test_create_revision_decision(self):
        """Test creating revision requested decision."""
        decision = ApprovalDecision(
            status=ApprovalStatus.REVISION_REQUESTED,
            feedback="Please add more examples",
            revisions={"example_count": 3},
        )

        assert decision.status == ApprovalStatus.REVISION_REQUESTED
        assert decision.revisions is not None
        assert decision.revisions["example_count"] == 3


class TestSkillApprovalWorkflow:
    """Tests for SkillApprovalWorkflow."""

    @pytest.fixture
    def sample_request(self):
        """Create sample approval request."""
        return SkillApprovalRequest(
            skill_name="new-skill",
            skill_description="A test skill",
            skill_yaml="skill_id: new-skill\nname: New Skill",
            skill_instructions="Test instructions",
            quality_score=8.5,
            validation_results=[],
            improvement_suggestions=[],
            freedom_level="medium",
            knowledge_domain="software",
        )

    def test_create_workflow(self, sample_request):
        """Test creating a workflow."""
        workflow = SkillApprovalWorkflow(request=sample_request)

        assert workflow.request.skill_name == "new-skill"
        assert workflow.decision is None
        assert workflow.workflow_id.startswith("skill-approval-")

    def test_submit_for_review(self, sample_request):
        """Test submitting workflow for review."""
        workflow = SkillApprovalWorkflow(request=sample_request)
        result = workflow.submit_for_review()

        assert result["status"] == "pending"
        assert result["request"]["skill_name"] == "new-skill"

    def test_make_decision(self, sample_request):
        """Test making a decision on workflow."""
        workflow = SkillApprovalWorkflow(request=sample_request)

        decision = ApprovalDecision(
            status=ApprovalStatus.APPROVED,
            feedback="Approved",
        )
        result = workflow.make_decision(decision)

        assert result["status"] == "approved"
        assert workflow.decision is not None
        assert workflow.decision.status == ApprovalStatus.APPROVED

    def test_is_pending(self, sample_request):
        """Test is_pending check."""
        workflow = SkillApprovalWorkflow(request=sample_request)

        assert workflow.is_pending() is True

        workflow.make_decision(ApprovalDecision(status=ApprovalStatus.APPROVED))
        assert workflow.is_pending() is False

    def test_is_approved(self, sample_request):
        """Test is_approved check."""
        workflow = SkillApprovalWorkflow(request=sample_request)

        assert workflow.is_approved() is False

        workflow.make_decision(ApprovalDecision(status=ApprovalStatus.APPROVED))
        assert workflow.is_approved() is True

    def test_is_rejected(self, sample_request):
        """Test is_rejected check."""
        workflow = SkillApprovalWorkflow(request=sample_request)

        assert workflow.is_rejected() is False

        workflow.make_decision(ApprovalDecision(status=ApprovalStatus.REJECTED))
        assert workflow.is_rejected() is True


class TestApprovalStore:
    """Tests for ApprovalStore."""

    @pytest.fixture
    def store(self):
        """Create fresh store for each test."""
        return ApprovalStore()

    @pytest.fixture
    def sample_request(self):
        """Create sample approval request."""
        return SkillApprovalRequest(
            skill_name="test-skill",
            skill_description="A test skill",
            skill_yaml="skill_id: test-skill\nname: Test Skill",
            skill_instructions="Test instructions",
            quality_score=7.0,
            validation_results=[],
            improvement_suggestions=[],
            freedom_level="medium",
            knowledge_domain="general",
        )

    def test_create_workflow(self, store, sample_request):
        """Test creating workflow in store."""
        workflow_id = store.create_workflow(sample_request)

        assert workflow_id is not None
        assert store.get_workflow(workflow_id) is not None

    def test_get_workflow(self, store, sample_request):
        """Test retrieving workflow from store."""
        workflow_id = store.create_workflow(sample_request)
        workflow = store.get_workflow(workflow_id)

        assert workflow is not None
        assert workflow.request.skill_name == "test-skill"

    def test_list_pending(self, store, sample_request):
        """Test listing pending workflows."""
        id1 = store.create_workflow(sample_request)
        id2 = store.create_workflow(sample_request)

        pending = store.list_pending()
        assert len(pending) == 2

        # Approve one
        store.record_decision(id1, ApprovalStatus.APPROVED, "Approved")

        pending = store.list_pending()
        assert len(pending) == 1

    def test_record_decision(self, store, sample_request):
        """Test recording a decision."""
        workflow_id = store.create_workflow(sample_request)

        success = store.record_decision(
            workflow_id=workflow_id,
            status=ApprovalStatus.APPROVED,
            feedback="Looks good",
            reviewed_by="admin",
        )

        assert success is True

        workflow = store.get_workflow(workflow_id)
        assert workflow.is_approved()

    def test_record_decision_invalid_workflow(self, store, sample_request):
        """Test recording decision for nonexistent workflow."""
        success = store.record_decision(
            workflow_id="nonexistent-id",
            status=ApprovalStatus.APPROVED,
        )

        assert success is False

    def test_count_by_status(self, store, sample_request):
        """Test counting workflows by status."""
        id1 = store.create_workflow(sample_request)
        id2 = store.create_workflow(sample_request)
        id3 = store.create_workflow(sample_request)

        store.record_decision(id1, ApprovalStatus.APPROVED)
        store.record_decision(id2, ApprovalStatus.REJECTED)

        counts = store.count_by_status()

        assert counts["approved"] == 1
        assert counts["rejected"] == 1
        assert counts["pending"] == 1

    def test_global_store(self):
        """Test global approval store instance."""
        assert approval_store is not None
        assert isinstance(approval_store, ApprovalStore)
