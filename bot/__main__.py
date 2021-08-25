import logging
import os
import sys
import jsonpickle
import discord
from discord.ext import commands
from dataclasses import dataclass
from shutil import copyfile
from texttable import Texttable
from typing import Dict, Tuple, Optional
from statistics import mean, geometric_mean

UserId = str
SplitMember = Tuple[int, str]


@dataclass
class MemberInfo:
    id: str
    name: str
    mean_share: Optional[float]
    geom_mean_share: Optional[float]


@dataclass
class Raid:
    SplitProposal = Dict[UserId, Optional[float]]

    # It is a Dict of
    # id member to dictionary id member with proposed split
    proposals: Dict[UserId, SplitProposal]
    member_infos: Dict[UserId, MemberInfo]

    def add_member(self, raider: discord.User):
        new_member = UserId(raider.id)
        self.member_infos[new_member] = MemberInfo(id=UserId(raider.id),
                                                   name=raider.name,
                                                   mean_share=None,
                                                   geom_mean_share=None)

        # Add new_member to all existing split proposals
        for _, proposal in self.proposals.items():
            if not proposal.get(new_member):
                proposal[new_member] = None

        # Create a new split proposal for new_member and add all existing members
        if not self.proposals.get(new_member, None):

            new_members_proposal = self.proposals[new_member] = {}

            # add others
            existing_members = self.proposals.keys()
            for existing_member in existing_members:
                new_members_proposal[existing_member] = None

            # add self
            new_members_proposal[new_member] = None


RaidDict = Dict[str, Raid]

TOKEN = os.getenv("API_TOKEN")
if TOKEN is None:
    sys.exit("Environment variable API_TOKEN must be supplied")

bot = commands.Bot(command_prefix="!")

RAIDS: RaidDict = {}

DB_PATH = os.getenv("DB_PATH")
DB_BACKUP_PATH = DB_PATH + '.bckp'


def init_db(db_path: str, db_backup_path: str) -> RaidDict:
    if os.path.isfile(db_backup_path):
        raise IOError("Backup file exists already. Last time, Something went wrong ")

    try:
        # backup the db and open
        copyfile(db_path, db_backup_path)
        file = open(db_path)
    except IOError:
        # If db not exists, create the file and populate with an empty dict
        file = open(db_path, 'w+')
        file.write(" {}")
        file.close()

        # backup the db and open
        copyfile(db_path, db_backup_path)
        file = open(db_path)

    raids: RaidDict = jsonpickle.decode(file.read())

    print("Raids DB:\n", raids)

    return raids


def close_db(raids: RaidDict, db_path: str, db_backup_path: str):
    print("Raids DB:\n", raids)

    file = open(db_path, 'w')
    file.write(jsonpickle.encode(raids))

    os.remove(db_backup_path)


def verify_allocation(proposed_splits: Dict[SplitMember, float]):
    allocation_used = 0
    for _, percentage in proposed_splits.items():
        allocation_used += percentage
        if allocation_used > 100:
            return False
    return True


@bot.group()
async def splitter(ctx):
    if ctx.invoked_subcommand is None:
        await ctx.send(f"Subcommand {ctx.subcommand_passed} is not a valid subcommand!")


@splitter.command()
async def help(ctx):
    commands = bot.all_commands
    group = commands.get("splitter")
    await ctx.send_help(group)


@splitter.command(help="Send out a message to split a raid")
async def split(ctx, raid_name, raiders: commands.Greedy[discord.Member]):
    """
    Command a PM will call when they want to run a split scenario
    """

    raid_name = raid_name.strip()
    group = Raid(proposals={}, member_infos={})
    if RAIDS.get(raid_name):
        await ctx.send("Raid Already exists please use a different name!")
        return

    RAIDS[raid_name] = group
    for raider in raiders:
        new_member: UserId = UserId(raider.id)
        print(new_member)
        group.add_member(raider)
        await raider.send(
            f"Hi {group.member_infos[new_member].name}. Your input has been requested for the **{raid_name}** raid.\n"
            "Please use the `!splitter allocate <raid_name> <member_handle> <allocation>`. "
            "Your allocations should be a number from 0 to 100 \n\n"
            "If you make a mistake use the `!splitter edit` command to modify your allocation"
        )


def find_raid(raid_name: str) -> Raid:
    raid_name = raid_name.strip()
    return RAIDS.get(raid_name)


def part_of_raid(raid_name: str, split_member: UserId) -> bool:
    res = find_raid(raid_name).proposals.get(UserId(split_member))
    return res is not None


