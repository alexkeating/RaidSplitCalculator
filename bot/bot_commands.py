from discord import Member
from discord.ext import commands
from raid import Raid, UserId, MemberInfo
from database import RAIDS, find_raid

from helpers import sender_is_admin, get_member_ids, get_member_names, \
    update_shares, calculate_share, build_summary_table, build_member_table

bot = commands.Bot(command_prefix="!")


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
async def split(ctx, raid_name, raiders: commands.Greedy[Member]):
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


@splitter.command(help="Close the split (admin only)")
async def close(ctx, raid_name):
    raid = find_raid(raid_name)

    if await sender_is_admin(ctx, raid):
        raid.is_open = False
        # TODO send to all member
        await ctx.send(f"The split for raid **{raid_name}** has been closed.")
