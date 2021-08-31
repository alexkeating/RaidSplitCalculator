import discord
import logging
from discord import Member
from discord.ext import commands
from raid import Raid, UserId, MemberInfo
from localfile_db import LocalFile

logger = logging.getLogger(__name__)

bot = commands.Bot(command_prefix="!")


@bot.group(help="Splits the spoils of a raid.")
async def split(ctx):
    if ctx.invoked_subcommand is None:
        await ctx.send(f"Subcommand {ctx.subcommand_passed} is not a valid subcommand!")


@split.command(help="Shows this message.")
async def help(ctx):
    commands = bot.all_commands
    group = commands.get("split")
    await ctx.send_help(group)


@split.command(help="Initiate a raid and specify its members")
async def raid(ctx, raid_name, raiders: commands.Greedy[Member]):
    """
    Command a PM will call when they want to run a raid scenario.
    The sender becomes the admin of the proposal.
    """

    raid_name = raid_name.strip()
    if LocalFile().find_raid(raid_name) is not None:
        await ctx.send(
            f"Raid **{raid_name}** already exists please use a different name!"
        )
        return

    raid = Raid(
        name=raid_name,
        admin=UserId(ctx.author.id),
        proposals={},
        member_infos={},
        is_open=True,
    )

    await ctx.send(
        f"A raid with the name **{raid_name}** and **{len(raiders)}** members was created."
    )

    for raider in raiders:
        new_member: UserId = UserId(raider.id)
        raid.add_member(raider)
        await raider.send(
            f"Hi {raid.member_infos[new_member].name}. Your input has been requested for the **{raid_name}** raid.\n"
            f"Please use the `!split allocate {raid_name} <allocations>`. "
            "Your allocations must be percentages between 0 and 100." 
            f"Together, they must sum up to exactly 100 and be specified in the same order as displayed in `!split members {raid_name}`. \n\n"
            f"If you make a mistake use the `!split allocate {raid_name} <allocations>` command again to modify your allocation."
        )

    LocalFile().store(raid)


@split.command(help="Show all raid members.")
async def members(ctx, raid_name):
    """
    This command returns all members. It is intended to be used before submitting the allocations.
    """
    if not raid_name:
        await ctx.send("Raid name is missing please provide a raid name!")
    raid = LocalFile().find_raid(raid_name)
    member_names = raid.get_member_names()

    await ctx.send(
        f"The raid **{raid_name}** has **{len(member_names)}** members:\n"
        f"*{', '.join(member_names)}*\n"
        f"Use the command `allocate` to specify their shares in the same order."
    )


@split.command(
    help="Allocate percentages to all raid members as ordered in the `!split members <raid_name>` command."
)
async def allocate(ctx, raid_name, percentages: commands.Greedy[float]):
    """
    This command allocates shares to all members specified in the order of the members command.
    """
    raid = LocalFile().find_raid(raid_name)

    if not raid.is_open:
        return await ctx.send(f"The raid **{raid_name}** has already been closed.")

    members_ids = raid.get_member_ids()

    if len(members_ids) is not len(percentages):
        await ctx.send(
            f"The number of allocations **{len(percentages)}** "
            f"does not match the number of **{len(members_ids)}**."
        )
        await members(ctx, raid_name)
        return
    elif sum(percentages) != 100.0:
        await ctx.send(f"The percentages must add up to **{100}**.")
        return
    elif any(x <= 0 or x > 100 for x in percentages):
        await ctx.send(f"The percentages must be between 0 and 100.")
        return

    sender: UserId = UserId(ctx.author.id)
    # iterate over senders beneficiaries in member info
    for i, beneficiary in enumerate(members_ids):
        raid.proposals[sender][beneficiary] = percentages[i]

    raid.update_shares()
    LocalFile().store(raid)

    await show(ctx, raid_name)


@split.command(help="Show your averaged shares.")
async def share(ctx, raid_name):
    raid = LocalFile().find_raid(raid_name)
    sender = UserId(ctx.author.id)

    all_calculated = raid.calculate_share(sender)

    if not all_calculated:
        await ctx.send(
            f"Your share cannot be calculated because some allocations are still missing.\n"
            f"Consider reminding the other members to use the "
            f"`!split allocate {raid_name} <allocations>` command."
        )
    else:
        await ctx.send(raid.share_message_text(sender))


@split.command(help="Show your allocations.")
async def show(ctx, raid_name):
    raid = LocalFile().find_raid(raid_name)
    sender = UserId(ctx.author.id)

    table = raid.build_member_table(sender)
    await ctx.send(f"```{table}```")


@split.command(help="Get a summary of the proposed allocations for a raid (admin only)")
async def summary(ctx, raid_name):
    """
    This command will show the allocations specified for all raiders
    in a specific raid
    """
    raid_name = raid_name.strip()
    raid = LocalFile().find_raid(raid_name)

    table = raid.build_summary_table()
    await ctx.send(f"```{table}```")


@split.command(help="Close the raid (admin only)")
async def close(ctx, raid_name):
    raid = LocalFile().find_raid(raid_name)

    sender = UserId(ctx.author.id)
    if not raid.is_open:
        await ctx.send(f"The raid **{raid_name}** has already been closed.")
    elif any(
        member_info.mean_share is None or member_info.geom_mean_share is None
        for _, member_info in raid.member_infos.items()
    ):
        await ctx.send(
            f"The raid **{raid_name}** cannot be closed because some allocations are still missing.\n"
            f"Consider reminding the other members to use "
            f"`!split allocate {raid_name} <allocations>`."
        )
    elif raid.is_admin(sender):
        raid.is_open = False

        LocalFile().store(raid)
        await ctx.send(f"The raid for raid **{raid_name}** has been closed.")

        for id, info in raid.member_infos.items():
            user: discord.User = await bot.fetch_user(int(id))
            await user.send(raid.share_message_text(id))

    else:
        await ctx.send(f"You are **not the admin**.")


@split.error
@summary.error
@close.error
@show.error
@share.error
@allocate.error
@members.error
@raid.error
async def split_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Missing required argument {error.param}")
    else:
        try:
            raise error
        except Exception:
            logging.exception("Command failed")
        await ctx.send("There was an error with your command")