@splitter.command(help="Allocate a percentage of the spoils")
async def allocate(ctx, raid_name, member: discord.User, split: float):
    """
    This command is meant to be used in a DM and where a raider will specify
    what they think a fair allocation is for a specific user

    """
    percentage = split

    raid_name = raid_name.strip()
    raid = find_raid(raid_name)
    if raid is None:
        await ctx.send(f"Raid **{raid_name}** not found.")
        return

    sender: UserId = UserId(ctx.author.id)
    beneficiary: UserId = UserId(member.id)

    # check if sender is part of the raid
    if not part_of_raid(raid_name, sender):
        await ctx.send(f"You are not in the raid party of raid **{raid_name}**")
        return

    sender_proposals = raid.proposals.get(sender, None)
    sender_proposal_for_benificiary = sender_proposals.get(beneficiary, None)

    # check if beneficiary is part of the raid
    if not part_of_raid(raid_name, beneficiary):
        await ctx.send(f"That beneficiary is not in the raid party of raid **{raid_name}**")
        return

    raid.proposals[sender][beneficiary] = percentage
    valid = verify_allocation(sender_proposals)
    if not valid:
        # Rollback
        raid.proposals[sender][beneficiary] = sender_proposal_for_benificiary
        await ctx.send("This modification makes your allocations above 100")
        return

    table = build_member_table(sender, raid)

    await update_shares(ctx, raid)

    await ctx.send(f"Your current entries are \n ```{table}```")


@splitter.command(help="Edit an existing allocation proposal")
async def edit(ctx, raid_name, member: discord.User, split: float):
    """
    This command allows a raider to modify their proposed allocation
    """

    percentage = split

    raid = find_raid(raid_name)
    if raid is None:
        await ctx.send(f"Raid **{raid_name}** not found.")
        return

    sender: UserId = UserId(ctx.author.id)
    beneficiary: UserId = UserId(member.id)

    if not part_of_raid(raid_name, sender):
        await ctx.send("You are not a part of this raid")
        return

    sender_percentage_proposal = raid.proposals.get(sender, None)
    old_percentage_proposal = sender_percentage_proposal.get(beneficiary, None)
    if old_percentage_proposal is None:  # TODO is this a good test?
        await ctx.send("The referred to member is not part of the raid party")
        return

    raid.proposals[sender][beneficiary] = percentage

    if not verify_allocation(sender_percentage_proposal):
        # Rollback
        raid.proposals[sender][beneficiary] = old_percentage_proposal
        await ctx.send("This modification makes your allocations above 100")
        return

    table = build_member_table(sender, raid)

    await ctx.send(f"Your current entries are \n ```{table}```")

    await update_shares(ctx, raid)


@splitter.command(help="Get a summary of the proposed allocations for a raid")
async def summary(ctx, raid_name):
    """
    This command will show the allocations specified for all raiders
    in a specific raid
    """
    raid_name = raid_name.strip()
    raid = RAIDS.get(raid_name)
    table = build_summary_table(raid)
    await ctx.send(f"The current entries are \n ```{table}```")


def build_member_table(member: UserId, group: Raid):
    splits = group.proposals.get(member)
    rows = []
    for member, percentage in splits.items():
        rows.append([group.member_infos[member].name, percentage])

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


@splitter.command(help="Get your averaged shares.")
async def get_share(ctx, raid_name):
    raid = find_raid(raid_name)
    sender = UserId(ctx.author.id)

    await calculate_share(ctx, raid, sender)

    sender_info: MemberInfo = raid.member_infos.get(sender)

    message = "Your arithmetic mean share is "
    if sender_info.mean_share is not None:
        message += f"**{sender_info.mean_share:.1f} %** and "
    else:
        message += f"**not available** and "

    message += "your geometric mean share is "
    if sender_info.geom_mean_share is not None:
        message += f"**{sender_info.geom_mean_share:.1f} %** and "
    else:
        message += f"**not available**."

    await ctx.send(message)


async def calculate_share(ctx, raid: Raid, user_id: UserId):
    # iterate over all members
    proposed_shares: List[float] = []

    for _, proposal in raid.proposals.items():
        proposed_shares.append(proposal.get(user_id, None))

    if any(x is None for x in proposed_shares):
        await ctx.send(f"Some allocations are missing.")
        return

    current_member_info: MemberInfo = raid.member_infos.get(user_id)

    if any(x is None for x in proposed_shares):
        await ctx.send(f"Some allocations are missing so the arithmetic mean cannot be calculated.")
    else:
        current_member_info.mean_share = mean(proposed_shares)

    if any(x == 0 for x in proposed_shares):
        await ctx.send(f"Some allocations are 0 so that the geometric mean cannot be applied.")
    else:
        current_member_info.geom_mean_share = geometric_mean(proposed_shares)


async def update_shares(ctx, raid: Raid):
    # iterate over all members
    for current_member, _ in raid.proposals.items():
        calculate_share(ctx, raid, current_member)


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


RAIDS = init_db(DB_PATH, DB_BACKUP_PATH)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
logger.info("Starting RaidSplitBot")

bot.run(TOKEN)

close_db(RAIDS, DB_PATH, DB_BACKUP_PATH)
