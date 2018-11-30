# Raiden Events Poller

[![Build Status](https://dev.azure.com/raiden-map/raiden-events-poller/_apis/build/status/raiden-map.raiden-events-poller)](https://dev.azure.com/raiden-map/raiden-events-poller/_build/latest?definitionId=2)

As stated by the name, this is the component of the pipeline that polls the blockchain for events and logs them into our Apache Kafka Cluster.

## Contributing

The entry point of the application is [raiden_poller_cli.py](https://github.com/poliez/raiden-events-poller/blob/master/raiden-events-poller/raiden_poller_cli.py).
As of now, the code is heavily inspired by the work of the [raiden.network](https://raiden.network) team on their [explorer](https://https://explorer.raiden.network). 

## To-Do

* Transform this project in a kafka producer
* Handle blockchain reorganization
* Handle blockchain unavailability
* Track current block somewhere (file/database)
