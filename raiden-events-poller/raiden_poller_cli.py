"""Command Line Tool to listen for raiden network events"""
import logging
import sys

from gevent import monkey, config

config.resolver = ["dnspython", "ares", "block"]
monkey.patch_all()

import click

from eth_utils import is_checksum_address
from web3 import HTTPProvider, Web3
from web3.net import Net
from web3.middleware import geth_poa_middleware

# pylint: disable=W0622
from requests.exceptions import ConnectionError
from raiden_libs.no_ssl_patch import no_ssl_verification
from raiden_contracts.contract_manager import (
    ContractManager,
    contracts_precompiled_path,
    get_contracts_deployed,
)
from raiden_contracts.constants import (
    CONTRACT_TOKEN_NETWORK_REGISTRY,
    CONTRACT_ENDPOINT_REGISTRY,
)

from poller_service import MetricsService

DEFAULT_PORT = 9999
OUTPUT_FILE = "network-info.json"
TEMP_FILE = "tmp.json"
OUTPUT_PERIOD = 10  # seconds
REQUIRED_CONFIRMATIONS = 8  # ~2min with 15s blocks


@click.command()
@click.option(
    "--eth-rpc",
    default="https://ropsten.infura.io/v3/42161ed53b634abf92d6acfbeb92bb31",
    type=str,
    help="Ethereum node RPC URI",
)
@click.option(
    "--token-registry-address",
    default="0x4a6E1fe3dB979e600712E269b26207c49FEe116E",
    type=str,
    help="Address of the token network registry",
)
@click.option(
    "--endpoint-registry-address",
    default="0x444588dFCFe27B31701D3a1541b19849314d1Cac",
    type=str,
    help="Address of the endpoint registry",
)
@click.option(
    "--start-block", default=3_800_000, type=int, help="Block to start syncing at"
)
@click.option(
    "--confirmations",
    default=REQUIRED_CONFIRMATIONS,
    type=int,
    help="Number of block confirmations to wait for",
)
# @click.option(
#     "--latest",
#     default=True,
#     type=bool,
#     help="If you want to use the latest contract release",
# )
def main(
    eth_rpc,
    token_registry_address,
    endpoint_registry_address,
    start_block,
    confirmations,
    # latest,
):
    """Main command"""
    # setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y%m%d %H:%M:%S",
    )
    log = logging.getLogger(__name__)
    logging.getLogger("web3").setLevel(logging.INFO)
    logging.getLogger("urllib3.connectionpool").setLevel(logging.ERROR)

    log.info("Starting Raiden Metrics Server")
    try:
        log.info(f"Starting Web3 client for node at {eth_rpc}")
        web3 = Web3(HTTPProvider(eth_rpc))
        web3.middleware_stack.inject(geth_poa_middleware, layer=0)
    except ConnectionError:
        log.error(
            "Can not connect to the Ethereum client. Please check that it is running and that "
            "your settings are correct."
        )
        sys.exit()

    # chain = Net(web3)
    # log.info(f"Net version = {chain.version}")
    # # use limits for mainnet, pre limits for testnets
    # is_mainnet = chain.version == 1
    # version = None if is_mainnet else "pre_limits"

    with no_ssl_verification():
        valid_params_given = (
            is_checksum_address(token_registry_address) and start_block >= 0
        )

        if not valid_params_given: # or latest is True
            try:
                contract_data = get_contracts_deployed(chain_id=4, version="pre_limits")
                token_network_registry_info = contract_data["contracts"][
                    CONTRACT_TOKEN_NETWORK_REGISTRY
                ]
                endpoint_registry_info = contract_data["contracts"][
                    CONTRACT_ENDPOINT_REGISTRY
                ]

                token_registry_address = token_network_registry_info["address"]
                endpoint_registry_address = endpoint_registry_info["address"]

                start_block = (
                    min(
                        token_network_registry_info["block_number"],
                        endpoint_registry_info["block_number"],
                    )
                    - 20
                )

            except ValueError as ex:
                log.error(ex)
                log.error(
                    "Provided registry address or start block are not valid and "
                    "no deployed contracts were found"
                )
                sys.exit(1)

        token_service = MetricsService(
            web3=web3,
            contract_manager=ContractManager(
                contracts_precompiled_path(version="pre_limits")
            ),
            token_registry_address=token_registry_address,
            endpoint_registry_address=endpoint_registry_address,
            sync_start_block=start_block,
            required_confirmations=confirmations,
        )

        token_service.run()

    sys.exit(0)


if __name__ == "__main__":
    # pylint: disable=E1120
    main()
