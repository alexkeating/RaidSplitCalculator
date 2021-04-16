import discord
import logging
import os
import sys

from dataclasses import dataclass
from discord.ext import commands
from texttable import Texttable
from typing import Dict, List, Union

logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO)
logger.info("Starting RaidSplitBot")

TOKEN = os.getenv("API_TOKEN")
if TOKEN is None:
    sys.exit("Environment variable API_TOKEN must be supplied")

bot = commands.Bot(command_prefix="!")


# TODO: Should be replaced with storage backend
RAIDS = {}


@dataclass
class SplitMember:
    info: discord.Member
    split_percent: int


@dataclass
class SplitGroup:
    members: Dict[int, SplitMember]
    # It is a Dict of
    # id member to dictionary id member with proposed split
    proposed_splits: Dict[int, Dict[int, SplitMember]]

    def add_member(self, raider: discord.Member):
        split_member = SplitMember(info=raider, split_percent=0)

        # Add member to members
        self.members[raider.id] = split_member

        # Add member to proposed splits
        for member_id, splits in self.proposed_splits.items():
            if not splits.get(raider.id):
                splits[raider.id] = split_member

        # Add proposed splits for new member
        if not self.proposed_splits.get(raider.id, None):
            self.proposed_splits[raider.id] = {
                id_: member for id_, member in self.members.items()
            }


def build_member_table(member: int, group: SplitGroup):
    splits = group.proposed_splits.get(member.id)
    rows = []
    for member, split in splits.items():
        rows.append([split.info.name, split.split_percent])

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


def build_summary_table(group: SplitGroup):
    rows = []
    for member, splits in group.proposed_splits.items():
        for teammate, split in splits.items():
            user = group.members.get(member)
            rows.append([user.info.name, split.info.name, split.split_percent])

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


def verify_allocation(proposed_splits):
    allocation_used = 0
    for member_id, split in proposed_splits.items():
        allocation_used += split.split_percent
        if allocation_used > 100:
            return False
    return True


@bot.command(help="Send anonymous suggestion")
async def split(ctx, raid_name, raiders: commands.Greedy[discord.Member]):
    """
    Command a PM will call when they want to run a split scenario
    """
    raid_name = raid_name.trim()
    group = SplitGroup(members={}, proposed_splits={})
    if RAIDS.get(raid_name):
        await ctx.send("Raid Already exists please use a different name!")
        return

    RAIDS[raid_name] = group
    for raider in raiders:
        group.add_member(raider)
        await raider.send(
            f"Hi your input has been requested for raid: {raid_name} \n Please "
            "use the `!allocate <raid_name> <member_handle> <allocation>`. Your "
            "allocations should be a number from 0 to 100 \n\n"
            "If you make a mistake use the `!edit` command to modify your allocation"
        )


@bot.command()
async def allocate(ctx, raid_name, member: discord.User, allocation: int):
    """
    This command is meant to be used in a DM and where a raider will specify
    what they think a fair allocation is for a specific user

    """
    raid_name = raid_name.trim()
    raid = RAIDS.get(raid_name)
    proposed_allocs = raid.proposed_splits.get(ctx.author.id)
    if proposed_allocs is None:
        await ctx.send("You are not in the raid party")
        return
    old_allocation = proposed_allocs.get(member.id, None)
    if old_allocation is None:
        await ctx.send("That user is not in the raid party")
        return

    raid.proposed_splits[ctx.author.id][member.id] = SplitMember(
        info=member, split_percent=allocation
    )
    valid = verify_allocation(proposed_allocs)
    if not valid:
        # Rollback
        raid.proposed_splits[ctx.author.id][member.id] = SplitMember(
            info=member, split_percent=old_allocation
        )
        await ctx.send("This modification makes your allocations above 100")
        return

    table = build_member_table(member, raid)

    await ctx.send(f"Your curent entries are \n ```{table}```")


@bot.command()
async def summary(ctx, raid_name):
    """
    This command will show the allocations specified for all raiders
    in a specific raid
    """
    raid_name = raid_name.trim()
    raid = RAIDS.get(raid_name)
    table = build_summary_table(raid)
    await ctx.send(f"The current entries are \n ```{table}```")


@bot.command()
async def edit(ctx, raid_name, member: discord.User, split: int):
    """
    This command allows a raider to modify their proposed allocation
    """
    raid_name = raid_name.trim()
    raid = RAIDS.get(raid_name)
    author_proposals = raid.proposed_splits.get(ctx.author.id, None)
    if not author_proposals:
        await ctx.send("You are not a part of this raid")
        return
    old_proposal = author_proposals.get(member.id, None)
    if old_proposal is None:
        await ctx.send("The referred to member is not part of the raid party")
        return

    raid.proposed_splits[ctx.author.id][member.id] = SplitMember(
        info=member, split_percent=split
    )
    valid = verify_allocation(author_proposals)
    if not valid:
        # Rollback
        raid.proposed_splits[ctx.author.id][member.id] = SplitMember(
            info=member, split_percent=old_proposal
        )
        await ctx.send("This modification makes your allocations above 100")
        return

    table = build_member_table(member, raid)

    await ctx.send(f"Your curent entries are \n ```{table}```")


bot.run(TOKEN)
