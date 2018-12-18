"""Service that logs raiden network events polled from the ethereum blockchain"""
import logging
import sys
import traceback
import time
from typing import Dict, List
from pprint import pprint
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
from poller_utils import get_specific_event_info, AvroProducerManager

from .blockchain_listener import (
    BlockchainListener,
    create_registry_event_topics,
    create_channel_event_topics,
)

# pylint: disable=C0103
TO_NANO: int = 10 ** 9


# pylint: disable=R0902
class MetricsService(gevent.Greenlet):
    """Logs raiden network events polled from the ethereum blockchain.
    
    Attributes:
        web3: A ethereum library's instance to call eth blockchain info.
        contract_manager: 
        required_confirmations: Minimun confirmations to explore block's tx
        is_running:
        token_network: List of known token network
        token_network_listeners: A BlockchainListener's intance to catch new events
        producer_manager: An AvroProducerManager's instance to send event's data to kafka producers

    """

    # pylint: disable=R0913
    def __init__(
        self,
        web3: Web3,
        contract_manager: ContractManager,
        token_registry_address: Address,
        endpoint_registry_address: Address,
        producer_manager: AvroProducerManager,
        sync_start_block: int = 0,
        required_confirmations: int = 12,  # ~3min
    ):
        """Creates a new pathfinding service"""
        super().__init__()
        self.log = logging.getLogger(__name__)
        self.web3 = web3
        self.contract_manager = contract_manager
        self.required_confirmations = required_confirmations
        self.is_running = gevent.event.Event()
        self.token_networks: List[str] = []
        self.token_network_listeners: List[BlockchainListener] = []
        self.produce_manager = producer_manager

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

        self.log.info(
            f"Starting TokenNetworkRegistry Listener"
            f" (required confirmations: {self.required_confirmations})...\n"
            f"Listening to token network registry @ {token_registry_address}\n"
            f"Listening to enpoint registry @ {endpoint_registry_address}\n"
            f"Starting from block {sync_start_block}"
        )

    # pylint: disable=E0202
    def _run(self):
        register_error_handler(self.error_handler)
        if self.token_network_registry_listener is not None:
            self.token_network_registry_listener.start()

        if self.endpoint_registry_listener is not None:
            self.endpoint_registry_listener.start()

        self.is_running.wait()

    def stop(self) -> None:
        """Stops the service"""
        self.is_running.set()

    def error_handler(self, _, exc_info):
        """Func to handle errors printing the tracebacks and exiting with a non-zero code"""

        self.log.fatal("Unhandled exception. Terminating the program...")
        traceback.print_exception(etype=exc_info[0], value=exc_info[1], tb=exc_info[2])
        sys.exit()

    def metadata_handler(self, event: Dict) -> str:
        """Handles generic data for any event.
        
        Args:
            event: Any raiden's events catched.

        Returns:
            A Dict with generic attributes.
                """

        blockTime = self.web3.eth.getBlock(event["blockNumber"])["timestamp"] * TO_NANO
        eventTime = int(time.time() * TO_NANO)

        metadata_attribute = {
            "blockNumber": event["blockNumber"],
            "blockTimestamp": blockTime,
            "eventTimestamp": eventTime,
        }

        return metadata_attribute

    def handle_channel_event(self, event: Dict) -> None:
        """Handles all channel events specified in raiden_contracts.constants.ChannelEvents and combine channel's generic attributes with event's generic attributes.

        Args:
            event: Any raiden channel's events catched.

        """

        channel_event = {
            "metadata": self.metadata_handler(event),
            "addressId": event["address"],
            "id": event["args"]["channel_identifier"],
        }

        specific_event_dict = get_specific_event_info(event, channel_event)
        self.produce_manager.produce(event["event"], specific_event_dict)

    # pylint: disable=R0201
    def handle_endpoint_registered(self, event: Dict) -> None:
        """Handles the EVENT_ADDRESS_REGISTERED event and combine endpoint registering's generic attributes with event's generic attributes.
        
        Args:
            event: Any new endpoint registering events catched.
        """

        specific_event_dict = {
            "metadata": self.metadata_handler(event),
            "ethAddress": event["args"]["eth_address"],
            "endpointAddress": event["args"]["endpoint"],
        }

        self.produce_manager.produce(event["event"], specific_event_dict)

    def handle_token_network_created(self, event: Dict) -> None:
        """Handles the EVENT_TOKEN_NETWORK_CREATED event"""
        token_network_address = event["args"]["token_network_address"]
        token_address = event["args"]["token_address"]
        event_block_number = event["blockNumber"]

        specific_event_dict = {
            "metadata": self.metadata_handler(event),
            "tokenNetworkAddress": token_network_address,
            "tokenAddress": token_address,
        }

        assert is_checksum_address(token_network_address)
        assert is_checksum_address(token_address)

        if token_network_address not in self.token_networks:
            self.log.info(
                f"New Token Network. token: {token_address} address: {token_network_address}"
            )
            self.create_token_network_for_address(
                token_network_address, event_block_number
            )
            # print(event["event"])
            self.produce_manager.produce(event["event"], specific_event_dict)

    def create_token_network_for_address(
        self, token_network_address: Address, block_number: int = 0
    ) -> None:
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
            create_channel_event_topics(), self.handle_channel_event
        )
        token_network_listener.start()
        self.token_network_listeners.append(token_network_listener)
