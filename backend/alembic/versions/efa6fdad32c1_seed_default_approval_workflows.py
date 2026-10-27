"""seed_default_approval_workflows

Revision ID: efa6fdad32c1
Revises: c49a60d1ef1f
Create Date: 2026-10-27 12:15:52.839560

"""
from datetime import datetime, timezone
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = 'efa6fdad32c1'
down_revision: Union[str, None] = 'c49a60d1ef1f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Deterministic UUIDs for standard seed data
EOA_WF_ID = uuid.UUID("11111111-1111-4111-8111-111111111111")
STAGE_SCRUTINY_ID = uuid.UUID("22222222-2222-4222-8222-222222222221")
STAGE_EVAL_ID = uuid.UUID("22222222-2222-4222-8222-222222222222")
STAGE_EVC_ID = uuid.UUID("22222222-2222-4222-8222-222222222223")
STAGE_COMM_ID = uuid.UUID("22222222-2222-4222-8222-222222222224")
STAGE_DECISION_ID = uuid.UUID("22222222-2222-4222-8222-222222222225")


def upgrade() -> None:
    now = datetime.now(timezone.utc)

    # 1. Workflow Definition: Extension of Approval
    wf_table = sa.table(
        'workflow_definitions',
        sa.column('id', sa.Uuid),
        sa.column('name', sa.String),
        sa.column('application_type', sa.String),
        sa.column('description', sa.String),
        sa.column('is_active', sa.Boolean),
        sa.column('created_at', sa.DateTime(timezone=True)),
        sa.column('updated_at', sa.DateTime(timezone=True)),
    )
    op.bulk_insert(
        wf_table,
        [
            {
                'id': EOA_WF_ID,
                'name': 'Standard Extension of Approval Workflow',
                'application_type': 'Extension of Approval',
                'description': 'Standard multi-stage AICTE regulatory workflow for Extension of Approval (EoA).',
                'is_active': True,
                'created_at': now,
                'updated_at': now,
            }
        ],
    )

    # 2. Workflow Stages
    stage_table = sa.table(
        'workflow_stages',
        sa.column('id', sa.Uuid),
        sa.column('workflow_definition_id', sa.Uuid),
        sa.column('stage_name', sa.String),
        sa.column('stage_code', sa.String),
        sa.column('description', sa.String),
        sa.column('sequence_order', sa.Integer),
        sa.column('is_active', sa.Boolean),
        sa.column('created_at', sa.DateTime(timezone=True)),
    )
    op.bulk_insert(
        stage_table,
        [
            {
                'id': STAGE_SCRUTINY_ID,
                'workflow_definition_id': EOA_WF_ID,
                'stage_name': 'Scrutiny',
                'stage_code': 'EOA_SCRUTINY',
                'description': 'Preliminary institutional document verification and verification of mandatory compliances.',
                'sequence_order': 1,
                'is_active': True,
                'created_at': now,
            },
            {
                'id': STAGE_EVAL_ID,
                'workflow_definition_id': EOA_WF_ID,
                'stage_name': 'Evaluation',
                'stage_code': 'EOA_EVALUATION',
                'description': 'Technical academic evaluation and infrastructural deficiency review.',
                'sequence_order': 2,
                'is_active': True,
                'created_at': now,
            },
            {
                'id': STAGE_EVC_ID,
                'workflow_definition_id': EOA_WF_ID,
                'stage_name': 'EVC',
                'stage_code': 'EOA_EVC',
                'description': 'Expert Visiting Committee on-site or virtual physical inspection.',
                'sequence_order': 3,
                'is_active': True,
                'created_at': now,
            },
            {
                'id': STAGE_COMM_ID,
                'workflow_definition_id': EOA_WF_ID,
                'stage_name': 'Committee Review',
                'stage_code': 'EOA_COMMITTEE_REVIEW',
                'description': 'Standing Appellate Committee / Executive Committee statutory assessment.',
                'sequence_order': 4,
                'is_active': True,
                'created_at': now,
            },
            {
                'id': STAGE_DECISION_ID,
                'workflow_definition_id': EOA_WF_ID,
                'stage_name': 'Decision',
                'stage_code': 'EOA_DECISION',
                'description': 'Final statutory determination by authorized AICTE Competent Authority.',
                'sequence_order': 5,
                'is_active': True,
                'created_at': now,
            },
        ],
    )

    # 3. Workflow Transitions
    trans_table = sa.table(
        'workflow_transitions',
        sa.column('id', sa.Uuid),
        sa.column('workflow_definition_id', sa.Uuid),
        sa.column('from_stage_id', sa.Uuid),
        sa.column('to_stage_id', sa.Uuid),
        sa.column('action_name', sa.String),
        sa.column('allowed_roles', sa.JSON),
        sa.column('requires_remarks', sa.Boolean),
        sa.column('resulting_status', sa.String),
        sa.column('is_active', sa.Boolean),
        sa.column('created_at', sa.DateTime(timezone=True)),
    )
    op.bulk_insert(
        trans_table,
        [
            # Initial submission transition
            {
                'id': uuid.uuid4(),
                'workflow_definition_id': EOA_WF_ID,
                'from_stage_id': None,
                'to_stage_id': STAGE_SCRUTINY_ID,
                'action_name': 'SUBMIT',
                'allowed_roles': ['INSTITUTION_USER'],
                'requires_remarks': False,
                'resulting_status': 'SUBMITTED',
                'is_active': True,
                'created_at': now,
            },
            # Scrutiny -> Scrutiny: Return for Clarification
            {
                'id': uuid.uuid4(),
                'workflow_definition_id': EOA_WF_ID,
                'from_stage_id': STAGE_SCRUTINY_ID,
                'to_stage_id': STAGE_SCRUTINY_ID,
                'action_name': 'RETURN_FOR_CLARIFICATION',
                'allowed_roles': ['ADMIN', 'AICTE_OFFICIAL'],
                'requires_remarks': True,
                'resulting_status': 'RETURNED_FOR_CLARIFICATION',
                'is_active': True,
                'created_at': now,
            },
            # Scrutiny -> Scrutiny: Resubmit Clarification
            {
                'id': uuid.uuid4(),
                'workflow_definition_id': EOA_WF_ID,
                'from_stage_id': STAGE_SCRUTINY_ID,
                'to_stage_id': STAGE_SCRUTINY_ID,
                'action_name': 'RESUBMIT_CLARIFICATION',
                'allowed_roles': ['INSTITUTION_USER'],
                'requires_remarks': False,
                'resulting_status': 'UNDER_SCRUTINY',
                'is_active': True,
                'created_at': now,
            },
            # Scrutiny -> Evaluation: Complete Scrutiny
            {
                'id': uuid.uuid4(),
                'workflow_definition_id': EOA_WF_ID,
                'from_stage_id': STAGE_SCRUTINY_ID,
                'to_stage_id': STAGE_EVAL_ID,
                'action_name': 'COMPLETE_SCRUTINY',
                'allowed_roles': ['ADMIN', 'AICTE_OFFICIAL'],
                'requires_remarks': False,
                'resulting_status': 'UNDER_SCRUTINY',
                'is_active': True,
                'created_at': now,
            },
            # Evaluation -> EVC: Schedule EVC
            {
                'id': uuid.uuid4(),
                'workflow_definition_id': EOA_WF_ID,
                'from_stage_id': STAGE_EVAL_ID,
                'to_stage_id': STAGE_EVC_ID,
                'action_name': 'SCHEDULE_EVC',
                'allowed_roles': ['ADMIN', 'AICTE_OFFICIAL'],
                'requires_remarks': False,
                'resulting_status': 'EVC_SCHEDULED',
                'is_active': True,
                'created_at': now,
            },
            # Evaluation -> Committee Review: Forward for Review (skip EVC if not required)
            {
                'id': uuid.uuid4(),
                'workflow_definition_id': EOA_WF_ID,
                'from_stage_id': STAGE_EVAL_ID,
                'to_stage_id': STAGE_COMM_ID,
                'action_name': 'FORWARD_FOR_REVIEW',
                'allowed_roles': ['ADMIN', 'AICTE_OFFICIAL'],
                'requires_remarks': False,
                'resulting_status': 'UNDER_REVIEW',
                'is_active': True,
                'created_at': now,
            },
            # EVC -> Committee Review: Complete EVC
            {
                'id': uuid.uuid4(),
                'workflow_definition_id': EOA_WF_ID,
                'from_stage_id': STAGE_EVC_ID,
                'to_stage_id': STAGE_COMM_ID,
                'action_name': 'COMPLETE_EVC',
                'allowed_roles': ['ADMIN', 'AICTE_OFFICIAL', 'REVIEWER'],
                'requires_remarks': False,
                'resulting_status': 'UNDER_REVIEW',
                'is_active': True,
                'created_at': now,
            },
            # Committee Review -> Decision: Complete Review
            {
                'id': uuid.uuid4(),
                'workflow_definition_id': EOA_WF_ID,
                'from_stage_id': STAGE_COMM_ID,
                'to_stage_id': STAGE_DECISION_ID,
                'action_name': 'COMPLETE_REVIEW',
                'allowed_roles': ['ADMIN', 'AICTE_OFFICIAL'],
                'requires_remarks': False,
                'resulting_status': 'UNDER_REVIEW',
                'is_active': True,
                'created_at': now,
            },
            # Decision -> Decision: Record Decision (Official action)
            {
                'id': uuid.uuid4(),
                'workflow_definition_id': EOA_WF_ID,
                'from_stage_id': STAGE_DECISION_ID,
                'to_stage_id': STAGE_DECISION_ID,
                'action_name': 'RECORD_DECISION',
                'allowed_roles': ['ADMIN', 'AICTE_OFFICIAL'],
                'requires_remarks': True,
                'resulting_status': 'APPROVED',
                'is_active': True,
                'created_at': now,
            },
            # Decision -> Decision: Close Application
            {
                'id': uuid.uuid4(),
                'workflow_definition_id': EOA_WF_ID,
                'from_stage_id': STAGE_DECISION_ID,
                'to_stage_id': STAGE_DECISION_ID,
                'action_name': 'CLOSE_APPLICATION',
                'allowed_roles': ['ADMIN'],
                'requires_remarks': False,
                'resulting_status': 'CLOSED',
                'is_active': True,
                'created_at': now,
            },
        ],
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            f"DELETE FROM workflow_transitions WHERE workflow_definition_id = '{EOA_WF_ID}';"
        )
    )
    op.execute(
        sa.text(
            f"DELETE FROM workflow_stages WHERE workflow_definition_id = '{EOA_WF_ID}';"
        )
    )
    op.execute(
        sa.text(
            f"DELETE FROM workflow_definitions WHERE id = '{EOA_WF_ID}';"
        )
    )
