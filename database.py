#!/usr/bin/env python3
from typing import List
from tinyflux.queries import TimeQuery
from datetime import datetime, timedelta, timezone
from tinyflux import TagQuery, TinyFlux, Point
from pathlib import Path


class TinyFluxDB:
    def __init__(self) -> None:
        DB_PATH = Path('./database.csv')

        self.db = TinyFlux(DB_PATH)
        self.Tags = TagQuery()
        self.Time = TimeQuery()

        self.mac_address_tag: str = "mac-address"
        self.time_zone = timezone.utc

    def insert_data(self, mac_address: str, fields: dict) -> None:
        """Insert data into the database.

        Args:
            mac_address: the key to insert.
            fields: The dictionary to be inserted as the value.

        Returns:
            None: 
        """

        point = Point(
            time=datetime.now(self.time_zone),
            # measurement='default', 
            tags={self.mac_address_tag: mac_address},
            fields=fields
        )
        self.db.insert(point)

    def query_data(self, macaddress: str, hours_past: int) -> List[dict]:
        """Search data into the database.
        
            Args:
                mac_address: the key to query.
                hours_past: How many hours to search for since now.
        
            Returns:
                List[dict]: The results of the query
        """
        hours_ago = datetime.now(self.time_zone) - timedelta(hours=hours_past)

        return self.db.search((self.Tags[self.mac_address_tag] == macaddress) 
                        & (self.Time >= hours_ago))

    def get_mac_addresses(self) -> List[str]:
        """Get a list of mac addresses in the DB.
        
            Returns:
                List[dict]: Every mac address
        """
        return self.db.get_tag_values()


if __name__ == "__main__": 
    db = TinyFluxDB()
    db.insert_data("dummydata", {"test": 25, "test1": 30})
    print(db.get_mac_addresses())
    print(db.query_data("dummydata", 10))