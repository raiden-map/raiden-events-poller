import os
import sys
from typing import Dict
from confluent_kafka import avro, KafkaError
from confluent_kafka.avro import AvroProducer
import time
from pprint import pprint
from confluent_kafka.cimpl import OFFSET_END, OFFSET_STORED
from .db_store_manager import dbStoreManager


def combine_schema(schema):
    """Concatenate metadata schema with specific event's schema.
    
    Args:
        schema: Several avro schemas to concatenate.

    Returns:    
        All schemas concatenated ( nested schema ) to be read in avro.
    """
    schemas = [open(el).read().replace("\r\n", "\n") for el in schema]

    for i in range(1,len(schemas)):
        schemas[i] = (schemas[i]).replace('"io.raidenmap.event.Metadata"',(schemas[i-1]).replace('"namespace": "io.raidenmap.event",',''))
        schemas[i] = (schemas[i]).replace('"io.raidenmap.event.channel.ChannelEvent"',(schemas[i-1]).replace('"namespace": "io.raidenmap.event.channel",',''))

    return schemas[len(schemas)-1]

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
            a=[metadata_dir, channel_event_dir, directory]
            schema_dict[event] = combine_schema(a)

        elif event != "Metadata":
            a=[metadata_dir, directory]
            schema_dict[event] = combine_schema(a)


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
        self.db_manager = dbStoreManager()
        self.max_block_number = 0
        self.offset = 0
        self.produced_event = []
    
    def set_produced_event(self, produced_event):
        self.produced_event = produced_event

    def producer_factory(
        self, kafka_broker_url: str, schema_registry_url: str, event_schema_dir: str
    ) -> Dict:
        """Initialize producer for every event
        
        Returns:
            A Dict with: value = event, key = kafka producer
        """
        schema_path = schema_avsc_research(event_schema_dir)
        key_schema = open(schema_path["ProducerKey"]).read()
        del schema_path["ProducerKey"]
        event_schema_dict = create_nested_schema(schema_path)
        raiden_map_producer = {}
        
        for event, schema in event_schema_dict.items():
            try:
                raiden_map_producer[event] = AvroProducer(
                    {
                        "bootstrap.servers": kafka_broker_url,
                        "schema.registry.url": schema_registry_url,
                    },
                    default_key_schema=avro.loads(key_schema),
                    default_value_schema=avro.loads(schema),
                )
            except KafkaError as ke:
                print(ke)
            except Exception:
                sys.exit(1)
            
        return raiden_map_producer


    def produce(self, event: str,*, value: Dict, key: Dict):
        """Call specific producer for every type of event and send data defined in its event's schema
        
        Args: 
            event: Name's event
            value: A specific event's schema
            key: The schema that contains tx hash
        """

        def delivery_report(err, msg):
        
            if err is not None:
                print('Message delivery failed: {}'.format(err))
            else:
                #print('Message delivered to {} [{}][{}]'.format(msg.topic(), msg.partition(), msg.offset()))
                self.offset = msg.offset()

        if key["txHash"] not in self.produced_event:

            self.raiden_map_producer[event].produce(
                topic="tracking.raidenEvent." + event, value=value, key=key, callback=delivery_report
                        )
            self.raiden_map_producer[event].poll(0)

            if event.startswith("Channel"):
                block_number = value["channelEvent"]["metadata"]["blockNumber"]
                print("PRODUCER: ", block_number)

                if block_number > self.max_block_number:
                    self.max_block_number = block_number
                    self.db_manager.update_block_number(event, block_number)
                    self.db_manager.new_produced_block( self.offset, self.max_block_number, event )
        else:
            print("Event: ", key["txHash"], " is in Kafka")

    def max_block_number_produced(self):
        """Find the maximum block number of which all events were produced
        
        Returns:
            The maximum block number if it exists, otherwise a minimum number
        """
        max_block_number = self.db_manager.max_block()
        if max_block_number is None:
            return 3800000
        else:
            return max_block_number




