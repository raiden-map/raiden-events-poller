from confluent_kafka import avro, OFFSET_END, TopicPartition, KafkaError
from confluent_kafka.avro import AvroConsumer
from confluent_kafka.avro.serializer import SerializerError
import sys
from .db_store_manager import dbStoreManager

class ConsumerRecovery:
    """Manages kafka consumer to recover last block's event not completly produced

    """
    def __init__(self):
        self.produced_event = []
        self.db_manager = dbStoreManager()
        produced_block = self.db_manager.event_list()
        self.consumer_factory(produced_block)
        

    def consumer_factory(self, produced_block):
        """Initialize consumer for every event and call consume function to start to consume all event produced

        Args:
            produced_block: mysql array with: offset, block_number, event_name 
        """
        consumer = {}
        for event in produced_block:
            try:
                consumer[event["event"]] = AvroConsumer(
                    {
                        "bootstrap.servers": "raiden-kafka-headless.kafka.svc.cluster.local:9092",
                        "schema.registry.url": "http://raiden-sr-schema-registry.kafka.svc.cluster.local:8081",
                        "group.id": "testConsumer",
                    }
                )
                consumer[event["event"]].assign(
                    [TopicPartition("tracking.raidenEvent." + event["event"], 0, event["offset"])]
                )
            except Exception:
                sys.exit(1)

            self.consume(consumer[event["event"]])

    def consume(self, consumer):
        """Call specific consumer for every type of event that consume and save in self.produced_event tx_hash
        
        Args: 
            consumer: list of initializated AvroConsumer
        """
        while True:
            try:
                msg = consumer.poll(0.5)

            except KafkaError as e:
                print("AvroConsumer error: {}".format(msg.error()))
                break

            except SerializerError as e:
                print("Message deserialization failed for {}: {}".format(msg, e))
                break

            if msg is None:
                print("Finished to consume")
                break

            elif msg.key() is not None:
                tx_hash = msg.key()["txHash"]
                self.produced_event.append(tx_hash)

    def get_produced_event(self):
        """Returns: produced event's list that contain all tx_hash of a block not completly produced
        """
        return self.produced_event 
    

