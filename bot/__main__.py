import logging
import os
import sys
import jsonpickle
import discord
from discord.ext import commands
from dataclasses import dataclass
from shutil import copyfile
from texttable import Texttable
from typing import Dict, List, Tuple, Optional
from statistics import mean, geometric_mean

UserId = str
SplitMember = Tuple[int, str]
SplitProposal = Dict[UserId, Optional[float]]


@dataclass
class MemberInfo:
    id: str
    name: str
    mean_share: Optional[float]
    geom_mean_share: Optional[float]


@dataclass
class Raid:
    """
    Command a
    """
    admin: UserId
    proposals: Dict[UserId, SplitProposal]
    member_infos: Dict[UserId, MemberInfo]
    is_open: bool

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
    return raids


def close_db(raids: RaidDict, db_path: str, db_backup_path: str):
    file = open(db_path, 'w')
    file.write(jsonpickle.encode(raids))

    os.remove(db_backup_path)


@bot.group()
async def splitter(ctx):
    if ctx.invoked_subcommand is None:
        await ctx.send(f"Subcommand {ctx.subcommand_passed} is not a valid subcommand!")


@splitter.command()
async def help(ctx):
    commands = bot.all_commands
    group = commands.get("splitter")
    await ctx.send_help(group)


@splitter.command(help="Send out a message to split a raid and become the admin")
async def split(ctx, raid_name, raiders: commands.Greedy[discord.Member]):
    """
    Command a PM will call when they want to run a split scenario.
    The sender becomes the admin of the proposal.
    """

    raid_name = raid_name.strip()
    if RAIDS.get(raid_name):
        await ctx.send(f"Raid **{raid_name}** already exists please use a different name!")
        return

    raid = Raid(admin=UserId(ctx.author.id), proposals={}, member_infos={}, is_open=True)
    RAIDS[raid_name] = raid

    await ctx.send(f"A raid wit the name **{raid_name}** and **{len(raiders)}** members was created.")

    for raider in raiders:
        new_member: UserId = UserId(raider.id)
        raid.add_member(raider)
        await raider.send(
            f"Hi {raid.member_infos[new_member].name}. Your input has been requested for the **{raid_name}** raid.\n"
            "Please use the `!splitter allocate <raid_name> <member_handle> <allocation>`. "
            "Your allocations should be a number greater 0 and smaller 100 \n\n"
            "If you make a mistake use the `!splitter allocate` again to modify your allocation."
        )

async def sender_is_admin(ctx, raid: Raid) -> bool:
    sender: UserId = UserId(ctx.author.id)

    if sender != raid.admin:
        await ctx.send(f"You are **not the admin**.")
        return False
    else:
        return True

@splitter.command(help="Close the split (admin only)")
async def close(ctx, raid_name):

    raid = find_raid(raid_name)

    if await sender_is_admin(ctx, raid):
        raid.is_open = False
        # TODO send to all member
        await ctx.send(f"The split for raid **{raid_name}** has been closed.")



def find_raid(raid_name: str) -> Raid:
    raid_name = raid_name.strip()
    return RAIDS.get(raid_name)


def part_of_raid(raid_name: str, split_member: UserId) -> bool:
    res = find_raid(raid_name).proposals.get(UserId(split_member))
    return res is not None


@splitter.command(help="Return all members of the raid.")
async def members(ctx, raid_name):
    """
    This command returns all members. It is intended to be used before submitting the allocations.
    """
    raid = find_raid(raid_name)
    member_names = get_member_names(raid)

    await ctx.send(f"The raid **{raid_name}** has **{len(member_names)}** members:\n"
                   f"*{', '.join(member_names)}*\n"
                   f"Use the command `allocate` to specify their shares in the same order.")


def get_member_names(raid):
    member_names: List[str] = []
    for member, percentage in raid.member_infos.items():
        member_names.append(raid.member_infos[member].name)
    return member_names


def get_member_ids(raid) -> List[str]:
    member_ids: List[str] = []
    for member, percentage in raid.member_infos.items():
        member_ids.append(raid.member_infos[member].id)
    return member_ids


@splitter.command(help="Allocate a percentage of the spoils in the order of the command `members`")
async def allocate(ctx, raid_name, percentages: commands.Greedy[float]):
    """
    This command allocates shares to all members specified in the order of the members command.
    """
    raid = find_raid(raid_name)
    members_ids = get_member_ids(raid)

    if len(members_ids) is not len(percentages):
        await ctx.send(f"The number of allocations **{len(percentages)}** "
                       f"does not match the number of **{len(members_ids)}**.")
        await members(ctx, raid_name)
        return
    elif sum(percentages) != 100.0:
        await ctx.send(f"The percentages must add up to **{100}**.")
        return
    elif any(x <= 0 or x >= 100 for x in percentages):
        await ctx.send(f"The percentages must greater than 0 and smaller than 100.")
        return

    # fetch sender proposal
    sender: UserId = UserId(ctx.author.id)
    sender_proposal = raid.proposals.get(sender)

    # iterate over all beneficiaries in member info
    for i, beneficiary in enumerate(members_ids):
        raid.proposals[sender][beneficiary] = percentages[i]

    await update_shares(ctx, raid)

    table = build_member_table(sender, raid)
    await ctx.send(f"Your current entries are \n ```{table}```")


@splitter.command(help="Get a summary of the proposed allocations for a raid (admin only)")
async def summary(ctx, raid_name):
    """
    This command will show the allocations specified for all raiders
    in a specific raid
    """
    sender: UserId = UserId(ctx.author.id)
    raid_name = raid_name.strip()
    raid = RAIDS.get(raid_name)

    if await sender_is_admin(ctx, raid):
        table = build_summary_table(raid)
        await ctx.send(f"The current entries are \n ```{table}```")


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


@splitter.command(help="Get your averaged shares.")
async def share(ctx, raid_name):
    raid = find_raid(raid_name)
    sender = UserId(ctx.author.id)

    sender_info: MemberInfo = raid.member_infos.get(sender)

    all_calculated = calculate_share(ctx, raid, sender)

    if not all_calculated:
        await ctx.send(
            f"Your share cannot be calculated because some allocations are still missing.\n"
            f"Consider reminding the other members to use the "
            f"`!splitter allocate {raid_name} <allocations>` "
            f"command.\n\n")
    else:
        await ctx.send(
            f"Your arithmetic mean share is **{sender_info.mean_share:.1f} %** and\n"
            f"your geometric mean share is **{sender_info.geom_mean_share:.1f} %**.")


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


RAIDS = init_db(DB_PATH, DB_BACKUP_PATH)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
logger.info("Starting RaidSplitBot")

bot.run(TOKEN)

close_db(RAIDS, DB_PATH, DB_BACKUP_PATH)
