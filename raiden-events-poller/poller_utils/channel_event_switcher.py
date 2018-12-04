"""Event switcher for channel events"""
from typing import Dict
from raiden_contracts.constants import ChannelEvent


class UnknownEventError(ValueError):
    """Raised when an unknown event occurs"""


class NotAnEventError(AttributeError):
    """Raised when the attribute is not a raiden event"""


def opened_channel(event: Dict) -> str:
    """Details the event of the creation of a new channel"""
    p1 = event["participant1"]
    p2 = event["participant2"]
    return f" p1: {p1} p2: {p2}"


def new_deposit(event: Dict) -> str:
    """Details the event of a new deposit"""
    total_deposit = event["total_deposit"]
    party = event["participant"]
    return f" party: {party} deposit: {total_deposit}"


# pylint: disable=W0613
def balance_proof_updated(event: Dict) -> str:
    """Details a balance proof related event"""
    closing_participant = event["closing_participant"]
    nonce = event["nonce"]
    return f" closing_participant: {closing_participant} nonce: {nonce}"


# pylint: disable=W0613
def withdraw(event: Dict) -> str:
    """Details a whitdrawal event"""
    return ""


# pylint: disable=W0613
def unkown_event(event: Dict) -> str:
    """Details an unknown event"""
    return ""


def get_specific_event_info(event: Dict) -> str:
    """Return additional info based on the event type"""

    if "event" not in event.keys():
        raise NotAnEventError

    event_name = event["event"]

    switcher = {
        ChannelEvent.OPENED: opened_channel,
        ChannelEvent.DEPOSIT: new_deposit,
        ChannelEvent.BALANCE_PROOF_UPDATED: balance_proof_updated,
        ChannelEvent.WITHDRAW: withdraw,
    }

    return switcher.get(event_name, unkown_event)(event["args"])
