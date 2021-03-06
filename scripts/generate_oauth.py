import os
from discord import Client
from discord.permissions import Permissions
from discord.utils import oauth_url


def generate_oauth():
    client_id = os.getenv("CLIENT_ID", "")
    guild_id = os.getenv("GUILD_ID", "")
    # Has send messages permisison
    permissions = Permissions(permissions=2048)
    Client().get_guild(guild_id)
    generated_url = oauth_url(client_id, permissions)
    print(f"Generated oauth for given client id: {generated_url}")


if __name__ == "__main__":
    generate_oauth()
