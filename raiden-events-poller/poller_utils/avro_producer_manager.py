import os
import sys
from typing import Dict
from json import dumps, loads
from confluent_kafka import avro
from confluent_kafka.avro import AvroProducer


def combine_schema(*schema: str) -> str:
    """Concatenate metadata schema with specific event's schema.
    
    Args:
        schema: Several avro schemas to concatenate.

    Returns:    
        All schemas concatenated ( nested schema ) to be read in avro.
    """

    schemas = [open(el).read().replace("\r\n", "\n") for el in schema]

    combined_schema = "[" + ",".join(schemas) + "]"

    return combined_schema


def schema_avsc_research(schema_directory: str) -> Dict:
    """Find all avro schema from a folder.

    Args:
        schema_directory: Folder in which search avro schema.
    
    Returns:
        A Dict: value = event_name, key = specific avro schema.
    """

    schema_dir_dict = {}
    for root, _, files in os.walk(schema_directory):
        for name in files:
            if name.endswith(".avsc"):
                event_name = os.path.splitext(name)[0]
                event_directory = os.path.join(root, name)
                schema_dir_dict[event_name] = event_directory
    return schema_dir_dict


def create_nested_schema(directory_dict: Dict) -> Dict:
    """For every specific event creates its nested schema.

    Args:
        directory_dict: A Dict with value = event_name, key = specific avro schema.
    
    Returns:
        A specific event's Dict with: value = specific event, key = nested avro schema. 

    """

    schema_dict = {}
    metadata_dir = directory_dict["Metadata"]
    channel_event_dir = directory_dict["ChannelEvent"]

    for event, directory in directory_dict.items():
        if event == "ChannelEvent":
            continue

        if event.startswith(("Channel", "Non")):
            schema_dict[event] = combine_schema(
                metadata_dir, channel_event_dir, directory
            )
        elif event != "Metadata":
            schema_dict[event] = combine_schema(metadata_dir, directory)

    return schema_dict


class AvroProducerManager:
    """Manages kafka producer to record events details.

    Attributes:
        kafka_broker_url: The URL of kafka broker to communicate with
        event_schema_dir: A directory in which search avro schema files
        schema_registry_url: The URL of the confluent schema registry instance
        raiden_map_producer: A Dict with: value = event, key = kafka producer
    """

    def __init__(
        self, event_schema_dir: str, kafka_broker_url: str, schema_registry_url: str
    ):
        self.raiden_map_producer = self.producer_factory(
            kafka_broker_url, schema_registry_url, event_schema_dir
        )

    def producer_factory(
        self, kafka_broker_url: str, schema_registry_url: str, event_schema_dir: str
    ) -> Dict:
        """Initialize producer for every event
        
        Returns:
            A Dict with: value = event, key = kafka producer
        """
        schema_path = schema_avsc_research(event_schema_dir)
        event_schema_dict = create_nested_schema(schema_path)
        raiden_map_producer = {}

        for event, schema in event_schema_dict.items():
            raiden_map_producer[event] = AvroProducer(
                {
                    "bootstrap.servers": kafka_broker_url,
                    "schema.registry.url": schema_registry_url,
                },
                default_value_schema=avro.loads(schema),
            )
        return raiden_map_producer

    def produce(self, event: str, value: Dict):
        """Call specific producer for every type of event and send data defined in its event's schema
        
        Args: 
            event: A specific event triggered in its constract
            value = Specific event's schema to complete with catched attributes
        """

        self.raiden_map_producer[event].produce(
            topic="tracking.raidenEvent." + event, value=value
        )
