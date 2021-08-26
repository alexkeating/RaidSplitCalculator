import discord
from dataclasses import dataclass
from typing import Dict, Optional, List
from texttable import Texttable
from statistics import mean, geometric_mean

UserId = str
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
    A class that holds the raid proposals of a raid.
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

        # Add new_member to all existing raid proposals
        for _, proposal in self.proposals.items():
            if not proposal.get(new_member):
                proposal[new_member] = None

        # Create a new raid proposal for new_member and add all existing members
        if not self.proposals.get(new_member, None):

            new_members_proposal = self.proposals[new_member] = {}

            # add others
            existing_members = self.proposals.keys()
            for existing_member in existing_members:
                new_members_proposal[existing_member] = None

            # add self
            new_members_proposal[new_member] = None

    def is_admin(self, member: UserId) -> bool:
        if member != self.admin:
            return False
        else:
            return True

    def get_member_names(self):
        member_names: List[str] = []
        for member, percentage in self.member_infos.items():
            member_names.append(self.member_infos[member].name)
        return member_names

    def get_member_ids(self) -> List[str]:
        member_ids: List[str] = []
        for member, percentage in self.member_infos.items():
            member_ids.append(self.member_infos[member].id)
        return member_ids

    def calculate_share(self, member: UserId) -> bool:
        # iterate over all members
        proposed_shares: List[float] = []

        for _, proposal in self.proposals.items():
            proposed_shares.append(proposal.get(member, None))

        allocations_incomplete = any(x is None for x in proposed_shares)
        if allocations_incomplete:
            return False

        member_info: MemberInfo = self.member_infos.get(member)
        member_info.mean_share = mean(proposed_shares)
        member_info.geom_mean_share = geometric_mean(proposed_shares)

        return not allocations_incomplete

    def update_shares(self):
        # iterate over all members
        for proposer, _ in self.proposals.items():
            self.calculate_share(proposer)

    def build_member_table(self, proposer: UserId):
        rows = []
        for proposer, percentage in self.proposals.get(proposer).items():
            rows.append([self.member_infos[proposer].name, percentage])

        return self.build_table(["Teammate", "Proposed Split"], rows)

    def build_summary_table(self):
        rows = []
        for proposer, inner_dict in self.proposals.items():
            is_first = True
            for teammate, percentage in inner_dict.items():
                rows.append([self.member_infos[proposer].name if is_first else "",
                             self.member_infos[teammate].name,
                             percentage])
                is_first = False

        return self.build_table(["Proposer", "Teammate", "Proposed Split"], rows)

    def build_table(self, header, rows):
        table = Texttable()
        table.add_rows([header, *rows])
        return table.draw()


RaidDict = Dict[str, Raid]
