import discord
from dataclasses import dataclass
from typing import Dict, Tuple, Optional

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
