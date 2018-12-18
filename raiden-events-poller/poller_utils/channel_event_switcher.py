"""Event switcher for channel events"""
from raiden_contracts.constants import ChannelEvent
from typing import Dict
import os.path as path
import time


class UnknownEventError(ValueError):
    """Raised when an unknown event occurs"""


class NotAnEventError(AttributeError):
    """Raised when the attribute is not a raiden event"""


def opened_channel(event: Dict) -> Dict:
    """Details the event of the creation of a new channel"""

    specific_attribute = {
        "participant1": event["participant1"],
        "participant2": event["participant2"],
    }

    return specific_attribute


def closed_channel(event: Dict) -> Dict:
    """Details the event of the creation of a new channel"""

    specific_attribute = {"participant": event["closing_participant"]}

    return specific_attribute


def new_deposit(event: Dict) -> Dict:
    """Details the event of a new deposit"""

    specific_attribute = {
        "participant": event["participant"],
        "totalDeposit": event["total_deposit"],
    }

    return specific_attribute


# pylint: disable=W0613
def balance_proof_updated(event: Dict) -> Dict:
    """Details a balance proof related event"""

    specific_attribute = {
        "closing_participant": event["closing_participant"],
        "nonce": event["nonce"],
    }

    return specific_attribute


def settled(event: Dict) -> Dict:
    """Details the event of a settled"""

    specific_attribute = {
        "participant1_amount": event["participant1_amount"],
        "participant2_amount": event["participant2_amount"],
    }

    return specific_attribute


def unlocked(event: Dict) -> Dict:
    """Details the event of a unlocked channel"""

    specific_attribute = {
        "participant": event["participant"],
        "partner": event["partner"],
        "locksroot": event["locksroot"],
        "unlocked_amount": event["unlocked_amount"],
        "returned_tokens": event["returned_tokens"],
    }

    return specific_attribute


# pylint: disable=W0613
def withdraw(event: Dict) -> Dict:
    """Details the event of a new withdraw"""

    specific_attribute = {
        "participant": event["participant"],
        "totalWithdraw": event["total_withdraw"],
    }

    return specific_attribute


# pylint: disable=W0613
def unkown_event(event: Dict) -> Dict:
    """Details an unknown event"""

    specific_attribute = {}
    
    return specific_attribute


def get_specific_event_info(event: Dict, channel_event: Dict) -> Dict:
    """Return additional info based on the event type.
    
    Args: 
        event: Event object catched by blockchain listener
        channel_event: Dict with specific attributes
    
    Returns:
        Specific event's Dict with "channelEvent" key for generic event attribute.
    """

    if "event" not in event.keys():
        raise NotAnEventError

    event_name = event["event"]
    generic_attribute = {"channelEvent": channel_event}

    switcher = {
        ChannelEvent.OPENED: opened_channel,
        ChannelEvent.CLOSED: closed_channel,
        ChannelEvent.DEPOSIT: new_deposit,
        ChannelEvent.BALANCE_PROOF_UPDATED: balance_proof_updated,
        ChannelEvent.WITHDRAW: withdraw,
        ChannelEvent.SETTLED: settled,
        ChannelEvent.UNLOCKED: unlocked,
    }
    specific_attributes = switcher.get(event_name, unkown_event)(event["args"])
    final_attributes = {**generic_attribute, **specific_attributes}

    return final_attributes

