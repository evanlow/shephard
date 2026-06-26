from __future__ import annotations

from datetime import datetime

from ..extensions import db
from ..models.group import Group
from ..models.member import Member
from ..models.membership import member_groups
from .group_service import GroupService
from .member_remarks import REMARKS_MAX_LENGTH


def _normalize_remarks(value, field_name: str = "Remarks") -> tuple[str | None, str | None]:
    """Return (normalized_value, error). None means "not provided / cleared"."""
    if value is None:
        return None, None
    text = str(value).strip()
    if not text:
        return None, None
    if len(text) > REMARKS_MAX_LENGTH:
        return None, f"{field_name} must be {REMARKS_MAX_LENGTH} characters or fewer"
    return text, None


def _resolve_membership(
    group_ids: list[int] | None,
    primary_group_id: int | None,
) -> tuple[Group, list[Group] | None, str | None]:
    default_group = GroupService.get_default_group()
    resolved_groups: list[Group] = []
    seen_ids = {default_group.id}
    primary_group = default_group

    candidate_ids = list(group_ids or [])
    if primary_group_id is not None:
        candidate_ids.insert(0, primary_group_id)

    if candidate_ids:
        first_group = db.session.get(Group, int(candidate_ids[0]))
        if not first_group:
            return default_group, None, f"Group {candidate_ids[0]} not found"
        primary_group = first_group
        if first_group.id not in seen_ids:
            resolved_groups.append(first_group)
            seen_ids.add(first_group.id)

        for raw_group_id in candidate_ids[1:]:
            if raw_group_id is None:
                continue
            group = db.session.get(Group, int(raw_group_id))
            if not group:
                return default_group, None, f"Group {raw_group_id} not found"
            if group.id not in seen_ids:
                resolved_groups.append(group)
                seen_ids.add(group.id)

    return primary_group, [default_group, *resolved_groups], None


class MemberService:
    @staticmethod
    def get_all() -> list[Member]:
        return db.session.execute(db.select(Member).order_by(Member.name)).scalars().all()

    @staticmethod
    def get_by_id(member_id: int) -> Member | None:
        return db.session.get(Member, member_id)

    @staticmethod
    def create(
        name: str,
        group_ids: list[int] | None = None,
        group_id: int | None = None,
        remarks: str | None = None,
    ) -> tuple[Member | None, str | None]:
        primary_group, groups, error = _resolve_membership(group_ids, group_id)
        if error:
            return None, error

        normalized_remarks, remarks_error = _normalize_remarks(remarks)
        if remarks_error:
            return None, remarks_error

        member = Member(name=name, group_id=primary_group.id, remarks=normalized_remarks)
        member.groups = groups or []
        db.session.add(member)
        db.session.commit()
        return member, None

    @staticmethod
    def update(
        member_id: int,
        name: str | None = None,
        group_ids: list[int] | None = None,
        group_id: int | None = None,
        groups_provided: bool = False,
        remarks: str | None = None,
        remarks_provided: bool = False,
    ) -> tuple[Member | None, str | None]:
        member = db.session.get(Member, member_id)
        if not member:
            return None, "Member not found"

        if name:
            member.name = name

        if groups_provided:
            primary_group, groups, error = _resolve_membership(group_ids, group_id)
            if error:
                return None, error
            member.group_id = primary_group.id
            member.groups = groups or []

        if remarks_provided:
            normalized_remarks, remarks_error = _normalize_remarks(remarks)
            if remarks_error:
                return None, remarks_error
            member.remarks = normalized_remarks

        db.session.commit()
        return member, None

    @staticmethod
    def delete(member_id: int) -> bool:
        member = db.session.get(Member, member_id)
        if not member:
            return False
        db.session.delete(member)
        db.session.commit()
        return True

    @staticmethod
    def deactivate(
        member_id: int,
        deactivated_at: datetime,
        deactivation_reason: str | None = None,
    ) -> tuple[Member | None, str | None]:
        """Mark a member as inactive from deactivated_at (their last active day).

        deactivated_at should be stored as end-of-day (23:59:59) so that events
        on the same calendar day still include the member; events on later dates do not.

        A non-empty deactivation_reason is required and is enforced here (not
        only in the UI) so that future UI/API paths cannot bypass it.
        """
        member = db.session.get(Member, member_id)
        if not member:
            return None, "Member not found"
        if member.deactivated_at is not None:
            return None, "Member is already inactive"

        normalized_reason, reason_error = _normalize_remarks(deactivation_reason, "Deactivation reason")
        if reason_error:
            return None, reason_error
        if not normalized_reason:
            return None, "Deactivation reason is required"

        member.deactivated_at = deactivated_at
        member.deactivation_reason = normalized_reason
        db.session.commit()
        return member, None

    @staticmethod
    def reactivate(member_id: int, rejoined_at: datetime) -> tuple[Member | None, str | None]:
        """Reactivate an inactive member.

        Clears deactivated_at and deactivation_reason, and updates joined_at for
        all group memberships to rejoined_at, so the member appears in events
        from that date onward but is correctly excluded from the gap period
        between their departure and return. The free-text ``remarks`` note is
        preserved across reactivation.
        """
        member = db.session.get(Member, member_id)
        if not member:
            return None, "Member not found"
        if member.deactivated_at is None:
            return None, "Member is already active"
        member.deactivated_at = None
        member.deactivation_reason = None
        db.session.execute(
            member_groups.update()
            .where(member_groups.c.member_id == member_id)
            .values(joined_at=rejoined_at)
        )
        db.session.commit()
        return member, None
