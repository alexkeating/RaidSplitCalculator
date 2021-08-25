import discord
from dataclasses import dataclass
from typing import Dict, Tuple, Optional, List
from texttable import Texttable
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

    def build_member_table(self, member: UserId):
        splits = self.proposals.get(member)
        rows = []
        for member, percentage in splits.items():
            rows.append([self.member_infos[member].name, percentage])

        table = Texttable()
        table.add_rows([["Teammate", "Proposed Split"], *rows])
        return table.draw()

    def calculate_share(self, user_id: UserId) -> bool:
        # iterate over all members
        proposed_shares: List[float] = []

        for _, proposal in self.proposals.items():
            proposed_shares.append(proposal.get(user_id, None))

        allocations_incomplete = any(x is None for x in proposed_shares)
        if allocations_incomplete:
            return False

        current_member_info: MemberInfo = self.member_infos.get(user_id)
        current_member_info.mean_share = mean(proposed_shares)
        current_member_info.geom_mean_share = geometric_mean(proposed_shares)

        return not allocations_incomplete

    def update_shares(self):
        # iterate over all members
        for current_member, _ in self.proposals.items():
            self.calculate_share(current_member)

    def build_summary_table(self):
        rows = []
        for outer_member, inner_dict in self.proposals.items():
            for inner_member, percentage in inner_dict.items():
                rows.append([self.member_infos[outer_member].name,
                             self.member_infos[inner_member].name,
                             percentage])

        table = Texttable()
        table.add_rows([["Proposer", "Teammate", "Proposed Split"], *rows])
        return table.draw()


RaidDict = Dict[str, Raid]
