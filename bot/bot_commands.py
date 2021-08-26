import discord
from discord import Member
from discord.ext import commands
from raid import Raid, UserId, MemberInfo
from database import RaidDB

bot = commands.Bot(command_prefix="!")


@bot.group(help="Splits the spoils of a raid.")
async def split(ctx):
    if ctx.invoked_subcommand is None:
        await ctx.send(f"Subcommand {ctx.subcommand_passed} is not a valid subcommand!")


@split.command(help="Shows this message.")
async def help(ctx):
    commands = bot.all_commands
    print(commands)
    group = commands.get("split")
    await ctx.send_help(group)


@split.command(help="Initiate a raid and specify its members")
async def raid(ctx, raid_name, raiders: commands.Greedy[Member]):
    """
    Command a PM will call when they want to run a raid scenario.
    The sender becomes the admin of the proposal.
    """

    raid_name = raid_name.strip()
    if RaidDB().find_raid(raid_name) is not None:
        await ctx.send(f"Raid **{raid_name}** already exists please use a different name!")
        return

    raid = Raid(admin=UserId(ctx.author.id), proposals={}, member_infos={}, is_open=True)

    await ctx.send(f"A raid wit the name **{raid_name}** and **{len(raiders)}** members was created.")

    for raider in raiders:
        new_member: UserId = UserId(raider.id)
        raid.add_member(raider)
        await raider.send(
            f"Hi {raid.member_infos[new_member].name}. Your input has been requested for the **{raid_name}** raid.\n"
            "Please use the `!split allocate <raid_name> <member_handle> <allocation>`. "
            "Your allocations should be a number greater 0 and smaller 100 \n\n"
            "If you make a mistake use the `!split allocate` again to modify your allocation."
        )

    RaidDB().store(raid_name, raid)


@split.command(help="Show all raid members.")
async def members(ctx, raid_name):
    """
    This command returns all members. It is intended to be used before submitting the allocations.
    """
    raid = RaidDB().find_raid(raid_name)
    member_names = raid.get_member_names()

    await ctx.send(f"The raid **{raid_name}** has **{len(member_names)}** members:\n"
                   f"*{', '.join(member_names)}*\n"
                   f"Use the command `allocate` to specify their shares in the same order.")


@split.command(
    help="Allocate percentages to all raid members as ordered in the `!split members <raid_name>` command.")
async def allocate(ctx, raid_name, percentages: commands.Greedy[float]):
    """
    This command allocates shares to all members specified in the order of the members command.
    """
    raid = RaidDB().find_raid(raid_name)

    if not raid.is_open:
        return await ctx.send(f"The raid **{raid_name}** has already been closed.")

    members_ids = raid.get_member_ids()

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

    sender: UserId = UserId(ctx.author.id)
    # iterate over senders beneficiaries in member info
    for i, beneficiary in enumerate(members_ids):
        raid.proposals[sender][beneficiary] = percentages[i]

    raid.update_shares()
    RaidDB().store(raid_name, raid)

    await show(ctx, raid_name)


@split.command(help="Show your averaged shares.")
async def share(ctx, raid_name):
    raid = RaidDB().find_raid(raid_name)
    sender = UserId(ctx.author.id)

    sender_info: MemberInfo = raid.member_infos.get(sender)

    all_calculated = raid.calculate_share(sender)

    if not all_calculated:
        await ctx.send(
            f"Your share cannot be calculated because some allocations are still missing.\n"
            f"Consider reminding the other members to use the "
            f"`!split allocate {raid_name} <allocations>` "
            f"command.\n\n")
    else:
        await ctx.send(share_message_text(raid_name, sender_info, not raid.is_open))


def share_message_text(raid_name: str, info: MemberInfo, is_final: bool) -> str:
    return f"Your shares for raid** {raid_name} %**:\n" \
           f"Arithmetic mean: **{info.mean_share:.1f} %**\n" \
           f"Geometric  mean: **{info.geom_mean_share:.1f} %**\n" \
           f"*This is **{'final' if is_final else 'not final'}**.*"


@split.command(help="Show your allocations.")
async def show(ctx, raid_name):
    raid = RaidDB().find_raid(raid_name)
    sender = UserId(ctx.author.id)

    table = raid.build_member_table(sender)
    await ctx.send(f"```{table}```")


@split.command(help="Get a summary of the proposed allocations for a raid (admin only)")
async def summary(ctx, raid_name):
    """
    This command will show the allocations specified for all raiders
    in a specific raid
    """
    sender = UserId(ctx.author.id)
    raid_name = raid_name.strip()
    raid = RaidDB().find_raid(raid_name)

    if raid.is_admin(sender):
        table = raid.build_summary_table()
        await ctx.send(f"```{table}```")
    else:
        await ctx.send(f"You are **not the admin**.")


@split.command(help="Close the raid (admin only)")
async def close(ctx, raid_name):
    raid = RaidDB().find_raid(raid_name)

    sender = UserId(ctx.author.id)
    if not raid.is_open:
        await ctx.send(f"The raid **{raid_name}** has already been closed.")
    elif False:
        # TODO check if allocations are missing
        pass
    elif raid.is_admin(sender):
        raid.is_open = False

        RaidDB().store(raid_name, raid)


        # TODO send to all member
        await ctx.send(f"The raid for raid **{raid_name}** has been closed.")

        for id, info in raid.member_infos.items():
            user: discord.User = await bot.fetch_user(int(id))
            await user.send(share_message_text(raid_name, info, True))
    else:
        await ctx.send(f"You are **not the admin**.")
