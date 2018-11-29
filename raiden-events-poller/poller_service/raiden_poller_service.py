"""Service that logs raiden network events polled from the ethereum blockchain"""
import logging
import sys
import traceback
from typing import Dict, List

import gevent

from web3 import Web3
from eth_utils import is_checksum_address
from raiden_libs.gevent_error_handler import register_error_handler
from raiden_libs.types import Address
from raiden_contracts.contract_manager import ContractManager
from raiden_contracts.constants import (
    CONTRACT_TOKEN_NETWORK,
    CONTRACT_TOKEN_NETWORK_REGISTRY,
    CONTRACT_ENDPOINT_REGISTRY,
    EVENT_TOKEN_NETWORK_CREATED,
    EVENT_ADDRESS_REGISTERED,
)

# pylint: disable=E0401
from poller_utils import get_specific_event_info

from .blockchain_listener import (
    BlockchainListener,
    create_registry_event_topics,
    create_channel_event_topics,
)

# pylint: disable=C0103
log = logging.getLogger(__name__)


def error_handler(_, exc_info):
    """Func to handle errors printing the tracebacks and exiting with a non-zero code"""
    log.fatal("Unhandled exception. Terminating the program...")
    traceback.print_exception(etype=exc_info[0], value=exc_info[1], tb=exc_info[2])
    sys.exit()


def handle_channel_event(event: Dict) -> None:
    """Handles all channel events specified in raiden_contracts.constants.ChannelEvents"""
    event_name = event["event"]
    token_address = event["address"]
    channel_identifier = event["args"]["channel_identifier"]

    log_entry = (
        f"Received {event_name} "
        f"event for token network {token_address} "
        f"on channel {channel_identifier}"
    )

    log_entry += get_specific_event_info(event)

    log.info(log_entry)


# pylint: disable=R0902
class MetricsService(gevent.Greenlet):
    """Logs raiden network events polled from the ethereum blockchain"""

    # pylint: disable=R0913
    def __init__(
        self,
        web3: Web3,
        contract_manager: ContractManager,
        token_registry_address: Address,
        endpoint_registry_address: Address,
        sync_start_block: int = 0,
        required_confirmations: int = 12,  # ~3min
    ):
        """Creates a new pathfinding service"""
        super().__init__()
        self.web3 = web3
        self.contract_manager = contract_manager
        self.required_confirmations = required_confirmations

        self.is_running = gevent.event.Event()
        self.token_networks: List[str] = []
        self.token_network_listeners: List[BlockchainListener] = []

        self.token_network_registry_listener = BlockchainListener(
            web3=web3,
            contract_manager=contract_manager,
            contract_name=CONTRACT_TOKEN_NETWORK_REGISTRY,
            contract_address=token_registry_address,
            sync_start_block=sync_start_block,
            required_confirmations=self.required_confirmations,
        )

        self.token_network_registry_listener.add_confirmed_listener(
            create_registry_event_topics(
                self.contract_manager,
                CONTRACT_TOKEN_NETWORK_REGISTRY,
                EVENT_TOKEN_NETWORK_CREATED,
            ),
            self.handle_token_network_created,
        )

        self.endpoint_registry_listener = BlockchainListener(
            web3=web3,
            contract_manager=contract_manager,
            contract_name=CONTRACT_ENDPOINT_REGISTRY,
            contract_address=endpoint_registry_address,
            sync_start_block=sync_start_block,
            required_confirmations=self.required_confirmations,
        )

        self.endpoint_registry_listener.add_confirmed_listener(
            create_registry_event_topics(
                self.contract_manager,
                CONTRACT_ENDPOINT_REGISTRY,
                EVENT_ADDRESS_REGISTERED,
            ),
            self.handle_endpoint_registered,
        )

        log.info(
            f"Starting TokenNetworkRegistry Listener"
            f" (required confirmations: {self.required_confirmations})...\n"
            f"Listening to token network registry @ {token_registry_address}\n"
            f"Listening to enpoint registry @ {endpoint_registry_address}\n"
            f"Starting from block {sync_start_block}"
        )

    # pylint: disable=E0202
    def _run(self):
        register_error_handler(error_handler)
        if self.token_network_registry_listener is not None:
            self.token_network_registry_listener.start()

        self.is_running.wait()

    def stop(self) -> None:
        """Stops the service"""
        self.is_running.set()

    # pylint: disable=R0201
    def handle_endpoint_registered(self, event: Dict):
        """Handles the EVENT_ADDRESS_REGISTERED event"""
        print(event)

    def handle_token_network_created(self, event: Dict):
        """Handles the EVENT_TOKEN_NETWORK_CREATED event"""
        token_network_address = event["args"]["token_network_address"]
        token_address = event["args"]["token_address"]
        event_block_number = event["blockNumber"]

        assert is_checksum_address(token_network_address)
        assert is_checksum_address(token_address)

        if token_network_address not in self.token_networks:
            log.info(
                f"Found token network for token {token_address} @ {token_network_address}"
            )
            self.create_token_network_for_address(
                token_network_address, event_block_number
            )

    def create_token_network_for_address(
        self, token_network_address: Address, block_number: int = 0
    ):
        """Creates"""
        token_network_listener = BlockchainListener(
            web3=self.web3,
            contract_manager=self.contract_manager,
            contract_address=token_network_address,
            contract_name=CONTRACT_TOKEN_NETWORK,
            sync_start_block=block_number,
            required_confirmations=self.required_confirmations,
        )

        # subscribe to event notifications from blockchain listener
        token_network_listener.add_confirmed_listener(
            create_channel_event_topics(), handle_channel_event
        )
        token_network_listener.start()
        self.token_network_listeners.append(token_network_listener)
