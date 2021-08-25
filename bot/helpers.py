from raid import Raid, UserId, MemberInfo
from typing import List
from statistics import mean, geometric_mean
from texttable import Texttable


async def sender_is_admin(ctx, raid: Raid) -> bool:
    sender: UserId = UserId(ctx.author.id)

    if sender != raid.admin:
        await ctx.send(f"You are **not the admin**.")
        return False
    else:
        return True

# TODO TODO put into Raid
def get_member_names(raid: Raid):
    member_names: List[str] = []
    for member, percentage in raid.member_infos.items():
        member_names.append(raid.member_infos[member].name)
    return member_names


def get_member_ids(raid: Raid) -> List[str]:
    member_ids: List[str] = []
    for member, percentage in raid.member_infos.items():
        member_ids.append(raid.member_infos[member].id)
    return member_ids


def build_member_table(member: UserId, raid: Raid):
    splits = raid.proposals.get(member)
    rows = []
    for member, percentage in splits.items():
        rows.append([raid.member_infos[member].name, percentage])

    table = Texttable()
    table.add_rows(
        [
            [
                "Teammate",
                "Proposed Split",
            ],
            *rows,
        ]
    )
    return table.draw()


def calculate_share(_ctx, raid: Raid, user_id: UserId) -> bool:
    # iterate over all members
    proposed_shares: List[float] = []

    for _, proposal in raid.proposals.items():
        proposed_shares.append(proposal.get(user_id, None))

    allocations_incomplete = any(x is None for x in proposed_shares)
    if allocations_incomplete:
        # await ctx.send(f"Some allocations are missing.")
        return False

    current_member_info: MemberInfo = raid.member_infos.get(user_id)
    current_member_info.mean_share = mean(proposed_shares)
    current_member_info.geom_mean_share = geometric_mean(proposed_shares)

    return not allocations_incomplete


async def update_shares(ctx, raid: Raid):
    # iterate over all members
    for current_member, _ in raid.proposals.items():
        calculate_share(ctx, raid, current_member)


# TODO should maybe be accessible only by PMs
def build_summary_table(group: Raid):
    rows = []
    for outer_member, inner_dict in group.proposals.items():
        for inner_member, percentage in inner_dict.items():
            rows.append([group.member_infos[outer_member].name,
                         group.member_infos[inner_member].name,
                         percentage])

    table = Texttable()
    table.add_rows(
        [
            [
                "Proposer",
                "Teammate",
                "Proposed Split",
            ],
            *rows,
        ]
    )
    return table.draw()
