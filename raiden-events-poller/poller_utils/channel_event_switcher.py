"""Event switcher for channel events"""
from typing import Dict
from raiden_contracts.constants import ChannelEvent


class UnknownEventError(ValueError):
    """Raised when an unknown event occurs"""

    pass


class NotAnEventError(AttributeError):
    """Raised when the attribute is not a raiden event"""

    pass


def opened_channel(event: Dict) -> str:
    """Details the event of the creation of a new channel"""
    fparty = event["args"]["participant1"]
    sparty = event["args"]["participant2"]
    return f":\tfparty = {fparty}\tsparty = {sparty}"


def new_deposit(event: Dict) -> str:
    """Details the event of a new deposit"""
    total_deposit = event["args"]["total_deposit"]
    party = event["args"]["participant"]
    return f": new total deposit {total_deposit} by {party}"


# pylint: disable=W0613
def balance_proof_updated(event: Dict) -> str:
    """Details a balance proof related event"""
    raise NotImplementedError


# pylint: disable=W0613
def withdraw(event: Dict) -> str:
    """Details a whitdrawal event"""
    raise NotImplementedError


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

    return switcher.get(event_name, unkown_event)(event)
